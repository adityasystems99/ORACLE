"""Persistent Temporal Knowledge Graph Store built on NetworkX with bounded traversal,
historical relationship preservation, and explainable provenance paths.
"""

from collections import deque
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx

from .blast_radius import BlastRadiusEngine
from .temporal import is_edge_active_at, parse_timestamp
from ..config import get_settings
from ..schemas.graph import (
    BlastRadiusReport,
    EdgeType,
    ExplainablePath,
    GraphSnapshot,
    NodeType,
    PathStep,
    RelationshipModality,
    TemporalGraphEdge,
    TemporalGraphNode,
    TraversalResult,
)

logger = logging.getLogger(__name__)


# Seed entities covering all required entity types
SEED_NODES: List[TemporalGraphNode] = [
    # Companies / Organizations
    TemporalGraphNode(id="tiangolo", name="Sebastián Ramírez", node_type=NodeType.COMPANY, ecosystem="python", description="Creator and maintainer of FastAPI and SQLModel"),
    TemporalGraphNode(id="pydantic-team", name="Pydantic Inc.", node_type=NodeType.COMPANY, ecosystem="python", description="Maintainers of Pydantic validation library"),
    TemporalGraphNode(id="python-software-foundation", name="Python Software Foundation", node_type=NodeType.COMPANY, ecosystem="python"),
    TemporalGraphNode(id="meta", name="Meta", node_type=NodeType.COMPANY, ecosystem="node"),
    TemporalGraphNode(id="cloudflare-corp", name="Cloudflare Inc.", node_type=NodeType.COMPANY, ecosystem="cloud"),

    # Products & Technologies
    TemporalGraphNode(id="python", name="Python", node_type=NodeType.TECHNOLOGY, ecosystem="python", latest_version="3.12"),
    TemporalGraphNode(id="nodejs", name="Node.js", node_type=NodeType.TECHNOLOGY, ecosystem="node", latest_version="20.14.0"),
    TemporalGraphNode(id="fastapi", name="FastAPI", node_type=NodeType.PRODUCT, ecosystem="python", latest_version="0.111.0", repository="https://github.com/fastapi/fastapi"),
    TemporalGraphNode(id="pydantic", name="Pydantic", node_type=NodeType.PRODUCT, ecosystem="python", latest_version="2.7.0", repository="https://github.com/pydantic/pydantic"),
    TemporalGraphNode(id="sqlmodel", name="SQLModel", node_type=NodeType.PRODUCT, ecosystem="python", latest_version="0.0.19"),
    TemporalGraphNode(id="starlette", name="Starlette", node_type=NodeType.PRODUCT, ecosystem="python", latest_version="0.37.0"),
    TemporalGraphNode(id="uvicorn", name="Uvicorn", node_type=NodeType.PRODUCT, ecosystem="python", latest_version="0.30.0"),
    TemporalGraphNode(id="sqlalchemy", name="SQLAlchemy", node_type=NodeType.PRODUCT, ecosystem="python", latest_version="2.0.30"),
    TemporalGraphNode(id="react", name="React", node_type=NodeType.PRODUCT, ecosystem="node", latest_version="18.3.1"),
    TemporalGraphNode(id="nextjs", name="Next.js", node_type=NodeType.PRODUCT, ecosystem="node", latest_version="14.2.0"),
    TemporalGraphNode(id="docker", name="Docker", node_type=NodeType.PRODUCT, ecosystem="cloud", latest_version="26.1.0", repository="https://github.com/moby/moby"),

    # APIs & Specifications
    TemporalGraphNode(id="openapi-spec", name="OpenAPI Specification", node_type=NodeType.API, ecosystem="web", version="3.1.0"),
    TemporalGraphNode(id="pydantic-v2-core-api", name="Pydantic V2 Core API", node_type=NodeType.API, ecosystem="python", version="2.0"),

    # Dependencies
    TemporalGraphNode(id="pydantic-core", name="Pydantic Core Rust Extension", node_type=NodeType.DEPENDENCY, ecosystem="python", latest_version="2.18.0"),
    TemporalGraphNode(id="httpx", name="HTTPX", node_type=NodeType.DEPENDENCY, ecosystem="python", latest_version="0.27.0"),

    # SoftwareVersions
    TemporalGraphNode(id="fastapi-v0.111.0", name="FastAPI v0.111.0", node_type=NodeType.SOFTWARE_VERSION, ecosystem="python", version="0.111.0"),
    TemporalGraphNode(id="pydantic-v2.7.0", name="Pydantic v2.7.0", node_type=NodeType.SOFTWARE_VERSION, ecosystem="python", version="2.7.0"),
    TemporalGraphNode(id="pydantic-v1.10.0", name="Pydantic v1.10.0 (Legacy)", node_type=NodeType.SOFTWARE_VERSION, ecosystem="python", version="1.10.0"),

    # Releases & Events
    TemporalGraphNode(id="rel_fastapi_0111", name="FastAPI 0.111.0 Official Release", node_type=NodeType.RELEASE, ecosystem="python"),
    TemporalGraphNode(id="rel_pydantic_270", name="Pydantic 2.7.0 Official Release", node_type=NodeType.RELEASE, ecosystem="python"),
    TemporalGraphNode(id="evt_pydantic_v2_migration", name="Pydantic V2 Architecture Migration", node_type=NodeType.EVENT, ecosystem="python"),

    # Projects
    TemporalGraphNode(id="project_oracle_copilot", name="ORACLE Copilot Core Services", node_type=NodeType.PROJECT, ecosystem="python", description="Internal production services consuming FastAPI"),

    # Security Advisories
    TemporalGraphNode(id="cve-2024-fastapi-security-advisory", name="FastAPI Security Bulletin 2024", node_type=NodeType.SECURITY_ADVISORY, ecosystem="security"),

    # Evidence Documents
    TemporalGraphNode(id="doc_fastapi_rel_0111", name="FastAPI 0.111.0 Release Changelog", node_type=NodeType.EVIDENCE_DOCUMENT, ecosystem="python", homepage="https://github.com/fastapi/fastapi/releases/tag/0.111.0"),
]

