"""Blast radius analysis and impact propagation through the knowledge graph."""

from collections import deque
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Set
import networkx as nx
from ..schemas.graph import BlastRadiusNode, BlastRadiusReport, EdgeType, NodeType

logger = logging.getLogger(__name__)


class BlastRadiusEngine:
    """Analyzes impact propagation across dependency and integration edges."""

    def __init__(self, graph: nx.MultiDiGraph):
        self.graph = graph

    def calculate_blast_radius(
        self,
        root_entity_id: str,
        max_depth: int = 3,
        event_id: Optional[str] = None,
        as_of: Optional[datetime] = None,
    ) -> BlastRadiusReport:
        """Traverse the knowledge graph to discover affected upstream and downstream entities."""
        root_key = root_entity_id.lower().strip()
        as_of_dt = as_of or datetime.now(timezone.utc)

        if root_key not in self.graph:
            logger.warning(f"Root entity '{root_key}' not found in knowledge graph.")
            return BlastRadiusReport(
                root_entity=root_key,
                event_id=event_id,
                max_traversal_depth=max_depth,
                total_nodes_scanned=0,
                direct_dependents_count=0,
                transitive_dependents_count=0,
                affected_nodes=[],
                analysis_timestamp=as_of_dt,
            )

        visited: Set[str] = {root_key}
        affected: List[BlastRadiusNode] = []
        # Queue item: (node_id, depth, path_of_edges)
        queue = deque([(root_key, 0, [])])
        direct_count = 0
        transitive_count = 0

        # Note: If A DEPENDS_ON B, edge is (A -> B).
        # When B changes, we traverse predecessors (in-edges) of B to find things that depend on B.
        while queue:
            current_id, depth, path = queue.popleft()

            if depth >= max_depth:
                continue

            # Check incoming edges: entities that depend on current_id
            for source_id, _, edge_data in self.graph.in_edges(current_id, data=True):
                # Verify temporal validity
                valid_from = edge_data.get("valid_from")
                valid_to = edge_data.get("valid_to")
                if isinstance(valid_from, str):
                    try:
                        valid_from = datetime.fromisoformat(valid_from)
                    except ValueError:
                        valid_from = None
                if isinstance(valid_to, str):
                    try:
                        valid_to = datetime.fromisoformat(valid_to)
                    except ValueError:
                        valid_to = None

                if valid_from and valid_from > as_of_dt:
                    continue
                if valid_to and valid_to <= as_of_dt:
                    continue

                edge_type = edge_data.get("edge_type", EdgeType.DEPENDS_ON.value)
                new_path = path + [f"{source_id} -[{edge_type}]-> {current_id}"]

                if source_id not in visited:
                    visited.add(source_id)
                    node_data = self.graph.nodes.get(source_id, {})
                    target_depth = depth + 1

                    if target_depth == 1:
                        direct_count += 1
                        likelihood = 0.90
                    elif target_depth == 2:
                        transitive_count += 1
                        likelihood = 0.70
                    else:
                        transitive_count += 1
                        likelihood = 0.45

                    reasons = [
                        f"Directly {edge_type} {current_id}" if target_depth == 1 else f"Transitively {edge_type} {current_id} (hop {target_depth})"
                    ]

                    node_type_val = node_data.get("node_type", NodeType.PACKAGE.value)
                    try:
                        node_type_enum = NodeType(node_type_val)
                    except ValueError:
                        node_type_enum = NodeType.PACKAGE

                    affected.append(
                        BlastRadiusNode(
                            node_id=source_id,
                            name=node_data.get("name", source_id.capitalize()),
                            node_type=node_type_enum,
                            ecosystem=node_data.get("ecosystem", "generic"),
                            depth=target_depth,
                            relationship_path=new_path,
                            impact_likelihood=likelihood,
                            vulnerability_reasons=reasons,
                        )
                    )
                    queue.append((source_id, target_depth, new_path))

        return BlastRadiusReport(
            root_entity=root_key,
            event_id=event_id,
            max_traversal_depth=max_depth,
            total_nodes_scanned=len(visited),
            direct_dependents_count=direct_count,
            transitive_dependents_count=transitive_count,
            affected_nodes=affected,
            analysis_timestamp=as_of_dt,
        )
