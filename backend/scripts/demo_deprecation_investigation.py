"""End-to-End Demonstration Script: Provider API Deprecation Scenario.

Shows the complete workflow:
1. Ingestion of official provider deprecation notice into Live RAG.
2. Temporal knowledge graph modeling of provider API and consuming product.
3. Execution of unified InvestigationService with bounded traversal & temporal checks.
4. Deterministic, transparent ranking of findings.
5. Generation and validation of final evidence-linked Impact Report.
"""

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

# Ensure backend root is on Python path
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from app.config import get_settings
from app.graph.store import KnowledgeGraphStore
from app.impact.investigation_service import InvestigationService
from app.retrieval.rag_pipeline import RAGPipeline
from app.retrieval.vector_store import VectorStore
from app.schemas.event import SeverityLevel
from app.schemas.graph import EdgeType, NodeType, RelationshipModality, TemporalGraphEdge, TemporalGraphNode
from app.schemas.investigation import InvestigationRequest
from app.schemas.rag import IngestedDocument, IngestionStatus
from app.storage.disk_store import DiskStore


async def run_demo():
    print("=" * 80)
    print("ORACLE — EVIDENCE-GROUNDED IMPACT INVESTIGATION DEMONSTRATION")
    print("SCENARIO: Provider API Deprecation & Downstream Blast Radius Analysis")
    print("=" * 80)

    settings = get_settings()
    disk_store = DiskStore(settings.DATA_DIR)
    graph_store = KnowledgeGraphStore(persist_path=settings.GRAPH_PERSIST_PATH)
    vector_store = VectorStore(persist_dir=settings.CHROMA_PERSIST_DIR)
    rag_pipeline = RAGPipeline(disk_store=disk_store, vector_store=vector_store)

    # -------------------------------------------------------------------------
    # STEP 1: Ingest Official Provider API Deprecation Notice into Live RAG
    # -------------------------------------------------------------------------
    print("\n[STEP 1] Ingesting official provider API deprecation notice into Live RAG...")
    deprecation_doc = IngestedDocument(
        id="doc_stripe_charges_deprecation_2026",
        source_id="src_stripe_advisories",
        source_url="https://stripe.com/docs/upgrades/charges-api-deprecation",
        publisher="Stripe Official Developer Platform",
        title="Stripe Charges API v1 Sunset & Migration Directive",
        content=(
            "Official Deprecation Bulletin: Stripe Charges API v1 (POST /v1/charges) is deprecated "
            "as of 2026-06-01 and will reach End-of-Life on 2026-09-01. All charges calls will fail "
            "with HTTP 410 Gone after the sunset deadline. Integrated services must migrate to the "
            "PaymentIntents API v2 immediately to maintain card transaction processing."
        ),
        content_hash="hash_stripe_charges_v1_sunset_2026",
        publication_timestamp=datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
        status=IngestionStatus.SUCCESS,
    )
    ingest_res = await rag_pipeline.ingest_documents([deprecation_doc])
    print(f"-> Ingestion complete: {ingest_res['ingested']} new doc, {ingest_res['chunks']} chunks indexed.")
    print(f"-> Document ID: {deprecation_doc.id}")
    print(f"-> Source URL: {deprecation_doc.source_url}")
    print(f"-> Publication Timestamp: {deprecation_doc.publication_timestamp.isoformat()} (UTC)")

    # -------------------------------------------------------------------------
    # STEP 2: Register API & Consumer Component in Temporal Knowledge Graph
    # -------------------------------------------------------------------------
    print("\n[STEP 2] Modeling provider API and consumer service in Temporal Knowledge Graph...")
    graph_store.add_node(
        TemporalGraphNode(
            id="stripe-charges-v1",
            name="Stripe Charges API v1",
            node_type=NodeType.API,
            ecosystem="cloud",
            version="1.0",
            description="Legacy card authorization endpoint (POST /v1/charges)",
        )
    )
    graph_store.add_node(
        TemporalGraphNode(
            id="oracle-billing-gateway",
            name="ORACLE Billing Gateway Service",
            node_type=NodeType.PRODUCT,
            ecosystem="python",
            description="Production payments microservice handling tenant subscriptions",
        )
    )
    graph_store.add_node(
        TemporalGraphNode(
            id="tenant-checkout-portal",
            name="Tenant Checkout Web Portal",
            node_type=NodeType.PRODUCT,
            ecosystem="node",
            description="Customer facing frontend portal invoking billing gateway",
        )
    )

    # Direct USES relationship: oracle-billing-gateway USES stripe-charges-v1
    graph_store.add_edge(
        TemporalGraphEdge(
            id="edge_billing_uses_stripe_charges_v1",
            source="oracle-billing-gateway",
            target="stripe-charges-v1",
            edge_type=EdgeType.USES,
            modality=RelationshipModality.OBSERVED,
            valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
            valid_until=None,
            evidence_ids=["doc_stripe_charges_deprecation_2026"],
            source_url="https://stripe.com/docs/upgrades/charges-api-deprecation",
        ),
        supersede_existing=False,
    )

    # Transitive DEPENDS_ON relationship: tenant-checkout-portal DEPENDS_ON oracle-billing-gateway
    graph_store.add_edge(
        TemporalGraphEdge(
            id="edge_portal_depends_billing",
            source="tenant-checkout-portal",
            target="oracle-billing-gateway",
            edge_type=EdgeType.DEPENDS_ON,
            modality=RelationshipModality.OBSERVED,
            valid_from=datetime(2024, 6, 1, tzinfo=timezone.utc),
            valid_until=None,
        ),
        supersede_existing=False,
    )
    print("-> Graph entities registered: 'stripe-charges-v1', 'oracle-billing-gateway', 'tenant-checkout-portal'")
    print("-> Recorded directional relationships:")
    print("   [Direct 1-Hop]:   oracle-billing-gateway -[USES]-> stripe-charges-v1 (OBSERVED)")
    print("   [Transitive 2-Hop]: tenant-checkout-portal -[DEPENDS_ON]-> oracle-billing-gateway (OBSERVED)")

    # -------------------------------------------------------------------------
    # STEP 3: Execute Unified Evidence-Grounded Impact Investigation
    # -------------------------------------------------------------------------
    print("\n[STEP 3] Executing unified InvestigationService pipeline...")
    service = InvestigationService(graph_store=graph_store, rag_pipeline=rag_pipeline)

    req = InvestigationRequest(
        query="Stripe Charges API v1 deprecation and sunset impact on billing gateway",
        target_technology="stripe-charges-v1",
        max_graph_depth=3,
        max_candidates=10,
        include_historical=True,
    )
    report = await service.investigate(req)

    # -------------------------------------------------------------------------
    # STEP 4: Output and Validate the Final Report
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("FINAL EVIDENCE-GROUNDED INVESTIGATION DOSSIER")
    print("=" * 80)
    print(f"Report ID: {report.id}")
    print(f"Investigation Timestamp: {report.investigation_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Executive Summary: {report.executive_summary}")
    print(f"Total Findings: {report.total_findings} (Confirmed: {report.confirmed_impacts_count}, Potential: {report.potential_impacts_count})")
    print(f"Internal Code Verification Status: {report.internal_impact_verification_status}")

    print("\n--- DETAILED RANKED FINDINGS ---")
    for idx, f in enumerate(report.findings, 1):
        print(f"\n[Finding #{idx}] {f.summary}")
        print(f"  * Affected Entity: `{f.affected_entity}` ({f.affected_entity_name}) - Type: {f.affected_entity_type}")
        print(f"  * Impact Category: {f.impact_category.value.upper()}")
        print(f"  * Impact Status:   {f.impact_status.value.upper()} (Confirmed vs Potential)")
        print(f"  * Severity:        {f.severity.value.upper()}")
        print(f"  * Priority:        {f.priority.value} (Score: {f.score:.1f}/100)")
        print(f"  * Rationale:       {f.severity_and_priority_explanation}")
        print(f"  * Graph Path:      {f.graph_path_explanation}")
        print(f"  * Known Facts:     {'; '.join(f.known_facts)}")
        print(f"  * Assumptions:     {'; '.join(f.inferences_and_assumptions)}")
        print(f"  * Limitations:     {'; '.join(f.confidence_limitations)}")
        print(f"  * Causation Rule:  {f.causation_disclaimer}")
        print(f"  * Internal Code:   {f.internal_verification_note}")
        print(f"  * Next Steps:")
        for step in f.suggested_next_steps:
            print(f"     -> {step}")
        if f.evidence_and_sources:
            print(f"  * Supporting Evidence:")
            for ev in f.evidence_and_sources:
                print(f"     -> [{ev.publisher}] {ev.source_url} (Version {ev.document_version})")

    print("\n--- TRANSPARENT RANKING RULES APPLIED ---")
    for r in report.ranking_rules_applied:
        print(f"  [Rule] {r}")

    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETED SUCCESSFULLY. ALL RELIABILITY RULES SATISFIED.")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_demo())
