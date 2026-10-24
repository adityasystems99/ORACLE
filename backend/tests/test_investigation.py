"""Comprehensive unit and integration tests for ORACLE's Evidence-Grounded

Impact Investigation Engine and Provider API Deprecation Scenario.
"""

from datetime import datetime, timezone
import pytest
from app.graph.store import KnowledgeGraphStore
from app.impact.investigation_service import InvestigationService
from app.impact.ranking import FindingRankingEngine
from app.retrieval.rag_pipeline import RAGPipeline
from app.schemas.event import SeverityLevel
from app.schemas.graph import EdgeType, NodeType, RelationshipModality, TemporalGraphEdge, TemporalGraphNode
from app.schemas.investigation import (
    FindingPriority,
    ImpactCategory,
    ImpactStatus,
    InvestigationFinding,
    InvestigationRequest,
)
from app.schemas.rag import IngestedDocument, IngestionStatus


def test_investigation_ranking_rules():
    """Verify deterministic, transparent ranking logic and priority thresholding."""
    engine = FindingRankingEngine()

    finding_critical = InvestigationFinding(
        id="fnd_test_crit",
        summary="Critical breaking change in core dependency",
        affected_entity="test_service",
        affected_entity_name="Test Service",
        affected_entity_type="Product",
        impact_category=ImpactCategory.BREAKING_CHANGE,
        impact_status=ImpactStatus.CONFIRMED,
        severity=SeverityLevel.CRITICAL,
        priority=FindingPriority.P2_MEDIUM,
        severity_and_priority_explanation="",
        evidence_and_sources=[],
        supporting_graph_path=["test_service -> dep"],
        graph_path_explanation="Direct dependency",
        known_facts=["Empirical link recorded"],
        inferences_and_assumptions=[],
        confidence_limitations=[],
        suggested_next_steps=[],
        last_verified_timestamp=datetime.now(timezone.utc),
        internal_verification_note="Unverified private code",
        score=0.0,
    )

    score, priority, rules = engine.score_finding(finding_critical, depth=1)
    assert score >= 75.0
    assert priority == FindingPriority.P0_CRITICAL
    assert any("CRITICAL" in r for r in rules)
    assert any("CONFIRMED" in r for r in rules)
    assert any("direct 1-hop" in r for r in rules)

    # Test superseded finding penalty
    finding_superseded = finding_critical.model_copy()
    finding_superseded.impact_status = ImpactStatus.SUPERSEDED
    score_super, priority_super, rules_super = engine.score_finding(finding_superseded, depth=1)
    assert score_super < score
    assert any("superseded" in r.lower() for r in rules_super)


@pytest.mark.asyncio
async def test_provider_api_deprecation_scenario(test_graph_store: KnowledgeGraphStore, test_disk_store, test_vector_store):
    """End-to-End Demonstration:

    1. Ingest official provider API deprecation notice into Live RAG.
    2. Register API entity and downstream consuming product in Temporal Knowledge Graph.
    3. Run unified InvestigationService.
    4. Verify grounded findings, severity, priority, provenance, and causation disclaimers.
    """
    rag_pipeline = RAGPipeline(disk_store=test_disk_store, vector_store=test_vector_store)

    # Step 1: Ingest provider deprecation announcement into Live RAG
    deprecation_doc = IngestedDocument(
        id="doc_stripe_deprecation_2026",
        source_id="src_stripe_official",
        source_url="https://stripe.com/docs/upgrades/charges-api-deprecation",
        publisher="Stripe Official Engineering",
        title="Stripe Charges API v1 Sunset Notice",
        content="Official Announcement: Stripe Charges API v1 is deprecated as of 2026-06-01 and will be sunset. All connected services must migrate to PaymentIntents v2 API to avoid request rejections.",
        content_hash="hash_stripe_deprecate_v1",
        publication_timestamp=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
        status=IngestionStatus.SUCCESS,
    )
    await rag_pipeline.ingest_documents([deprecation_doc])

    # Step 2: Register API entity and consuming downstream product in knowledge graph
    test_graph_store.add_node(
        TemporalGraphNode(
            id="stripe-charges-v1",
            name="Stripe Charges API v1",
            node_type=NodeType.API,
            ecosystem="cloud",
            description="Legacy Stripe card processing endpoint",
        )
    )
    test_graph_store.add_node(
        TemporalGraphNode(
            id="billing-worker-service",
            name="Billing Worker Service",
            node_type=NodeType.PRODUCT,
            ecosystem="python",
            description="Internal order billing microservice",
        )
    )

    # Add active USES edge between consumer and deprecated API
    test_graph_store.add_edge(
        TemporalGraphEdge(
            id="edge_billing_uses_stripe_v1",
            source="billing-worker-service",
            target="stripe-charges-v1",
            edge_type=EdgeType.USES,
            modality=RelationshipModality.OBSERVED,
            valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
            valid_until=None,
            evidence_ids=["doc_stripe_deprecation_2026"],
            source_url="https://stripe.com/docs/upgrades/charges-api-deprecation",
        ),
        supersede_existing=False,
    )

    # Step 3: Run unified investigation
    service = InvestigationService(graph_store=test_graph_store, rag_pipeline=rag_pipeline)

    request = InvestigationRequest(
        query="Stripe Charges API v1 deprecation impact on billing service",
        target_technology="stripe-charges-v1",
        max_graph_depth=2,
    )

    report = await service.investigate(request)

    # Step 4: Validate generated report against reliability rules
    assert report.total_findings >= 1
    assert "stripe-charges-v1" in report.executive_summary

    # Find the finding for billing-worker-service
    billing_finding = next((f for f in report.findings if f.affected_entity == "billing-worker-service"), None)
    assert billing_finding is not None
    assert billing_finding.affected_entity_name == "Billing Worker Service"
    assert billing_finding.impact_category == ImpactCategory.API_DEPRECATION
    assert billing_finding.impact_status == ImpactStatus.CONFIRMED

    # Reliability Rule: Priority and severity must be explained
    assert billing_finding.priority in (FindingPriority.P0_CRITICAL, FindingPriority.P1_HIGH)
    assert "Score:" in billing_finding.severity_and_priority_explanation

    # Reliability Rule: Supporting evidence and URLs must be grounded
    assert len(billing_finding.evidence_and_sources) >= 1
    assert "stripe.com/docs/upgrades/charges-api-deprecation" in billing_finding.evidence_and_sources[0].source_url
    assert billing_finding.evidence_and_sources[0].publisher == "Stripe Official Engineering"

    # Reliability Rule: Causation disclaimer must be explicitly stated
    assert "A graph connection indicates exposure/dependency, not proven causal impact" in billing_finding.causation_disclaimer

    # Reliability Rule: Private repository unverified notice
    assert "UNVERIFIABLE_WITHOUT_PRIVATE_CODE" in billing_finding.internal_verification_note

    # Reliability Rule: Concrete next steps
    assert len(billing_finding.suggested_next_steps) >= 2


