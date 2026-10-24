"""Comprehensive unit and integration tests for Temporal Graph RAG,

relationship provenance, temporal filtering, bounded traversal, cycle handling,
and evidence-backed path generation.
"""

from datetime import datetime, timedelta, timezone
import pytest
from app.graph.store import KnowledgeGraphStore
from app.graph.temporal import is_edge_active_at
from app.retrieval.rag_pipeline import RAGPipeline
from app.retrieval.temporal_graph_rag import TemporalGraphRAGEngine
from app.schemas.graph import (
    EdgeType,
    NodeType,
    RelationshipModality,
    TemporalGraphEdge,
    TemporalGraphNode,
    TemporalGraphRAGQuery,
)
from app.schemas.rag import IngestedDocument, IngestionStatus


def test_seed_graph_initialization(test_graph_store: KnowledgeGraphStore):
    """Verify seed graph initializes with all core entities and relations."""
    snapshot = test_graph_store.get_snapshot()
    assert snapshot.node_count >= 15
    assert snapshot.edge_count >= 10
    assert "fastapi" in test_graph_store.graph
    assert "pydantic" in test_graph_store.graph
    assert "tiangolo" in test_graph_store.graph


def test_all_required_entity_and_relationship_types(test_graph_store: KnowledgeGraphStore):
    """Requirement: Support Company, Product, Technology, API, SoftwareVersion,

    Release, SecurityAdvisory, Event, Project, Dependency, EvidenceDocument
    and PRODUCES, USES, DEPENDS_ON, AFFECTS, SUPERSEDES, ANNOUNCES, DOCUMENTED_BY, VERSION_OF.
    """
    types_present = {data.get("node_type") for _, data in test_graph_store.graph.nodes(data=True)}
    # Convert all to strings or enum values
    type_strings = {NodeType(t).value for t in types_present}

    assert NodeType.COMPANY.value in type_strings
    assert NodeType.PRODUCT.value in type_strings
    assert NodeType.TECHNOLOGY.value in type_strings
    assert NodeType.API.value in type_strings
    assert NodeType.SOFTWARE_VERSION.value in type_strings
    assert NodeType.RELEASE.value in type_strings
    assert NodeType.SECURITY_ADVISORY.value in type_strings
    assert NodeType.EVENT.value in type_strings
    assert NodeType.PROJECT.value in type_strings
    assert NodeType.DEPENDENCY.value in type_strings
    assert NodeType.EVIDENCE_DOCUMENT.value in type_strings

    edges_present = {data.get("edge_type") for _, _, data in test_graph_store.graph.edges(data=True)}
    edge_strings = {EdgeType(e).value for e in edges_present}

    assert EdgeType.PRODUCES.value in edge_strings
    assert EdgeType.USES.value in edge_strings
    assert EdgeType.DEPENDS_ON.value in edge_strings
    assert EdgeType.AFFECTS.value in edge_strings
    assert EdgeType.SUPERSEDES.value in edge_strings
    assert EdgeType.ANNOUNCES.value in edge_strings
    assert EdgeType.DOCUMENTED_BY.value in edge_strings
    assert EdgeType.VERSION_OF.value in edge_strings


def test_blast_radius_pydantic_change(test_graph_store: KnowledgeGraphStore):
    """Verify that when Pydantic has a breaking change, downstream dependents

    (FastAPI, SQLModel, ORACLE copilot) are discovered in the blast radius.
    """
    blast = test_graph_store.calculate_blast_radius("pydantic", max_depth=3)
    assert blast.root_entity == "pydantic"
    assert blast.direct_dependents_count >= 1

    affected_ids = [n.node_id for n in blast.affected_nodes]
    assert "fastapi" in affected_ids
    assert "sqlmodel" in affected_ids
    # Transitive dependent: project_oracle_copilot depends on fastapi which depends on pydantic
    assert "project_oracle_copilot" in affected_ids


