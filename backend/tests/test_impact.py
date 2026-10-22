"""Unit tests for Impact Analyzer and report generation."""

import pytest
from app.change_detection.detector import ChangeDetector
from app.graph.store import KnowledgeGraphStore
from app.impact.analyzer import ImpactAnalyzer
from app.impact.report_generator import format_markdown_dossier
from app.llm.mock_adapter import MockLLMAdapter
from app.retrieval.vector_store import VectorStore
from app.schemas.event import ChangeCategory, EvidenceRef, IntelligenceEvent, SeverityLevel
from app.storage.disk_store import DiskStore


@pytest.mark.asyncio
async def test_generate_impact_report(test_graph_store, test_vector_store, test_disk_store, test_llm_adapter):
    analyzer = ImpactAnalyzer(
        graph_store=test_graph_store,
        vector_store=test_vector_store,
        disk_store=test_disk_store,
        llm_adapter=test_llm_adapter,
    )

    ev_ref = EvidenceRef(
        source_url="https://github.com/pydantic/pydantic/releases/tag/v2.8.0",
        source_type="github_release",
        title="Pydantic 2.8.0 Release Notes",
        snippet="Changed validator signature causing deprecation warning.",
        content_hash="test_ev_hash",
    )
    event = IntelligenceEvent(
        id="evt_test_pydantic",
        raw_signal_id="sig_1",
        category=ChangeCategory.DEPRECATION,
        severity=SeverityLevel.MEDIUM,
        title="Pydantic Validator Deprecation",
        summary="Validator signature update",
        primary_technology="pydantic",
        confidence=0.88,
        detection_rationale="Found deprecation notice",
        evidence=[ev_ref],
    )

    report = await analyzer.generate_impact_report(event=event, max_graph_depth=2)
    assert report.id.startswith("rpt_")
    assert report.event_id == event.id
    assert report.primary_technology == "pydantic"
    assert len(report.impacted_components) >= 1
    assert len(report.mitigation_playbook) >= 1
    assert report.llm_provenance["provider"] == "mock-test"

    # Test markdown formatting
    md = format_markdown_dossier(report)
    assert "# [ORACLE INTELLIGENCE DOSSIER]" in md
    assert "Knowledge Graph Blast Radius" in md
    assert "Actionable Mitigation Playbook" in md
