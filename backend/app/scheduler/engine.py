"""Reliable Scheduler and Autonomous Monitoring Engine for ORACLE.

Provides idempotent, bounded scheduled ingestion, rate limit backoff,
checkpoint tracking, change detection, automated impact investigations,
and strict alert deduplication.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import fnmatch
import logging
import random
import re
from typing import Any, Dict, List, Optional, Set

from ..change_detection.detector import ChangeDetector
from ..config import get_settings
from ..impact.investigation_service import InvestigationService
from ..ingestion.engine import IngestionEngine
from ..retrieval.rag_pipeline import LiveRAGPipeline
from ..schemas.event import ChangeCategory, IntelligenceEvent, SeverityLevel
from ..schemas.ingestion import IngestionSource, RawSignal
from ..schemas.investigation import InvestigationRequest
from ..schemas.monitoring import (
    AlertChannel,
    AlertRecord,
    MonitoringRule,
    MonitoringRuleCreate,
    MonitoringRuleUpdate,
    MonitoringTargetType,
    NotificationPreferences,
    SchedulerHealth,
    SourceHealthStatus,
)
from ..schemas.report import ImpactReport, MitigationAction
from ..storage.disk_store import DiskStore

logger = logging.getLogger("oracle.scheduler")


DEFAULT_MONITORING_RULES: List[MonitoringRule] = [
    MonitoringRule(
        id="rule-pydantic-v2",
        name="Pydantic V2 Interface & Serialization Watch",
        description="Trigger high-priority alerts on Pydantic schema changes, deprecated dict()/parse_obj() methods, and ConfigDict migrations.",
        target_type=MonitoringTargetType.TECHNOLOGY,
        category="breaking_change",
        min_severity=SeverityLevel.HIGH,
        ecosystem="python",
        technology_pattern="pydantic*",
        enabled=True,
        trigger_count=0,
        alert_channels=[AlertChannel.IN_APP, AlertChannel.SLACK, AlertChannel.WEBHOOK],
        notification_preferences=NotificationPreferences(
            include_dossier=True,
            auto_trigger_investigation=True,
        ),
    ),
    MonitoringRule(
        id="rule-fastapi-lifespan",
        name="FastAPI Breaking Lifespan & Dependency Watch",
        description="Monitor FastAPI core updates, lifespan event handler deprecations, and Starlette version bumps.",
        target_type=MonitoringTargetType.API,
        category="any",
        min_severity=SeverityLevel.MEDIUM,
        ecosystem="python",
        technology_pattern="fastapi*",
        enabled=True,
        trigger_count=0,
        alert_channels=[AlertChannel.IN_APP, AlertChannel.WEBHOOK],
        notification_preferences=NotificationPreferences(
            include_dossier=True,
            auto_trigger_investigation=True,
        ),
    ),
    MonitoringRule(
        id="rule-security-advisories",
        name="CISA & NVD Critical Security Advisory Watch",
        description="Immediate P0 alert on newly published remote code execution, CVSS 8.0+, or known exploited vulnerabilities.",
        target_type=MonitoringTargetType.SECURITY_ADVISORY,
        category="security_vulnerability",
        min_severity=SeverityLevel.CRITICAL,
        ecosystem="all",
        technology_pattern="*",
        enabled=True,
        trigger_count=0,
        alert_channels=[AlertChannel.IN_APP, AlertChannel.PAGERDUTY, AlertChannel.SLACK],
        notification_preferences=NotificationPreferences(
            include_dossier=True,
            auto_trigger_investigation=True,
        ),
    ),
    MonitoringRule(
        id="rule-cloud-outages",
        name="Cloudflare & Infrastructure Outage Monitor",
        description="Track edge network degradation, API incident notices, and public cloud status disruptions.",
        target_type=MonitoringTargetType.PRODUCT,
        category="outage",
        min_severity=SeverityLevel.MEDIUM,
        ecosystem="cloud",
        technology_pattern="cloudflare*|aws*|gcp*",
        enabled=True,
        trigger_count=0,
        alert_channels=[AlertChannel.IN_APP, AlertChannel.WEBHOOK],
        notification_preferences=NotificationPreferences(
            include_dossier=False,
            auto_trigger_investigation=False,
        ),
    ),
]


class ScheduledMonitoringEngine:
    """Manages scheduled polling, rate-limited execution, checkpointing,

    rule evaluation, automated impact investigations, and alert deduplication.
    """

    def __init__(
        self,
        disk_store: DiskStore,
        ingestion_engine: IngestionEngine,
        rag_pipeline: LiveRAGPipeline,
        change_detector: ChangeDetector,
        investigation_service: InvestigationService,
    ):
        self.disk_store = disk_store
        self.ingestion_engine = ingestion_engine
        self.rag_pipeline = rag_pipeline
        self.change_detector = change_detector
        self.investigation_service = investigation_service

        self._is_running = False
        self._is_paused = False
        self._loop_task: Optional[asyncio.Task] = None
        self._poll_locks: Dict[str, asyncio.Lock] = {}
        self._last_tick_at: Optional[datetime] = None
        self._total_runs = 0
        self._total_events = 0
        self._total_investigations = 0
        self._total_errors = 0

        self._init_rules()

    # -------------------------------------------------------------------------
    # Rule Management (CRUD & State)
    # -------------------------------------------------------------------------

    def _init_rules(self) -> None:
        """Seed default monitoring rules if not present in disk store."""
        existing = self.disk_store.load_all("monitoring_rules", MonitoringRule)
        if not existing:
            self.disk_store.save_all("monitoring_rules", DEFAULT_MONITORING_RULES)
            logger.info(f"Initialized {len(DEFAULT_MONITORING_RULES)} default monitoring rules.")

    def list_rules(self) -> List[MonitoringRule]:
        """List all configured monitoring rules."""
        rules = self.disk_store.load_all("monitoring_rules", MonitoringRule)
        rules.sort(key=lambda r: r.created_at, reverse=True)
        return rules

    def get_rule(self, rule_id: str) -> Optional[MonitoringRule]:
        """Fetch a specific rule by ID."""
        return self.disk_store.get_by_id("monitoring_rules", rule_id, MonitoringRule)

    def create_rule(self, payload: MonitoringRuleCreate) -> MonitoringRule:
        """Create a new monitoring rule."""
        now = datetime.now(timezone.utc)
        rule_id = f"rule-{int(now.timestamp())}-{random.randint(100, 999)}"
        rule = MonitoringRule(
            id=rule_id,
            name=payload.name,
            description=payload.description or "",
            target_type=payload.target_type or MonitoringTargetType.TECHNOLOGY,
            category=payload.category or "any",
            min_severity=payload.min_severity or SeverityLevel.HIGH,
            ecosystem=payload.ecosystem or "all",
            technology_pattern=payload.technology_pattern or "*",
            enabled=True,
            trigger_count=0,
            alert_channels=payload.alert_channels or [AlertChannel.IN_APP, AlertChannel.WEBHOOK],
            notification_preferences=payload.notification_preferences or NotificationPreferences(),
            created_at=now,
            updated_at=now,
        )
        self.disk_store.upsert_item("monitoring_rules", rule)
        logger.info(f"Created monitoring rule: '{rule.name}' ({rule.id})")
        return rule

    def update_rule(self, rule_id: str, payload: MonitoringRuleUpdate) -> Optional[MonitoringRule]:
        """Update an existing monitoring rule."""
        rule = self.get_rule(rule_id)
        if not rule:
            return None

        update_data = payload.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            if val is not None:
                setattr(rule, key, val)
        rule.updated_at = datetime.now(timezone.utc)

        self.disk_store.upsert_item("monitoring_rules", rule)
        logger.info(f"Updated monitoring rule: '{rule.name}' ({rule.id})")
        return rule

    def pause_rule(self, rule_id: str) -> Optional[MonitoringRule]:
        """Pause a monitoring rule."""
        rule = self.get_rule(rule_id)
        if not rule:
            return None
        rule.enabled = False
        rule.updated_at = datetime.now(timezone.utc)
        self.disk_store.upsert_item("monitoring_rules", rule)
        logger.info(f"Paused monitoring rule: {rule_id}")
        return rule

    def resume_rule(self, rule_id: str) -> Optional[MonitoringRule]:
        """Resume a paused monitoring rule."""
        rule = self.get_rule(rule_id)
        if not rule:
            return None
        rule.enabled = True
        rule.updated_at = datetime.now(timezone.utc)
        self.disk_store.upsert_item("monitoring_rules", rule)
        logger.info(f"Resumed monitoring rule: {rule_id}")
        return rule

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a monitoring rule."""
        return self.disk_store.delete_item("monitoring_rules", rule_id, MonitoringRule)

    def list_alerts(self, limit: int = 50) -> List[AlertRecord]:
        """Retrieve audit log of dispatched, deduplicated alerts."""
        alerts = self.disk_store.load_all("alert_records", AlertRecord)
        alerts.sort(key=lambda a: a.dispatched_at, reverse=True)
        return alerts[:limit]

    # -------------------------------------------------------------------------
    # Evaluation & Deduplicated Alerting
    # -------------------------------------------------------------------------

    def _matches_pattern(self, pattern: str, target: str) -> bool:
        """Evaluate wildcard or regex pattern against a target string."""
        if not pattern or pattern == "*":
            return True
        t_clean = target.lower().strip()
        p_clean = pattern.lower().strip()

        # Handle pipe-separated patterns like "fastapi|pydantic|nextjs"
        if "|" in p_clean:
            subpatterns = [p.strip() for p in p_clean.split("|") if p.strip()]
            return any(self._matches_pattern(sub, target) for sub in subpatterns)

        # Wildcard match
        if "*" in p_clean or "?" in p_clean:
            return fnmatch.fnmatch(t_clean, p_clean)

        return p_clean in t_clean

    def _is_severity_met(self, event_sev: SeverityLevel, min_sev: SeverityLevel) -> bool:
        """Check if event severity meets or exceeds rule threshold."""
        hierarchy = {
            SeverityLevel.INFO: 0,
            SeverityLevel.LOW: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.HIGH: 3,
            SeverityLevel.CRITICAL: 4,
        }
        return hierarchy.get(event_sev, 0) >= hierarchy.get(min_sev, 0)

    async def evaluate_event(self, event: IntelligenceEvent) -> List[AlertRecord]:
        """Evaluate an intelligence event against all active monitoring rules

        with strict alert deduplication and optional automatic impact investigations.
        """
        rules = [r for r in self.list_rules() if r.enabled]
        if not rules:
            return []

        # Load existing alert records to prevent duplicate notifications
        existing_alerts = {a.dedup_key: a for a in self.disk_store.load_all("alert_records", AlertRecord)}
        dispatched_alerts: List[AlertRecord] = []
        now = datetime.now(timezone.utc)

        for rule in rules:
            # 1. Ecosystem match
            if rule.ecosystem != "all" and rule.ecosystem.lower() != event.metadata.get("ecosystem", "").lower():
                continue

            # 2. Category match
            if rule.category != "any" and rule.category.lower() != event.category.value.lower():
                continue

            # 3. Severity gate
            if not self._is_severity_met(event.severity, rule.min_severity):
                continue

            # 4. Technology / Pattern match
            matched_tech = self._matches_pattern(rule.technology_pattern, event.primary_technology)
            matched_entities = any(self._matches_pattern(rule.technology_pattern, ent) for ent in event.affected_entities)
            matched_title = self._matches_pattern(rule.technology_pattern, event.title)
            if not (matched_tech or matched_entities or matched_title):
                continue

            # 5. Strict Alert Deduplication
            version_key = event.version_affected or event.metadata.get("version", "v1")
            dedup_key = f"{rule.id}:{event.id}:{version_key}"
            if dedup_key in existing_alerts:
                logger.debug(f"Alert suppressed (duplicate): {dedup_key}")
                continue

            # 6. Automatic Impact Investigation
            investigation_id = None
            if rule.notification_preferences.auto_trigger_investigation:
                try:
                    report = await self.investigation_service.investigate(
                        InvestigationRequest(
                            query=f"{event.title} - {event.summary}",
                            event_id=event.id,
                            target_technology=event.primary_technology,
                            max_candidates=8,
                        )
                    )
                    investigation_id = report.id
                    self._total_investigations += 1

                    # Persist impact report
                    impact_report = ImpactReport(
                        id=f"rpt_{report.id}",
                        event_id=event.id,
                        event_title=event.title,
                        severity=event.severity,
                        primary_technology=event.primary_technology,
                        ecosystem=event.metadata.get("ecosystem", "generic"),
                        executive_summary=report.executive_summary,
                        technical_root_cause=f"Auto-triggered by monitoring rule '{rule.name}' for {event.primary_technology}.",
                        breaking_changes=[f.summary for f in report.findings if f.severity in (SeverityLevel.HIGH, SeverityLevel.CRITICAL)],
                        impacted_components=[],
                        evidence_trail=[
                            {
                                "source_url": c.source_url,
                                "source_type": "advisory",
                                "title": c.title,
                                "snippet": c.snippet,
                                "content_hash": c.content_hash,
                            }
                            for c in report.evidence_citations
                        ],
                        mitigation_playbook=[
                            MitigationAction(
                                step_number=i + 1,
                                title=f"Remediate {f.affected_entity_name}",
                                description="; ".join(f.suggested_next_steps[:2]),
                                priority=f.severity,
                                action_type="dependency_audit",
                                estimated_effort="medium",
                            )
                            for i, f in enumerate(report.findings[:3])
                        ],
                        confidence_score=0.92,
                        llm_provenance={"mode": "automated_rule_trigger", "rule_id": rule.id},
                        generated_at=now.isoformat(),
                        is_live_data=True,
                    )
                    self.disk_store.upsert_item("reports", impact_report)
                except Exception as e:
                    logger.warning(f"Auto-investigation failed for event {event.id}: {e}")

            # 7. Record and dispatch alert
            alert = AlertRecord(
                id=f"alt-{int(now.timestamp())}-{random.randint(100, 999)}",
                rule_id=rule.id,
                rule_name=rule.name,
                event_id=event.id,
                event_title=event.title,
                event_version=version_key,
                severity=event.severity,
                dispatched_at=now,
                channels=rule.alert_channels,
                status="dispatched",
                investigation_id=investigation_id,
                dedup_key=dedup_key,
            )
            self.disk_store.upsert_item("alert_records", alert)
            existing_alerts[dedup_key] = alert
            dispatched_alerts.append(alert)

            # Update rule triggers
            rule.trigger_count += 1
            rule.last_triggered_at = now
            self.disk_store.upsert_item("monitoring_rules", rule)

            logger.info(
                f"Dispatched alert for rule '{rule.name}' on event '{event.title}' "
                f"({', '.join(c.value for c in alert.channels)})"
            )

        return dispatched_alerts

    # -------------------------------------------------------------------------
    # Scheduled Polling Runner
    # -------------------------------------------------------------------------

    async def sync_single_source(self, source: IngestionSource) -> Dict[str, Any]:
        """Idempotently poll a single source with lock protection, rate-limit

        handling, checkpointing, and change detection.
        """
        if source.id not in self._poll_locks:
            self._poll_locks[source.id] = asyncio.Lock()

        # Prevent concurrent executions of the same source
        async with self._poll_locks[source.id]:
            now = datetime.now(timezone.utc)

            # Check rate limit window
            if source.rate_limit_reset_at and now < source.rate_limit_reset_at:
                logger.info(f"Source {source.id} rate-limited until {source.rate_limit_reset_at.isoformat()}. Skipping.")
                return {"status": "rate_limited", "signals": 0, "events": 0}

            try:
                # 1. Fetch documents into Live RAG (handles ETags, 304 Not Modified, and version preservation)
                ingest_res = await self.rag_pipeline.ingest_source(source)

                # 2. Fetch raw signals for ChangeDetector
                signals: List[RawSignal] = await self.ingestion_engine.poll_source(source)

                # Deduplicate against stored signals
                existing_signals = {s.content_hash: s for s in self.disk_store.load_all("raw_signals", RawSignal)}
                new_signals = [s for s in signals if s.content_hash not in existing_signals]
                for s in new_signals:
                    existing_signals[s.content_hash] = s
                if new_signals:
                    self.disk_store.save_all("raw_signals", list(existing_signals.values()))

                # 3. Detect technological changes
                new_events = self.change_detector.process_signals(new_signals)
                self._total_events += len(new_events)

                # 4. Evaluate monitoring rules on new events
                alerts_fired = 0
                for evt in new_events:
                    alerts = await self.evaluate_event(evt)
                    alerts_fired += len(alerts)

                # 5. Update Checkpoints & Successful Observability State
                source.last_synced_at = now
                source.last_successful_run_at = now
                source.last_status = "success" if (new_signals or ingest_res.get("ingested", 0) > 0) else "unchanged (304 / deduped)"
                source.error_message = None
                source.consecutive_failures = 0

                # Jitter: ±5% of interval to avoid harmonic request spikes
                jitter_seconds = random.uniform(-0.05, 0.05) * (source.refresh_interval_minutes * 60)
                next_interval = max(60, (source.refresh_interval_minutes * 60) + jitter_seconds)
                source.next_scheduled_run_at = now + timedelta(seconds=next_interval)

                self.disk_store.upsert_item("sources", source)
                self._total_runs += 1

                return {
                    "status": source.last_status,
                    "signals": len(new_signals),
                    "events": len(new_events),
                    "alerts": alerts_fired,
                }

            except Exception as e:
                self._total_errors += 1
                source.last_synced_at = now
                source.last_status = "error"
                source.error_message = str(e)
                source.consecutive_failures = getattr(source, "consecutive_failures", 0) + 1

                # Exponential backoff with rate limit protection
                backoff_multiplier = min(2 ** (source.consecutive_failures - 1), 16)
                backoff_minutes = min(source.refresh_interval_minutes * backoff_multiplier, 1440)
                source.next_scheduled_run_at = now + timedelta(minutes=backoff_minutes)

                if "429" in str(e) or "rate limit" in str(e).lower():
                    source.rate_limit_reset_at = now + timedelta(minutes=5)

                self.disk_store.upsert_item("sources", source)
                logger.error(f"Error in scheduled sync for source {source.id}: {e}", exc_info=True)
                return {"status": "error", "error": str(e)}

    async def run_due_sources(self) -> Dict[str, Any]:
        """Check all configured sources and poll those whose schedule is due."""
        if self._is_paused:
            return {"status": "paused", "sources_processed": 0}

        now = datetime.now(timezone.utc)
        self._last_tick_at = now
        sources = self.ingestion_engine.get_sources()

        due_sources = []
        for s in sources:
            if not s.enabled:
                continue
            # Overdue or never run
            if not s.next_scheduled_run_at or now >= s.next_scheduled_run_at:
                due_sources.append(s)

        if not due_sources:
            return {"status": "idle", "sources_due": 0}

        logger.info(f"Scheduled Ingestion: {len(due_sources)} sources due for execution.")
        results = await asyncio.gather(*(self.sync_single_source(src) for src in due_sources), return_exceptions=True)

        return {
            "status": "completed",
            "sources_processed": len(due_sources),
            "results": [r if isinstance(r, dict) else {"error": str(r)} for r in results],
        }

    # -------------------------------------------------------------------------
    # Scheduler Daemon Lifecycle
    # -------------------------------------------------------------------------

    async def _scheduler_loop(self, tick_seconds: int = 10) -> None:
        """Background daemon loop periodically evaluating due sources."""
        logger.info("ORACLE Scheduled Ingestion Daemon loop started.")
        while self._is_running:
            try:
                await self.run_due_sources()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler tick: {e}", exc_info=True)
            await asyncio.sleep(tick_seconds)
        logger.info("ORACLE Scheduled Ingestion Daemon loop stopped.")

    def start(self, tick_seconds: int = 10) -> None:
        """Start background scheduler loop."""
        if self._is_running:
            return
        self._is_running = True
        self._is_paused = False
        loop = asyncio.get_event_loop()
        self._loop_task = loop.create_task(self._scheduler_loop(tick_seconds))
        logger.info("Started background Ingestion Scheduler.")

    def stop(self) -> None:
        """Stop background scheduler loop gracefully."""
        self._is_running = False
        if self._loop_task:
            self._loop_task.cancel()
            self._loop_task = None
        logger.info("Stopped background Ingestion Scheduler.")

    def pause(self) -> None:
        """Pause polling execution."""
        self._is_paused = True
        logger.info("Paused Ingestion Scheduler.")

    def resume(self) -> None:
        """Resume polling execution."""
        self._is_paused = False
        logger.info("Resumed Ingestion Scheduler.")

    # -------------------------------------------------------------------------
    # Observability & Health
    # -------------------------------------------------------------------------

    def get_health(self) -> SchedulerHealth:
        """Assemble comprehensive health and schedule observability."""
        sources = self.ingestion_engine.get_sources()
        rules = self.list_rules()
        now = datetime.now(timezone.utc)

        source_statuses: List[SourceHealthStatus] = []
        for s in sources:
            is_limited = bool(s.rate_limit_reset_at and now < s.rate_limit_reset_at)
            source_statuses.append(
                SourceHealthStatus(
                    source_id=s.id,
                    name=s.name,
                    source_type=s.source_type.value,
                    url=s.url,
                    enabled=s.enabled,
                    refresh_interval_minutes=s.refresh_interval_minutes,
                    last_synced_at=s.last_synced_at,
                    last_successful_run_at=s.last_successful_run_at,
                    next_scheduled_run_at=s.next_scheduled_run_at,
                    last_status=s.last_status or "initialized",
                    error_message=s.error_message,
                    consecutive_failures=s.consecutive_failures,
                    etag=s.etag,
                    last_modified=s.last_modified,
                    is_rate_limited=is_limited,
                    rate_limit_reset_at=s.rate_limit_reset_at,
                )
            )

        return SchedulerHealth(
            is_running=self._is_running,
            is_paused=self._is_paused,
            scheduler_type="local_polling_monolith",
            last_tick_at=self._last_tick_at,
            active_sources_count=sum(1 for s in sources if s.enabled),
            active_rules_count=sum(1 for r in rules if r.enabled),
            jobs_scheduled=len(sources),
            total_runs_completed=self._total_runs,
            total_events_detected=self._total_events,
            total_investigations_triggered=self._total_investigations,
            total_errors=self._total_errors,
            sources=source_statuses,
        )