def test_graph_persistence_and_safe_reload(temp_dir):
    """Requirement: Persist and reload graph data safely with exact attributes."""
    graph_path = temp_dir / "persisted_graph.json"
    store1 = KnowledgeGraphStore(persist_path=graph_path)

    store1.add_node(
        TemporalGraphNode(
            id="custom_service",
            name="Custom Service",
            node_type=NodeType.PRODUCT,
            ecosystem="cloud",
            evidence_ids=["ev_custom_doc_1"],
        )
    )
    store1.add_edge(
        TemporalGraphEdge(
            id="edge_custom_1",
            source="custom_service",
            target="fastapi",
            edge_type=EdgeType.DEPENDS_ON,
            modality=RelationshipModality.OBSERVED,
            evidence_ids=["ev_custom_doc_1"],
            source_url="https://internal.corp/manifest",
        )
    )

    # Re-instantiate from disk
    store2 = KnowledgeGraphStore(persist_path=graph_path)
    assert "custom_service" in store2.graph
    node_data = store2.graph.nodes["custom_service"]
    assert node_data["name"] == "Custom Service"
    assert "ev_custom_doc_1" in node_data["evidence_ids"]

    # Verify edge attributes preserved
    edge_data = store2.graph.get_edge_data("custom_service", "fastapi")
    assert "edge_custom_1" in edge_data
    saved_edge = edge_data["edge_custom_1"]
    assert saved_edge["edge_type"] == EdgeType.DEPENDS_ON.value
    assert saved_edge["modality"] == RelationshipModality.OBSERVED.value
    assert saved_edge["source_url"] == "https://internal.corp/manifest"


def test_historical_relationship_preservation(temp_dir):
    """Requirement: Preserve historical relationships instead of silently overwriting them."""
    graph_path = temp_dir / "historical_graph.json"
    store = KnowledgeGraphStore(persist_path=graph_path)

    t0 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Add initial relationship (FastAPI -> Pydantic v1)
    edge_v1 = TemporalGraphEdge(
        id="edge_fa_pyd_v1",
        source="fastapi",
        target="pydantic",
        edge_type=EdgeType.DEPENDS_ON,
        version_constraint="<2.0.0",
        valid_from=t0,
        valid_until=None,
        modality=RelationshipModality.OBSERVED,
    )
    store.add_edge(edge_v1, supersede_existing=False)

    # Supersede with newer relationship at t1 (FastAPI -> Pydantic v2)
    edge_v2 = TemporalGraphEdge(
        id="edge_fa_pyd_v2",
        source="fastapi",
        target="pydantic",
        edge_type=EdgeType.DEPENDS_ON,
        version_constraint=">=2.0.0",
        valid_from=t1,
        valid_until=None,
        modality=RelationshipModality.OBSERVED,
    )
    store.add_edge(edge_v2, supersede_existing=True)

    # Verify that BOTH edges exist in MultiDiGraph
    edge_dict = store.graph.get_edge_data("fastapi", "pydantic")
    assert "edge_fa_pyd_v1" in edge_dict
    assert "edge_fa_pyd_v2" in edge_dict

    # Check that historical edge was closed at t1
    hist_edge = edge_dict["edge_fa_pyd_v1"]
    assert hist_edge["valid_until"] is not None
    assert hist_edge["version_constraint"] == "<2.0.0"

    # Current edge remains open
    active_edge = edge_dict["edge_fa_pyd_v2"]
    assert active_edge["valid_until"] is None
    assert active_edge["version_constraint"] == ">=2.0.0"


def test_temporal_filtering_active_vs_historical(temp_dir):
    """Requirement: Apply temporal filters so outdated evidence is not mistaken for current truth."""
    graph_path = temp_dir / "temporal_filter_graph.json"
    store = KnowledgeGraphStore(persist_path=graph_path)

    past_date = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    transition_date = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    current_date = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    edge_past = TemporalGraphEdge(
        id="edge_legacy_dep",
        source="pkg_a",
        target="pkg_b",
        edge_type=EdgeType.DEPENDS_ON,
        valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        valid_until=transition_date,
    )
    edge_new = TemporalGraphEdge(
        id="edge_new_dep",
        source="pkg_a",
        target="pkg_b",
        edge_type=EdgeType.DEPENDS_ON,
        valid_from=transition_date,
        valid_until=None,
    )

    store.add_edge(edge_past, supersede_existing=False)
    store.add_edge(edge_new, supersede_existing=False)

    # 1. At past date: edge_past is ACTIVE, edge_new is INACTIVE
    assert is_edge_active_at(edge_past, as_of=past_date) is True
    assert is_edge_active_at(edge_new, as_of=past_date) is False

    # 2. At current date: edge_past is INACTIVE (historical), edge_new is ACTIVE
    assert is_edge_active_at(edge_past, as_of=current_date) is False
    assert is_edge_active_at(edge_new, as_of=current_date) is True

    # Traversal at current date with active_only=True should only follow edge_new
    traversal = store.traverse(root_id="pkg_a", as_of=current_date, active_only=True)
    traversed_ids = [e.id for e in traversal.edges]
    assert "edge_new_dep" in traversed_ids
    assert "edge_legacy_dep" not in traversed_ids


