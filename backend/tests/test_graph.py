"""Unit tests for temporal knowledge graph and blast radius calculation."""

from datetime import datetime, timezone
from app.graph.store import KnowledgeGraphStore
from app.schemas.graph import EdgeType, NodeType, TemporalGraphEdge, TemporalGraphNode


def test_seed_graph_initialization(test_graph_store: KnowledgeGraphStore):
    snapshot = test_graph_store.get_snapshot()
    assert snapshot.node_count >= 10
    assert snapshot.edge_count >= 5
    assert "fastapi" in test_graph_store.graph
    assert "pydantic" in test_graph_store.graph


def test_blast_radius_pydantic_change(test_graph_store: KnowledgeGraphStore):
    # FastAPI depends on Pydantic, SQLModel depends on Pydantic.
    # Therefore, when Pydantic has an issue, FastAPI and SQLModel should be in the blast radius.
    blast = test_graph_store.calculate_blast_radius("pydantic", max_depth=2)
    assert blast.root_entity == "pydantic"
    assert blast.direct_dependents_count >= 1

    affected_ids = [n.node_id for n in blast.affected_nodes]
    assert "fastapi" in affected_ids


def test_graph_persistence(temp_dir):
    graph_path = temp_dir / "persisted_graph.json"
    store1 = KnowledgeGraphStore(persist_path=graph_path)
    store1.add_node(
        TemporalGraphNode(id="custom_lib", name="CustomLib", node_type=NodeType.PACKAGE, ecosystem="python")
    )
    store1.add_edge(
        TemporalGraphEdge(source="custom_lib", target="fastapi", edge_type=EdgeType.DEPENDS_ON)
    )

    # Re-instantiate from same path
    store2 = KnowledgeGraphStore(persist_path=graph_path)
    assert "custom_lib" in store2.graph
    blast = store2.calculate_blast_radius("fastapi", max_depth=1)
    affected = [n.node_id for n in blast.affected_nodes]
    assert "custom_lib" in affected
