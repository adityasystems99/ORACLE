"""Blast radius analysis and impact propagation through the temporal knowledge graph."""

from collections import deque
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Set
import networkx as nx
from .temporal import is_edge_active_at, parse_timestamp
from ..schemas.graph import (
    BlastRadiusNode,
    BlastRadiusReport,
    EdgeType,
    NodeType,
    RelationshipModality,
)

logger = logging.getLogger(__name__)


class BlastRadiusEngine:
    """Analyzes impact propagation across dependency, integration, and advisory edges."""

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
        as_of_dt = parse_timestamp(as_of) or datetime.now(timezone.utc)

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
        # Queue item: (node_id, depth, path_of_edges, accumulated_evidence)
        queue = deque([(root_key, 0, [], [])])
        direct_count = 0
        transitive_count = 0

        # Note: In standard dependency modeling, A DEPENDS_ON B is modeled as (A -> B).
        # When B changes, we traverse in-edges to find things that depend on B.
        # When an advisory AFFECTS B, edge is (Advisory -> B), so we traverse out-edges from advisory.
        while queue:
            current_id, depth, path, accumulated_ev = queue.popleft()

            if depth >= max_depth:
                continue

            # 1. Check in-edges (consumer dependencies of current_id, e.g. A DEPENDS_ON current_id, B USES current_id)
            for source_id, _, edge_data in self.graph.in_edges(current_id, data=True):
                if not is_edge_active_at(edge_data, as_of=as_of_dt):
                    continue

                edge_type = str(edge_data.get("edge_type", "")).upper()
                # Only consumer dependency edges propagate impact to callers
                if edge_type not in [EdgeType.DEPENDS_ON.value, EdgeType.USES.value, "DEPENDS_ON", "USES"]:
                    continue

                node_data = self.graph.nodes.get(source_id, {})
                node_type_val = str(node_data.get("node_type", "")).lower()
                # Exclude organizations, releases, and documents from affected software counts
                if any(ignored in node_type_val for ignored in ["company", "organization", "release", "evidence_document", "event", "security_advisory"]):
                    continue

                new_path = path + [f"{source_id} -[{edge_type}]-> {current_id}"]
                ev_ids = list(accumulated_ev) + list(edge_data.get("evidence_ids", []))
                if edge_data.get("source_evidence_id"):
                    ev_ids.append(edge_data["source_evidence_id"])
                ev_ids = list(dict.fromkeys(ev_ids))

                if source_id not in visited:
                    visited.add(source_id)
                    target_depth = depth + 1

                    if target_depth == 1:
                        direct_count += 1
                        likelihood = 0.90
                        modality = RelationshipModality.OBSERVED if ev_ids else RelationshipModality.INFERRED
                    elif target_depth == 2:
                        transitive_count += 1
                        likelihood = 0.70
                        modality = RelationshipModality.INFERRED
                    else:
                        transitive_count += 1
                        likelihood = 0.45
                        modality = RelationshipModality.INFERRED

                    reasons = [
                        f"Directly {edge_type} {current_id}"
                        if target_depth == 1
                        else f"Transitively {edge_type} {current_id} (hop {target_depth})"
                    ]

                    try:
                        node_type_enum = NodeType(node_data.get("node_type", NodeType.DEPENDENCY.value))
                    except ValueError:
                        node_type_enum = NodeType.DEPENDENCY

                    affected.append(
                        BlastRadiusNode(
                            node_id=source_id,
                            name=node_data.get("name", source_id.capitalize()),
                            node_type=node_type_enum,
                            ecosystem=node_data.get("ecosystem", "generic"),
                            depth=target_depth,
                            relationship_path=new_path,
                            impact_likelihood=likelihood,
                            modality=modality,
                            vulnerability_reasons=reasons,
                            evidence_ids=ev_ids,
                        )
                    )
                    queue.append((source_id, target_depth, new_path, ev_ids))

            # 2. Check out-edges for advisories and incidents (e.g. Advisory AFFECTS Product)
            for _, target_id, edge_data in self.graph.out_edges(current_id, data=True):
                if not is_edge_active_at(edge_data, as_of=as_of_dt):
                    continue

                edge_type = str(edge_data.get("edge_type", "")).upper()
                if edge_type not in [EdgeType.AFFECTS.value, "AFFECTS"]:
                    continue

                node_data = self.graph.nodes.get(target_id, {})
                node_type_val = str(node_data.get("node_type", "")).lower()
                if any(ignored in node_type_val for ignored in ["company", "organization", "release", "evidence_document", "event"]):
                    continue

                new_path = path + [f"{current_id} -[{edge_type}]-> {target_id}"]
                ev_ids = list(accumulated_ev) + list(edge_data.get("evidence_ids", []))
                if edge_data.get("source_evidence_id"):
                    ev_ids.append(edge_data["source_evidence_id"])
                ev_ids = list(dict.fromkeys(ev_ids))

                if target_id not in visited:
                    visited.add(target_id)
                    target_depth = depth + 1

                    if target_depth == 1:
                        direct_count += 1
                        likelihood = 0.95
                        modality = RelationshipModality.OBSERVED if ev_ids else RelationshipModality.INFERRED
                    else:
                        transitive_count += 1
                        likelihood = 0.75
                        modality = RelationshipModality.INFERRED

                    reasons = [f"Target of {edge_type} from {current_id}"]
                    try:
                        node_type_enum = NodeType(node_data.get("node_type", NodeType.PRODUCT.value))
                    except ValueError:
                        node_type_enum = NodeType.PRODUCT

                    affected.append(
                        BlastRadiusNode(
                            node_id=target_id,
                            name=node_data.get("name", target_id.capitalize()),
                            node_type=node_type_enum,
                            ecosystem=node_data.get("ecosystem", "generic"),
                            depth=target_depth,
                            relationship_path=new_path,
                            impact_likelihood=likelihood,
                            modality=modality,
                            vulnerability_reasons=reasons,
                            evidence_ids=ev_ids,
                        )
                    )
                    queue.append((target_id, target_depth, new_path, ev_ids))

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