def test_bounded_traversal_depth_and_node_limits(test_graph_store: KnowledgeGraphStore):
    """Requirement: Implement bounded graph traversal with configurable depth and node limits."""
    # Depth 1 test: should only reach direct neighbors
    traversal_depth1 = test_graph_store.traverse(root_id="fastapi", max_depth=1, max_nodes=50)
    visited_depth1 = {n.id for n in traversal_depth1.nodes}
    assert "fastapi" in visited_depth1
    assert "pydantic" in visited_depth1
    # pydantic-core is 2 hops away from fastapi (fastapi -> pydantic -> pydantic-core)
    assert "pydantic-core" not in visited_depth1

    # Node limit test: max_nodes=3 should never return more than 3 visited nodes
    traversal_limited = test_graph_store.traverse(root_id="fastapi", max_depth=4, max_nodes=3)
    assert len(traversal_limited.nodes) <= 3


def test_cycle_handling_prevention(temp_dir):
    """Requirement: Cycle handling in bounded traversal without infinite loops."""
    graph_path = temp_dir / "cyclic_graph.json"
    store = KnowledgeGraphStore(persist_path=graph_path)

    # Create cycle: A -> B -> C -> A
    store.add_edge(TemporalGraphEdge(source="node_a", target="node_b", edge_type=EdgeType.DEPENDS_ON), supersede_existing=False)
    store.add_edge(TemporalGraphEdge(source="node_b", target="node_c", edge_type=EdgeType.DEPENDS_ON), supersede_existing=False)
    store.add_edge(TemporalGraphEdge(source="node_c", target="node_a", edge_type=EdgeType.DEPENDS_ON), supersede_existing=False)

    # Traversal should complete quickly and detect the cycle without infinite recursion
    traversal = store.traverse(root_id="node_a", max_depth=5, max_nodes=20)
    assert traversal.cycles_detected >= 1
    node_ids = {n.id for n in traversal.nodes}
    assert node_ids == {"node_a", "node_b", "node_c"}

    # Path finding should also avoid cyclic loops
    paths = store.find_explainable_paths(source_id="node_a", target_id="node_c", max_depth=5)
    assert len(paths) >= 1
    for p in paths:
        # Every step in path must be unique to prevent infinite cycles
        visited_nodes = [s.from_node for s in p.steps] + [p.steps[-1].to_node]
        assert len(visited_nodes) == len(set(visited_nodes))


def test_explainable_paths_with_evidence_provenance(test_graph_store: KnowledgeGraphStore):
    """Requirement: Return explainable paths showing how an event connects to an affected entity,

    and verify that claimed relationships can be traced to supporting evidence.
    """
    # Find path from advisory to project_oracle_copilot:
    # cve-2024-fastapi-security-advisory AFFECTS fastapi
    # project_oracle_copilot DEPENDS_ON fastapi
    paths = test_graph_store.find_explainable_paths(
        source_id="cve-2024-fastapi-security-advisory",
        target_id="project_oracle_copilot",
        max_depth=4,
    )
    assert len(paths) >= 1
    path = paths[0]
    assert path.source_id == "cve-2024-fastapi-security-advisory"
    assert path.target_id == "project_oracle_copilot"
    assert len(path.steps) >= 2
    assert "doc_cve_advisory_2024" in path.evidence_citations
    assert len(path.overall_explanation) > 10


def test_relationship_modality_distinction(test_graph_store: KnowledgeGraphStore):
    """Requirement: Distinguish observed relationships from inferred or hypothetical relationships."""
    # Direct 1-hop path with explicit evidence is OBSERVED
    paths = test_graph_store.find_explainable_paths(
        source_id="rel_fastapi_0111",
        target_id="doc_fastapi_rel_0111",
        max_depth=1,
    )
    assert len(paths) >= 1
    assert paths[0].path_modality == RelationshipModality.OBSERVED

    # Multi-hop transitive dependency path is INFERRED
    paths_multi = test_graph_store.find_explainable_paths(
        source_id="project_oracle_copilot",
        target_id="pydantic-core",
        max_depth=3,
    )
    assert len(paths_multi) >= 1
    assert paths_multi[0].path_modality == RelationshipModality.INFERRED