# Seed relationships demonstrating PRODUCES, USES, DEPENDS_ON, AFFECTS, SUPERSEDES, ANNOUNCES, DOCUMENTED_BY, VERSION_OF
SEED_EDGES: List[TemporalGraphEdge] = [
    # Companies PRODUCE Products
    TemporalGraphEdge(source="tiangolo", target="fastapi", edge_type=EdgeType.PRODUCES, modality=RelationshipModality.OBSERVED, evidence_ids=["doc_fastapi_manifest"], source_url="https://github.com/tiangolo/fastapi"),
    TemporalGraphEdge(source="tiangolo", target="sqlmodel", edge_type=EdgeType.PRODUCES, modality=RelationshipModality.OBSERVED, evidence_ids=["doc_sqlmodel_manifest"], source_url="https://github.com/tiangolo/sqlmodel"),
    TemporalGraphEdge(source="pydantic-team", target="pydantic", edge_type=EdgeType.PRODUCES, modality=RelationshipModality.OBSERVED, evidence_ids=["doc_pydantic_manifest"], source_url="https://github.com/pydantic/pydantic"),
    TemporalGraphEdge(source="python-software-foundation", target="python", edge_type=EdgeType.PRODUCES, modality=RelationshipModality.OBSERVED, evidence_ids=["doc_python_org"], source_url="https://www.python.org"),

    # Products DEPEND_ON dependencies
    TemporalGraphEdge(source="fastapi", target="pydantic", edge_type=EdgeType.DEPENDS_ON, version_constraint=">=1.7.4", modality=RelationshipModality.OBSERVED, evidence_ids=["doc_fastapi_pyproject"], source_url="https://github.com/tiangolo/fastapi/blob/master/pyproject.toml"),
    TemporalGraphEdge(source="fastapi", target="starlette", edge_type=EdgeType.DEPENDS_ON, version_constraint=">=0.37.0", modality=RelationshipModality.OBSERVED, evidence_ids=["doc_fastapi_pyproject"], source_url="https://github.com/tiangolo/fastapi/blob/master/pyproject.toml"),
    TemporalGraphEdge(source="fastapi", target="python", edge_type=EdgeType.DEPENDS_ON, version_constraint=">=3.8", modality=RelationshipModality.OBSERVED, evidence_ids=["doc_fastapi_pyproject"], source_url="https://github.com/tiangolo/fastapi/blob/master/pyproject.toml"),
    TemporalGraphEdge(source="pydantic", target="pydantic-core", edge_type=EdgeType.DEPENDS_ON, version_constraint="==2.18.0", modality=RelationshipModality.OBSERVED, evidence_ids=["doc_pydantic_manifest"], source_url="https://github.com/pydantic/pydantic"),
    TemporalGraphEdge(source="sqlmodel", target="pydantic", edge_type=EdgeType.DEPENDS_ON, version_constraint=">=2.0", modality=RelationshipModality.OBSERVED, evidence_ids=["doc_sqlmodel_manifest"], source_url="https://github.com/tiangolo/sqlmodel"),
    TemporalGraphEdge(source="sqlmodel", target="sqlalchemy", edge_type=EdgeType.DEPENDS_ON, version_constraint=">=2.0", modality=RelationshipModality.OBSERVED, evidence_ids=["doc_sqlmodel_manifest"], source_url="https://github.com/tiangolo/sqlmodel"),
    TemporalGraphEdge(source="project_oracle_copilot", target="fastapi", edge_type=EdgeType.DEPENDS_ON, version_constraint=">=0.111.0", modality=RelationshipModality.OBSERVED, evidence_ids=["doc_oracle_pyproject"], source_url="https://github.com/oracle/copilot"),

    # Products USE APIs / Specifications
    TemporalGraphEdge(source="fastapi", target="openapi-spec", edge_type=EdgeType.USES, modality=RelationshipModality.OBSERVED, evidence_ids=["doc_fastapi_docs"], source_url="https://fastapi.tiangolo.com/features/"),
    TemporalGraphEdge(source="fastapi", target="pydantic-v2-core-api", edge_type=EdgeType.USES, modality=RelationshipModality.OBSERVED, evidence_ids=["doc_fastapi_docs"], source_url="https://fastapi.tiangolo.com"),

    # Versions VERSION_OF Product
    TemporalGraphEdge(source="fastapi-v0.111.0", target="fastapi", edge_type=EdgeType.VERSION_OF, modality=RelationshipModality.OBSERVED, evidence_ids=["doc_fastapi_rel_0111"], source_url="https://github.com/tiangolo/fastapi/releases/tag/0.111.0"),
    TemporalGraphEdge(source="pydantic-v2.7.0", target="pydantic", edge_type=EdgeType.VERSION_OF, modality=RelationshipModality.OBSERVED, evidence_ids=["doc_pydantic_rel_270"], source_url="https://github.com/pydantic/pydantic/releases/tag/v2.7.0"),
    TemporalGraphEdge(source="pydantic-v1.10.0", target="pydantic", edge_type=EdgeType.VERSION_OF, modality=RelationshipModality.OBSERVED, evidence_ids=["doc_pydantic_rel_1100"], source_url="https://github.com/pydantic/pydantic/releases/tag/v1.10.0"),

    # SUPERSEDES: v2.7.0 supersedes legacy v1.10.0
    TemporalGraphEdge(source="pydantic-v2.7.0", target="pydantic-v1.10.0", edge_type=EdgeType.SUPERSEDES, modality=RelationshipModality.OBSERVED, evidence_ids=["doc_pydantic_migration"], source_url="https://docs.pydantic.dev/2.0/migration/"),

    # Events ANNOUNCE Releases
    TemporalGraphEdge(source="evt_pydantic_v2_migration", target="rel_pydantic_270", edge_type=EdgeType.ANNOUNCES, modality=RelationshipModality.OBSERVED, evidence_ids=["doc_pydantic_migration"], source_url="https://docs.pydantic.dev/2.0/migration/"),

    # Releases DOCUMENTED_BY EvidenceDocument
    TemporalGraphEdge(
        source="rel_fastapi_0111",
        target="doc_fastapi_rel_0111",
        edge_type=EdgeType.DOCUMENTED_BY,
        modality=RelationshipModality.OBSERVED,
        source_url="https://github.com/fastapi/fastapi/releases/tag/0.111.0",
        evidence_ids=["doc_fastapi_rel_0111"],
    ),

    # Security Advisories AFFECT Products
    TemporalGraphEdge(
        source="cve-2024-fastapi-security-advisory",
        target="fastapi",
        edge_type=EdgeType.AFFECTS,
        version_constraint="<0.110.0",
        modality=RelationshipModality.OBSERVED,
        source_url="https://nvd.nist.gov/vuln/detail/CVE-2024-24762",
        evidence_ids=["doc_cve_advisory_2024"],
    ),

    # Node.js ecosystem
    TemporalGraphEdge(source="react", target="nodejs", edge_type=EdgeType.DEPENDS_ON, modality=RelationshipModality.OBSERVED, evidence_ids=["doc_react_pkg"], source_url="https://www.npmjs.com/package/react"),
    TemporalGraphEdge(source="nextjs", target="react", edge_type=EdgeType.DEPENDS_ON, modality=RelationshipModality.OBSERVED, evidence_ids=["doc_nextjs_pkg"], source_url="https://www.npmjs.com/package/next"),
    TemporalGraphEdge(source="nextjs", target="nodejs", edge_type=EdgeType.DEPENDS_ON, modality=RelationshipModality.OBSERVED, evidence_ids=["doc_nextjs_pkg"], source_url="https://www.npmjs.com/package/next"),
]


