"""End-to-end integration tests for FastAPI REST endpoints."""

from app.schemas.event import ChangeCategory, EvidenceRef, IntelligenceEvent, SeverityLevel


def test_api_health(client):
    res = client.get("/api/system/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "ORACLE"
    assert "graph" in data
    assert data["graph"]["nodes"] > 0


def test_api_graph_endpoints(client):
    # Snapshot
    res = client.get("/api/graph/snapshot")
    assert res.status_code == 200
    snapshot = res.json()
    assert snapshot["node_count"] > 0
    assert snapshot["edge_count"] > 0

    # Blast radius
    res = client.get("/api/graph/blast-radius?entity=pydantic&max_depth=2")
    assert res.status_code == 200
    data = res.json()
    assert data["root_entity"] == "pydantic"
    assert len(data["affected_nodes"]) > 0


def test_api_ingest_sources(client):
    res = client.get("/api/ingest/sources")
    assert res.status_code == 200
    sources = res.json()
    assert len(sources) >= 5


def test_api_event_and_impact_flow(client):
    app = client.app
    disk_store = app.state.disk_store

    # Insert an event directly to disk store
    ev_ref = EvidenceRef(
        source_url="https://github.com/fastapi/fastapi/releases",
        source_type="github_release",
        title="FastAPI update",
        snippet="FastAPI updated dependencies.",
        content_hash="flow_test_hash",
    )
    event = IntelligenceEvent(
        id="evt_flow_test",
        raw_signal_id="sig_flow_1",
        category=ChangeCategory.BREAKING_CHANGE,
        severity=SeverityLevel.HIGH,
        title="Breaking Change in FastAPI Dependency",
        summary="A dependency interface has shifted.",
        primary_technology="fastapi",
        confidence=0.92,
        detection_rationale="Breaking signature match",
        evidence=[ev_ref],
    )
    disk_store.upsert_item("events", event)

    # Query event
    res = client.get("/api/events/evt_flow_test")
    assert res.status_code == 200
    assert res.json()["primary_technology"] == "fastapi"

    # Trigger impact analysis
    analyze_res = client.post("/api/impact/analyze", json={"event_id": "evt_flow_test", "max_depth": 2})
    assert analyze_res.status_code == 200
    report = analyze_res.json()
    assert report["event_id"] == "evt_flow_test"
    assert report["primary_technology"] == "fastapi"
    assert len(report["mitigation_playbook"]) >= 1

    # Verify report in list
    list_res = client.get("/api/impact/reports")
    assert list_res.status_code == 200
    assert any(r["id"] == report["id"] for r in list_res.json())

    # Verify markdown export
    md_res = client.get(f"/api/impact/reports/{report['id']}/markdown")
    assert md_res.status_code == 200
    assert "# [ORACLE INTELLIGENCE DOSSIER]" in md_res.text