def test_never_invent_unverified_dependencies(test_graph_store: KnowledgeGraphStore):
    """Requirement: Never invent internal dependencies that have not been provided or verified."""
    # Add an isolated entity with 0 connections
    isolated_node = TemporalGraphNode(
        id="isolated_proprietary_system",
        name="Isolated Proprietary System",
        node_type=NodeType.PRODUCT,
    )
    test_graph_store.add_node(isolated_node)

    # Blast radius should be strictly 0 affected nodes
    blast = test_graph_store.calculate_blast_radius("isolated_proprietary_system", max_depth=3)
    assert blast.direct_dependents_count == 0
    assert blast.transitive_dependents_count == 0
    assert len(blast.affected_nodes) == 0

    # Paths to any other node should be empty
    paths = test_graph_store.find_explainable_paths(
        source_id="isolated_proprietary_system",
        target_id="fastapi",
        max_depth=4,
    )
    assert len(paths) == 0


@pytest.mark.asyncio
async def test_temporal_graph_rag_investigate_engine(test_graph_store: KnowledgeGraphStore, test_disk_store, test_vector_store):
    """Requirement: Combine vector search results with relevant graph neighborhoods."""
    rag_pipeline = RAGPipeline(disk_store=test_disk_store, vector_store=test_vector_store)

    # Ingest evidence document into RAG pipeline
    sample_doc = IngestedDocument(
        id="doc_pydantic_alert",
        source_id="src_official",
        source_url="https://pydantic.dev/blog/v2-7-0",
        publisher="Pydantic Inc.",
        title="Pydantic v2.7.0 Breaking Core Serialization Bug",
        content="Critical serialization issue detected in Pydantic v2.7.0 affecting FastAPI query parsing.",
        content_hash="hash_pydantic_alert_123",
        publication_timestamp=datetime(2026, 4, 10, 10, 0, 0, tzinfo=timezone.utc),
        status=IngestionStatus.SUCCESS,
    )
    await rag_pipeline.ingest_documents([sample_doc])

    engine = TemporalGraphRAGEngine(graph_store=test_graph_store, rag_pipeline=rag_pipeline)

    query = TemporalGraphRAGQuery(
        query="What is the impact of Pydantic serialization bug on connected products?",
        max_depth=3,
        top_k_evidence=3,
    )

    response = await engine.investigate(query)
    assert "pydantic" in response.anchored_entities
    assert len(response.evidence_passages) >= 1
    assert response.verified_evidence_count >= 1
    assert len(response.affected_nodes) >= 1
    # Check that FastAPI and SQLModel are flagged in affected nodes
    affected_ids = [n.node_id for n in response.affected_nodes]
    assert "fastapi" in affected_ids
    assert response.unverified_dependencies_invented is False
    assert "Temporal Graph RAG Investigation" in response.synthesis


def test_api_graph_traversal_and_paths_endpoints(client):
    """Test FastAPI GET /api/graph/traversal and /api/graph/paths."""
    # Traversal endpoint
    res_trav = client.get("/api/graph/traversal?root_id=fastapi&max_depth=2&max_nodes=10")
    assert res_trav.status_code == 200
    data_trav = res_trav.json()
    assert data_trav["root_entity"] == "fastapi"
    assert data_trav["total_nodes_visited"] >= 2
    assert len(data_trav["nodes"]) >= 2

    # Paths endpoint
    res_paths = client.get("/api/graph/paths?source=fastapi&target=pydantic&max_depth=2")
    assert res_paths.status_code == 200
    data_paths = res_paths.json()
    assert len(data_paths) >= 1
    assert data_paths[0]["source_id"] == "fastapi"
    assert data_paths[0]["target_id"] == "pydantic"


def test_api_temporal_graph_rag_investigate_endpoint(client):
    """Test FastAPI POST /api/graph/temporal-rag/investigate."""
    payload = {
        "query": "How does Pydantic affect FastAPI and SQLModel?",
        "root_entity": "pydantic",
        "max_depth": 3,
        "max_nodes": 20,
        "top_k_evidence": 3,
        "active_only": True,
        "rerank": True,
    }
    res = client.post("/api/graph/temporal-rag/investigate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "pydantic" in data["anchored_entities"]
    assert "synthesis" in data
    assert data["unverified_dependencies_invented"] is False
    assert len(data["affected_nodes"]) >= 1