class KnowledgeGraphStore:
    """NetworkX-based Temporal Knowledge Graph with safe persistence, historical relationship

    preservation, cycle detection, bounded traversal, and explainable path extraction.
    """

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
                    self.add_edge(TemporalGraphEdge.model_validate(edge_data), supersede_existing=False, persist=False)
                logger.info(f"Loaded graph from {self.persist_path}: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges.")
                return
            except Exception as e:
                logger.error(f"Error loading graph from {self.persist_path}: {e}. Initializing seed graph.")

        # Seed initial graph
        for node in SEED_NODES:
            self.add_node(node, persist=False)
        for edge in SEED_EDGES:
            self.add_edge(edge, supersede_existing=False, persist=False)
        self.save_to_disk()
        logger.info(f"Initialized seed graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges.")

    def add_node(self, node: TemporalGraphNode, persist: bool = True) -> None:
        """Add or update an entity node in the graph."""
        node_dict = node.model_dump(mode="json")
        self.graph.add_node(node.id, **node_dict)
        if persist:
            self.save_to_disk()

    def add_edge(self, edge: TemporalGraphEdge, supersede_existing: bool = True, persist: bool = True) -> TemporalGraphEdge:
        """Add a directional relationship edge between two entities.

        Reliability Rule: Preserve historical relationships instead of silently overwriting them.
        When supersede_existing is True, existing active edges with identical source, target, and
        edge_type have their validity window closed (valid_until = new_edge.valid_from).
        Both the historical and new edges are preserved in the MultiDiGraph.
        """
        # Ensure source and target nodes exist
        if edge.source not in self.graph:
            self.add_node(TemporalGraphNode(id=edge.source, name=edge.source.capitalize(), node_type=NodeType.DEPENDENCY), persist=False)
        if edge.target not in self.graph:
            self.add_node(TemporalGraphNode(id=edge.target, name=edge.target.capitalize(), node_type=NodeType.DEPENDENCY), persist=False)

        # Check existing active edges between source and target
        if supersede_existing and self.graph.has_edge(edge.source, edge.target):
            edge_dict_existing = self.graph.get_edge_data(edge.source, edge.target)
            for key, data in list(edge_dict_existing.items()):
                # If same relationship type and currently active
                if data.get("edge_type") == edge.edge_type.value:
                    valid_until = data.get("valid_until") or data.get("valid_to")
                    if valid_until is None:
                        # Close the historical interval
                        closure_time = edge.valid_from.isoformat()
                        data["valid_until"] = closure_time
                        data["valid_to"] = closure_time
                        logger.info(f"Preserved historical edge {key} ({edge.source} -> {edge.target}) superseded at {closure_time}")

        edge_dict = edge.model_dump(mode="json")
        edge_key = edge.id or f"{edge.source}_{edge.edge_type.value}_{edge.target}_{int(edge.valid_from.timestamp())}"
        self.graph.add_edge(edge.source, edge.target, key=edge_key, **edge_dict)

        if persist:
            self.save_to_disk()
        return edge

    def get_snapshot(self, as_of: Optional[datetime] = None, active_only: bool = False) -> GraphSnapshot:
        """Export snapshot of the knowledge graph, optionally filtered temporally."""
        nodes: List[TemporalGraphNode] = []
        for _, data in self.graph.nodes(data=True):
            nodes.append(TemporalGraphNode.model_validate(data))

        edges: List[TemporalGraphEdge] = []
        for _, _, data in self.graph.edges(data=True):
            edge_obj = TemporalGraphEdge.model_validate(data)
            if active_only and not is_edge_active_at(edge_obj, as_of):
                continue
            edges.append(edge_obj)

        return GraphSnapshot(
            nodes=nodes,
            edges=edges,
            node_count=len(nodes),
            edge_count=len(edges),
        )

    def traverse(
        self,
        root_id: str,
        max_depth: int = 3,
        max_nodes: int = 50,
        as_of: Optional[datetime] = None,
        direction: str = "both",  # "outgoing", "incoming", or "both"
        edge_types: Optional[List[EdgeType]] = None,
        active_only: bool = True,
    ) -> TraversalResult:
        """Bounded graph traversal respecting depth and node limits, temporal filters, and cycle prevention."""
        root_key = root_id.lower().strip()
        as_of_dt = parse_timestamp(as_of) or datetime.now(timezone.utc)

        if root_key not in self.graph:
            return TraversalResult(
                root_entity=root_key,
                as_of=as_of_dt,
                max_depth=max_depth,
                max_nodes=max_nodes,
                total_nodes_visited=0,
                total_edges_traversed=0,
                cycles_detected=0,
                nodes=[],
                edges=[],
                explainable_paths=[],
            )

        visited_nodes: Set[str] = {root_key}
        traversed_edges: Dict[str, TemporalGraphEdge] = {}
        cycles_count = 0

        # Queue items: (current_node_id, current_depth, path_tuples)
        queue = deque([(root_key, 0, [])])
        explainable_paths: List[ExplainablePath] = []

        allowed_edge_types = {et.value for et in edge_types} if edge_types else None

        while queue and len(visited_nodes) < max_nodes:
            curr_id, depth, path = queue.popleft()

            if depth >= max_depth:
                continue

            candidate_edges = []
            if direction in ("outgoing", "both"):
                for u, v, k, data in self.graph.out_edges(curr_id, keys=True, data=True):
                    candidate_edges.append((u, v, k, data, "out"))
            if direction in ("incoming", "both"):
                for u, v, k, data in self.graph.in_edges(curr_id, keys=True, data=True):
                    candidate_edges.append((u, v, k, data, "in"))

            for u, v, k, data, edge_dir in candidate_edges:
                edge_type_val = data.get("edge_type")
                if allowed_edge_types and edge_type_val not in allowed_edge_types:
                    continue

                if active_only and not is_edge_active_at(data, as_of=as_of_dt):
                    continue

                edge_obj = TemporalGraphEdge.model_validate(data)
                traversed_edges[edge_obj.id or f"{u}->{v}_{k}"] = edge_obj

                neighbor_id = v if edge_dir == "out" else u

                # Cycle detection
                if neighbor_id in [step[0] for step in path] or neighbor_id == curr_id:
                    cycles_count += 1
                    continue

                new_path = path + [(curr_id, neighbor_id, edge_obj)]

                if neighbor_id not in visited_nodes:
                    visited_nodes.add(neighbor_id)
                    queue.append((neighbor_id, depth + 1, new_path))

                    # Build explainable path for reached neighbor
                    explainable_paths.append(self._build_explainable_path(root_key, neighbor_id, new_path))

                    if len(visited_nodes) >= max_nodes:
                        break

        # Collect node objects for all visited nodes
        result_nodes: List[TemporalGraphNode] = []
        for nid in visited_nodes:
            if nid in self.graph:
                result_nodes.append(TemporalGraphNode.model_validate(self.graph.nodes[nid]))

        return TraversalResult(
            root_entity=root_key,
            as_of=as_of_dt,
            max_depth=max_depth,
            max_nodes=max_nodes,
            total_nodes_visited=len(visited_nodes),
            total_edges_traversed=len(traversed_edges),
            cycles_detected=cycles_count,
            nodes=result_nodes,
            edges=list(traversed_edges.values()),
            explainable_paths=explainable_paths,
        )

    def find_explainable_paths(
        self,
        source_id: str,
        target_id: Optional[str] = None,
        max_depth: int = 4,
        max_paths: int = 10,
        as_of: Optional[datetime] = None,
        active_only: bool = True,
    ) -> List[ExplainablePath]:
        """Find verifiable explainable paths from source_id to target_id (or all reachable entities)

        tracing step-by-step provenance and evidence citations.
        """
        src = source_id.lower().strip()
        tgt = target_id.lower().strip() if target_id else None
        as_of_dt = parse_timestamp(as_of) or datetime.now(timezone.utc)

        if src not in self.graph:
            return []

        paths_found: List[ExplainablePath] = []
        # Queue item: (current_node, current_path_steps, visited_in_path)
        queue = deque([(src, [], {src})])

        while queue and len(paths_found) < max_paths:
            curr, steps, visited_in_path = queue.popleft()

            if tgt and curr == tgt and steps:
                paths_found.append(self._build_explainable_path(src, tgt, steps))
                continue

            if len(steps) >= max_depth:
                continue

            # Traverse outgoing and incoming edges for comprehensive dependency reasoning
            candidates = []
            for u, v, k, data in self.graph.out_edges(curr, keys=True, data=True):
                candidates.append((v, data))
            for u, v, k, data in self.graph.in_edges(curr, keys=True, data=True):
                candidates.append((u, data))

            for nxt, data in candidates:
                if nxt in visited_in_path:
                    continue  # prevent cycles

                if active_only and not is_edge_active_at(data, as_of=as_of_dt):
                    continue

                edge_obj = TemporalGraphEdge.model_validate(data)
                new_steps = steps + [(curr, nxt, edge_obj)]
                new_visited = visited_in_path | {nxt}

                if tgt is None and len(new_steps) > 0:
                    paths_found.append(self._build_explainable_path(src, nxt, new_steps))

                queue.append((nxt, new_steps, new_visited))

        return paths_found

    def _build_explainable_path(
        self,
        source_id: str,
        target_id: str,
        path_tuples: List[Tuple[str, str, TemporalGraphEdge]],
    ) -> ExplainablePath:
        """Construct structured ExplainablePath with step-by-step reasoning and evidence citations."""
        steps: List[PathStep] = []
        evidence_citations: List[str] = []
        step_narratives: List[str] = []
        all_temporally_valid = True
        overall_modality = RelationshipModality.OBSERVED

        for from_id, to_id, edge in path_tuples:
            from_data = self.graph.nodes.get(from_id, {})
            to_data = self.graph.nodes.get(to_id, {})

            from_name = from_data.get("name", from_id.capitalize())
            to_name = to_data.get("name", to_id.capitalize())
            from_type = NodeType(from_data.get("node_type", NodeType.DEPENDENCY.value))
            to_type = NodeType(to_data.get("node_type", NodeType.DEPENDENCY.value))

            if edge.modality == RelationshipModality.HYPOTHETICAL:
                overall_modality = RelationshipModality.HYPOTHETICAL
            elif edge.modality == RelationshipModality.INFERRED and overall_modality != RelationshipModality.HYPOTHETICAL:
                overall_modality = RelationshipModality.INFERRED

            # Gather evidence references
            for ev in edge.evidence_ids:
                if ev not in evidence_citations:
                    evidence_citations.append(ev)
            if edge.source_url and edge.source_url not in evidence_citations:
                evidence_citations.append(edge.source_url)

            narrative = (
                f"{from_name} ({from_type.value}) {edge.edge_type.value} {to_name} ({to_type.value})"
                + (f" [constraint: {edge.version_constraint}]" if edge.version_constraint else "")
                + (f" [modality: {edge.modality.value}]" if edge.modality != RelationshipModality.OBSERVED else "")
            )
            step_narratives.append(narrative)

            steps.append(
                PathStep(
                    from_node=from_id,
                    from_name=from_name,
                    from_type=from_type,
                    to_node=to_id,
                    to_name=to_name,
                    to_type=to_type,
                    edge_id=edge.id,
                    relationship=edge.edge_type,
                    modality=edge.modality,
                    valid_from=edge.valid_from,
                    valid_until=edge.valid_until,
                    version_constraint=edge.version_constraint,
                    confidence=edge.confidence,
                    evidence_ids=edge.evidence_ids,
                    source_url=edge.source_url,
                    step_explanation=narrative,
                )
            )

        # Multi-hop paths represent inferred propagation if > 1 hop
        if len(steps) > 1 and overall_modality == RelationshipModality.OBSERVED:
            overall_modality = RelationshipModality.INFERRED

        path_id = f"path_{source_id}_to_{target_id}_{len(steps)}hops"
        overall_explanation = " -> ".join(step_narratives)

        return ExplainablePath(
            path_id=path_id,
            source_id=source_id,
            target_id=target_id,
            steps=steps,
            overall_explanation=overall_explanation,
            evidence_citations=evidence_citations,
            total_hops=len(steps),
            is_temporally_valid=all_temporally_valid,
            path_modality=overall_modality,
        )

    def calculate_blast_radius(
        self,
        root_entity_id: str,
        max_depth: int = 3,
        event_id: Optional[str] = None,
        as_of: Optional[datetime] = None,
    ) -> BlastRadiusReport:
        """Compute impact blast radius for an entity."""
        return self.blast_engine.calculate_blast_radius(
            root_entity_id, max_depth=max_depth, event_id=event_id, as_of=as_of
        )

    def save_to_disk(self) -> None:
        """Serialize current graph state safely to JSON file."""
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot = self.get_snapshot()
        with open(self.persist_path, "w", encoding="utf-8") as f:
            json.dump(snapshot.model_dump(mode="json"), f, indent=2)