def test_distinguish_confirmed_from_potential_impacts(test_graph_store: KnowledgeGraphStore, test_disk_store, test_vector_store):
    """Requirement: Distinguish confirmed impacts from potential impacts."""
    rag_pipeline = RAGPipeline(disk_store=test_disk_store, vector_store=test_vector_store)
    service = InvestigationService(graph_store=test_graph_store, rag_pipeline=rag_pipeline)

    # fastapi directly depends on pydantic (depth=1, observed) -> CONFIRMED
    # project_oracle_copilot depends on fastapi which depends on pydantic (depth=2) -> POTENTIAL
    import asyncio
    report = asyncio.run(
        service.investigate(
            InvestigationRequest(
                query="Pydantic core breaking change",
                target_technology="pydantic",
                max_graph_depth=3,
                max_candidates=20,
            )
        )
    )

    confirmed_entities = [f.affected_entity for f in report.findings if f.impact_status == ImpactStatus.CONFIRMED]
    potential_entities = [f.affected_entity for f in report.findings if f.impact_status == ImpactStatus.POTENTIAL]

    assert "fastapi" in confirmed_entities
    # Transitive dependent is marked potential
    assert "project_oracle_copilot" in potential_entities


@pytest.mark.asyncio
async def test_superseded_claims_detection_across_versions(test_graph_store: KnowledgeGraphStore, test_disk_store, test_vector_store):
    """Requirement: Detect changed content, check superseded claims and preserve history."""
    rag_pipeline = RAGPipeline(disk_store=test_disk_store, vector_store=test_vector_store)

    # Ingest version 1 of document
    doc_v1 = IngestedDocument(
        id="doc_version_check",
        source_id="src_vendor",
        source_url="https://vendor.org/roadmap",
        publisher="Vendor Org",
        title="Vendor API Roadmap",
        content="Version 1: API v1 is officially supported until 2028 with zero planned deprecations.",
        content_hash="hash_v1_vendor",
        publication_timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        status=IngestionStatus.SUCCESS,
    )
    await rag_pipeline.ingest_documents([doc_v1])

    # Ingest version 2 with changed content hash -> triggers version mutation archiving
    doc_v2 = IngestedDocument(
        id="doc_version_check",
        source_id="src_vendor",
        source_url="https://vendor.org/roadmap",
        publisher="Vendor Org",
        title="Vendor API Roadmap (Updated)",
        content="Version 2: Urgent update. API v1 will be deprecated prematurely in 2026.",
        content_hash="hash_v2_vendor_mutated",
        publication_timestamp=datetime(2026, 2, 1, tzinfo=timezone.utc),
        status=IngestionStatus.SUCCESS,
    )
    await rag_pipeline.ingest_documents([doc_v2])

    service = InvestigationService(graph_store=test_graph_store, rag_pipeline=rag_pipeline)
    report = await service.investigate(InvestigationRequest(query="Vendor API roadmap update", include_historical=True))

    assert len(report.superseded_claims) >= 1
    assert "v1 was updated to v2" in report.superseded_claims[0]


def test_api_impact_investigate_and_retrieve_endpoints(client):
    """Test FastAPI POST /api/impact/investigate and GET /api/impact/investigations endpoints."""
    payload = {
        "query": "Pydantic breaking change in FastAPI query parameters",
        "target_technology": "pydantic",
        "max_graph_depth": 2,
        "max_candidates": 5,
        "include_historical": True,
    }

    # 1. POST /api/impact/investigate
    res_post = client.post("/api/impact/investigate", json=payload)
    assert res_post.status_code == 200
    report_data = res_post.json()
    assert "id" in report_data
    assert report_data["total_findings"] >= 1
    report_id = report_data["id"]

    # 2. GET /api/impact/investigations
    res_list = client.get("/api/impact/investigations")
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert len(list_data) >= 1
    assert any(r["id"] == report_id for r in list_data)

    # 3. GET /api/impact/investigations/{report_id}
    res_get = client.get(f"/api/impact/investigations/{report_id}")
    assert res_get.status_code == 200
    single_data = res_get.json()
    assert single_data["id"] == report_id
    assert len(single_data["findings"]) >= 1
    assert single_data["findings"][0]["causation_disclaimer"] is not None
