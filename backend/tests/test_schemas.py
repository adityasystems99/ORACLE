"""Unit tests for Pydantic schemas and serialization."""

from datetime import datetime, timezone
from app.schemas.event import ChangeCategory, EvidenceRef, IntelligenceEvent, SeverityLevel
from app.schemas.graph import EdgeType, NodeType, TemporalGraphEdge, TemporalGraphNode
from app.schemas.ingestion import IngestionSource, RawSignal, SourceType
from app.schemas.report import ImpactReport, MitigationAction


def test_raw_signal_serialization():
    sig = RawSignal(
        id="sig_test_1",
        source_id="src_1",
        source_type=SourceType.GITHUB_RELEASES,
        title="FastAPI v0.111.0 Released",
        url="https://github.com/fastapi/fastapi/releases/tag/0.111.0",
        content="Support Pydantic v2.7 and new features",
        content_hash="abc123hash",
    )
    dumped = sig.model_dump()
    assert dumped["id"] == "sig_test_1"
    assert dumped["source_type"] == "github_releases"


def test_intelligence_event_evidence():
    ev_ref = EvidenceRef(
        source_url="https://example.com/cve-1234",
        source_type="security_advisory",
        title="CVE-2024-9999",
        snippet="Remote code execution vulnerability detected.",
        content_hash="hash999",
    )
    event = IntelligenceEvent(
        id="evt_test_1",
        raw_signal_id="sig_test_1",
        category=ChangeCategory.SECURITY_VULNERABILITY,
        severity=SeverityLevel.CRITICAL,
        title="Critical RCE in Package",
        summary="Summary of vulnerability",
        primary_technology="fastapi",
        confidence=0.95,
        detection_rationale="Identified CVE advisory",
        evidence=[ev_ref],
    )
    assert event.severity == SeverityLevel.CRITICAL
    assert len(event.evidence) == 1
    assert event.evidence[0].content_hash == "hash999"


def test_temporal_graph_models():
    node = TemporalGraphNode(
        id="fastapi",
        name="FastAPI",
        node_type=NodeType.PACKAGE,
        ecosystem="python",
    )
    edge = TemporalGraphEdge(
        source="fastapi",
        target="pydantic",
        edge_type=EdgeType.DEPENDS_ON,
        version_constraint=">=2.0.0",
    )
    assert node.id == "fastapi"
    assert edge.edge_type == EdgeType.DEPENDS_ON
    assert edge.valid_to is None
