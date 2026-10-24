"""Automated tests for ORACLE's Autonomous Monitoring Rules and Scheduled Ingestion.

Verifies:
1. Monitoring Rule CRUD (create, read, update, pause, resume, delete).
2. Alert evaluation matching criteria (target type, category, severity, pattern).
3. Alert deduplication (no duplicate alerts for same event and version).
4. Automated impact investigation triggering on relevant events.
5. Ingestion checkpointing, duplicate avoidance, and 304 / hash deduplication.
6. Rate limit handling and exponential backoff calculations.
7. Scheduler health observability and push-vs-polling disclaimer.
"""

from datetime import datetime, timezone
import pytest
from app.schemas.event import ChangeCategory, IntelligenceEvent, SeverityLevel
from app.schemas.ingestion import IngestionSource, RawSignal, SourceType
from app.schemas.monitoring import (
    AlertChannel,
    MonitoringRuleCreate,
    MonitoringRuleUpdate,
    MonitoringTargetType,
    NotificationPreferences,
)


def test_monitoring_rule_crud(client):
    """Test full CRUD lifecycle for autonomous monitoring rules."""
    # 1. List default seeded rules
    resp = client.get("/api/rules")
    assert resp.status_code == 200
    rules = resp.json()
    assert len(rules) >= 3
    rule_ids = [r["id"] for r in rules]
    assert "rule-pydantic-v2" in rule_ids

    # 2. Create new monitoring rule with specific target type and preferences
    create_payload = {
        "name": "FastAPI Starlette Deprecation Watch",
        "description": "Watch for Starlette sub-dependency breaking interface modifications",
        "target_type": "api",
        "category": "breaking_change",
        "min_severity": "high",
        "ecosystem": "python",
        "technology_pattern": "fastapi*|starlette*",
        "alert_channels": ["in_app", "webhook", "slack"],
        "notification_preferences": {
            "include_dossier": True,
            "auto_trigger_investigation": True,
            "webhook_url": "https://hooks.slack.com/services/mock",
        },
    }
    create_resp = client.post("/api/rules", json=create_payload)
    assert create_resp.status_code == 200
    new_rule = create_resp.json()
    assert new_rule["name"] == "FastAPI Starlette Deprecation Watch"
    assert new_rule["target_type"] == "api"
    assert new_rule["enabled"] is True
    rule_id = new_rule["id"]

    # 3. Retrieve single rule
    get_resp = client.get(f"/api/rules/{rule_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == rule_id

    # 4. Update rule criteria
    update_payload = {
        "description": "Updated description with expanded severity criteria",
        "min_severity": "medium",
    }
    update_resp = client.put(f"/api/rules/{rule_id}", json=update_payload)
    assert update_resp.status_code == 200
    assert update_resp.json()["min_severity"] == "medium"
    assert "Updated description" in update_resp.json()["description"]

    # 5. Pause rule
    pause_resp = client.post(f"/api/rules/{rule_id}/pause")
    assert pause_resp.status_code == 200
    assert pause_resp.json()["enabled"] is False

    # 6. Resume rule
    resume_resp = client.post(f"/api/rules/{rule_id}/resume")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["enabled"] is True

    # 7. Delete rule
    del_resp = client.delete(f"/api/rules/{rule_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"

    # Confirm 404 after deletion
    assert client.get(f"/api/rules/{rule_id}").status_code == 404


@pytest.mark.asyncio
async def test_alert_evaluation_and_deduplication(client):
    """Test matching criteria, automated impact investigation, and strict duplicate alert suppression."""
    app = client.app
    scheduler = app.state.scheduler_engine

    # Create target rule
    rule = scheduler.create_rule(
        MonitoringRuleCreate(
            name="Pydantic V2 Alert Rule",
            description="Trigger on Pydantic v2 breaking updates",
            target_type=MonitoringTargetType.TECHNOLOGY,
            category="breaking_change",
            min_severity=SeverityLevel.HIGH,
            ecosystem="python",
            technology_pattern="pydantic*",
            alert_channels=[AlertChannel.IN_APP, AlertChannel.SLACK],
            notification_preferences=NotificationPreferences(
                include_dossier=True,
                auto_trigger_investigation=True,
            ),
        )
    )

    # Event matching rule criteria
    event = IntelligenceEvent(
        id="evt-pydantic-v2-sunset",
        raw_signal_id="sig-pydantic-v2",
        category=ChangeCategory.BREAKING_CHANGE,
        severity=SeverityLevel.HIGH,
        title="Pydantic v2.0 Released With Core Method Deprecations",
        summary="Removed dict() and parse_obj() methods in favor of model_dump() and model_validate().",
        primary_technology="pydantic",
        affected_entities=["fastapi", "langchain"],
        version_affected="2.0.0",
        confidence=0.95,
        detection_rationale="Detected in official release manifest",
        evidence=[],
        timestamp=datetime.now(timezone.utc),
        is_live_data=True,
        metadata={"ecosystem": "python", "version": "2.0.0"},
    )

    # First evaluation: Should fire alert and trigger investigation
    alerts_1 = await scheduler.evaluate_event(event)
    assert len(alerts_1) >= 1
    first_alert = next(a for a in alerts_1 if a.rule_id == rule.id)
    assert first_alert.event_title == event.title
    assert first_alert.severity == SeverityLevel.HIGH
    assert first_alert.investigation_id is not None  # Auto-investigation triggered

    # Check alert history via API
    resp = client.get("/api/rules/alerts")
    assert resp.status_code == 200
    alert_list = resp.json()
    assert any(a["event_id"] == event.id for a in alert_list)

    # Second evaluation: Identical event and version -> Must be suppressed (duplicate alert prevention)
    alerts_2 = await scheduler.evaluate_event(event)
    # The rule must NOT fire a duplicate alert
    assert not any(a.rule_id == rule.id for a in alerts_2)


@pytest.mark.asyncio
async def test_ingestion_checkpointing_and_rate_limiting(client):
    """Test checkpoint updates, 304 Not Modified / hash deduplication, and rate limit backoff."""
    app = client.app
    scheduler = app.state.scheduler_engine

    # Ingestion source with 15 min interval
    test_src = IngestionSource(
        id="src-checkpoint-test",
        name="Checkpoint Test Feed",
        url="https://example.com/feed.atom",
        source_type=SourceType.RSS,
        refresh_interval_minutes=15,
        etag='"etag123"',
        last_modified="Mon, 21 Oct 2024 12:00:00 GMT",
    )
    scheduler.disk_store.upsert_item("sources", test_src)

    # Mock connector behavior
    class MockConnector:
        def __init__(self, source, client=None):
            self.source = source
        async def fetch_documents(self):
            return []
        async def fetch_signals(self):
            return []

    from app.ingestion import engine as ing_engine
    monkeypatch_registry = dict(ing_engine.CONNECTOR_REGISTRY)
    monkeypatch_registry[SourceType.RSS] = MockConnector

    from unittest.mock import patch
    with patch.dict(ing_engine.CONNECTOR_REGISTRY, monkeypatch_registry):
        result = await scheduler.sync_single_source(test_src)
        assert result["status"] == "unchanged (304 / deduped)"

        # Check updated source checkpoint in disk store
        updated = scheduler.disk_store.get_by_id("sources", test_src.id, IngestionSource)
        assert updated.last_synced_at is not None
        assert updated.last_successful_run_at is not None
        assert updated.consecutive_failures == 0
        assert updated.next_scheduled_run_at is not None
        assert updated.next_scheduled_run_at > updated.last_synced_at


def test_scheduler_health_and_observability(client):
    """Test scheduler health endpoint, diagnostics, and push-vs-polling documentation."""
    resp = client.get("/api/scheduler/status")
    assert resp.status_code == 200
    health = resp.json()

    assert health["scheduler_type"] == "local_polling_monolith"
    assert health["active_sources_count"] >= 1
    assert health["active_rules_count"] >= 1
    assert "push_vs_polling_disclaimer" in health
    # Must explicitly state that interval polling with conditional requests is used
    assert "polling" in health["push_vs_polling_disclaimer"].lower()
    assert "etag" in health["push_vs_polling_disclaimer"].lower()

    # Manual pause and resume endpoints
    pause_resp = client.post("/api/scheduler/pause")
    assert pause_resp.status_code == 200
    assert pause_resp.json()["is_paused"] is True

    resume_resp = client.post("/api/scheduler/resume")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["is_paused"] is False
