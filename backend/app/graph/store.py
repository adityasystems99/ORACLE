"""Persistent Temporal Knowledge Graph Store built on NetworkX."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import networkx as nx
from .blast_radius import BlastRadiusEngine
from ..config import get_settings
from ..schemas.graph import (
    BlastRadiusReport,
    EdgeType,
    GraphSnapshot,
    NodeType,
    TemporalGraphEdge,
    TemporalGraphNode,
)

logger = logging.getLogger(__name__)


SEED_NODES: List[TemporalGraphNode] = [
    TemporalGraphNode(id="python", name="Python", node_type=NodeType.TECHNOLOGY, ecosystem="python", latest_version="3.12"),
    TemporalGraphNode(id="fastapi", name="FastAPI", node_type=NodeType.PACKAGE, ecosystem="python", latest_version="0.111.0"),
    TemporalGraphNode(id="pydantic", name="Pydantic", node_type=NodeType.PACKAGE, ecosystem="python", latest_version="2.7.0"),
    TemporalGraphNode(id="pydantic-core", name="Pydantic Core", node_type=NodeType.PACKAGE, ecosystem="python", latest_version="2.18.0"),
    TemporalGraphNode(id="starlette", name="Starlette", node_type=NodeType.PACKAGE, ecosystem="python", latest_version="0.37.0"),
    TemporalGraphNode(id="uvicorn", name="Uvicorn", node_type=NodeType.PACKAGE, ecosystem="python", latest_version="0.30.0"),
    TemporalGraphNode(id="sqlalchemy", name="SQLAlchemy", node_type=NodeType.PACKAGE, ecosystem="python", latest_version="2.0.30"),
    TemporalGraphNode(id="sqlmodel", name="SQLModel", node_type=NodeType.PACKAGE, ecosystem="python", latest_version="0.0.19"),
    TemporalGraphNode(id="httpx", name="HTTPX", node_type=NodeType.PACKAGE, ecosystem="python", latest_version="0.27.0"),
    
    TemporalGraphNode(id="nodejs", name="Node.js", node_type=NodeType.TECHNOLOGY, ecosystem="node", latest_version="20.14.0"),
    TemporalGraphNode(id="react", name="React", node_type=NodeType.PACKAGE, ecosystem="node", latest_version="18.3.1"),
    TemporalGraphNode(id="vite", name="Vite", node_type=NodeType.PACKAGE, ecosystem="node", latest_version="5.3.0"),
    TemporalGraphNode(id="nextjs", name="Next.js", node_type=NodeType.PACKAGE, ecosystem="node", latest_version="14.2.0"),
    TemporalGraphNode(id="axios", name="Axios", node_type=NodeType.PACKAGE, ecosystem="node", latest_version="1.7.2"),
    TemporalGraphNode(id="tailwindcss", name="Tailwind CSS", node_type=NodeType.PACKAGE, ecosystem="node", latest_version="3.4.4"),

    TemporalGraphNode(id="cloudflare", name="Cloudflare", node_type=NodeType.SERVICE, ecosystem="cloud"),
    TemporalGraphNode(id="aws", name="Amazon Web Services", node_type=NodeType.SERVICE, ecosystem="cloud"),
    TemporalGraphNode(id="postgresql", name="PostgreSQL", node_type=NodeType.TECHNOLOGY, ecosystem="database", latest_version="16.3"),
    TemporalGraphNode(id="docker", name="Docker", node_type=NodeType.TECHNOLOGY, ecosystem="infrastructure"),
]

SEED_EDGES: List[TemporalGraphEdge] = [
    # FastAPI depends on Pydantic and Starlette
    TemporalGraphEdge(source="fastapi", target="pydantic", edge_type=EdgeType.DEPENDS_ON, version_constraint=">=1.7.4"),
    TemporalGraphEdge(source="fastapi", target="starlette", edge_type=EdgeType.DEPENDS_ON, version_constraint=">=0.37.0"),
    TemporalGraphEdge(source="fastapi", target="python", edge_type=EdgeType.DEPENDS_ON, version_constraint=">=3.8"),
    
    # Pydantic depends on pydantic-core and Python
    TemporalGraphEdge(source="pydantic", target="pydantic-core", edge_type=EdgeType.DEPENDS_ON, version_constraint="==2.18.0"),
    TemporalGraphEdge(source="pydantic", target="python", edge_type=EdgeType.DEPENDS_ON, version_constraint=">=3.8"),
    
    # SQLModel depends on Pydantic and SQLAlchemy
    TemporalGraphEdge(source="sqlmodel", target="pydantic", edge_type=EdgeType.DEPENDS_ON, version_constraint=">=2.0"),
    TemporalGraphEdge(source="sqlmodel", target="sqlalchemy", edge_type=EdgeType.DEPENDS_ON, version_constraint=">=2.0"),

    # Uvicorn and Starlette depend on Python
    TemporalGraphEdge(source="uvicorn", target="python", edge_type=EdgeType.DEPENDS_ON),
    TemporalGraphEdge(source="starlette", target="python", edge_type=EdgeType.DEPENDS_ON),
    TemporalGraphEdge(source="httpx", target="python", edge_type=EdgeType.DEPENDS_ON),

    # Web & Node dependencies
    TemporalGraphEdge(source="react", target="nodejs", edge_type=EdgeType.DEPENDS_ON),
    TemporalGraphEdge(source="vite", target="nodejs", edge_type=EdgeType.DEPENDS_ON),
    TemporalGraphEdge(source="nextjs", target="react", edge_type=EdgeType.DEPENDS_ON),
    TemporalGraphEdge(source="nextjs", target="nodejs", edge_type=EdgeType.DEPENDS_ON),
    TemporalGraphEdge(source="axios", target="nodejs", edge_type=EdgeType.DEPENDS_ON),
]


class KnowledgeGraphStore:
    """Manages the NetworkX temporal knowledge graph with disk backup and blast radius queries."""

    def __init__(self, persist_path: Optional[Path] = None):
        self.settings = get_settings()
        self.persist_path = persist_path or self.settings.GRAPH_PERSIST_PATH
        self.graph = nx.MultiDiGraph()
        self._load_or_initialize()
        self.blast_engine = BlastRadiusEngine(self.graph)

    def _load_or_initialize(self) -> None:
        """Load graph from JSON disk file or populate with seed entities."""
        if self.persist_path.exists():
            try:
                with open(self.persist_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for node_data in data.get("nodes", []):
                    self.add_node(TemporalGraphNode.model_validate(node_data), persist=False)
                for edge_data in data.get("edges", []):
                    self.add_edge(TemporalGraphEdge.model_validate(edge_data), persist=False)
                logger.info(f"Loaded graph from {self.persist_path}: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges.")
                return
            except Exception as e:
                logger.error(f"Error loading graph from {self.persist_path}: {e}")

        # Seed initial graph
        for node in SEED_NODES:
            self.add_node(node, persist=False)
        for edge in SEED_EDGES:
            self.add_edge(edge, persist=False)
        self.save_to_disk()
        logger.info(f"Initialized seed graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges.")

    def add_node(self, node: TemporalGraphNode, persist: bool = True) -> None:
        """Add or update an entity node in the graph."""
        node_dict = node.model_dump(mode="json")
        self.graph.add_node(node.id, **node_dict)
        if persist:
            self.save_to_disk()

    def add_edge(self, edge: TemporalGraphEdge, persist: bool = True) -> None:
        """Add a directional temporal relationship edge between two entities."""
        # Ensure nodes exist
        if edge.source not in self.graph:
            self.add_node(TemporalGraphNode(id=edge.source, name=edge.source.capitalize(), node_type=NodeType.PACKAGE), persist=False)
        if edge.target not in self.graph:
            self.add_node(TemporalGraphNode(id=edge.target, name=edge.target.capitalize(), node_type=NodeType.PACKAGE), persist=False)

        edge_dict = edge.model_dump(mode="json")
        self.graph.add_edge(edge.source, edge.target, key=edge.edge_type.value, **edge_dict)
        if persist:
            self.save_to_disk()

    def get_snapshot(self) -> GraphSnapshot:
        """Export full snapshot of the knowledge graph."""
        nodes: List[TemporalGraphNode] = []
        for _, data in self.graph.nodes(data=True):
            nodes.append(TemporalGraphNode.model_validate(data))

        edges: List[TemporalGraphEdge] = []
        for _, _, data in self.graph.edges(data=True):
            edges.append(TemporalGraphEdge.model_validate(data))

        return GraphSnapshot(
            nodes=nodes,
            edges=edges,
            node_count=len(nodes),
            edge_count=len(edges),
        )

    def calculate_blast_radius(self, root_entity_id: str, max_depth: int = 3, event_id: Optional[str] = None) -> BlastRadiusReport:
        """Compute impact blast radius for an entity."""
        return self.blast_engine.calculate_blast_radius(root_entity_id, max_depth=max_depth, event_id=event_id)

    def save_to_disk(self) -> None:
        """Serialize current graph state to JSON file."""
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot = self.get_snapshot()
        with open(self.persist_path, "w", encoding="utf-8") as f:
            json.dump(snapshot.model_dump(mode="json"), f, indent=2)
