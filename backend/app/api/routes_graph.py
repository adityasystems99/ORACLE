"""API routes for Knowledge Graph exploration, bounded temporal traversal,
explainable path queries, and combined Temporal Graph RAG investigation.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Request

from ..schemas.graph import (
    BlastRadiusReport,
    ExplainablePath,
    GraphSnapshot,
    TemporalGraphEdge,
    TemporalGraphNode,
    TemporalGraphRAGQuery,
    TemporalGraphRAGResponse,
    TraversalResult,
)

router = APIRouter(prefix="/api/graph", tags=["Knowledge Graph"])


@router.get("/snapshot", response_model=GraphSnapshot)
def get_graph_snapshot(
    request: Request,
    active_only: bool = Query(default=False, description="Filter only active edges as of current timestamp"),
    as_of: Optional[datetime] = Query(default=None, description="Optional temporal snapshot timestamp"),
):
    """Retrieve temporal knowledge graph snapshot for rendering, analysis, and visualization."""
    graph_store = request.app.state.graph_store
    return graph_store.get_snapshot(as_of=as_of, active_only=active_only)


@router.get("/blast-radius", response_model=BlastRadiusReport)
def get_blast_radius(
    request: Request,
    entity: str = Query(..., description="Root entity identifier (e.g. 'pydantic', 'fastapi')"),
    max_depth: int = Query(default=3, ge=1, le=6),
    event_id: Optional[str] = Query(default=None),
    as_of: Optional[datetime] = Query(default=None, description="Temporal point in time for edge validity"),
):
    """Calculate the dependency explosion / blast radius for a given technology."""
    graph_store = request.app.state.graph_store
    return graph_store.calculate_blast_radius(
        root_entity_id=entity, max_depth=max_depth, event_id=event_id, as_of=as_of
    )


@router.get("/traversal", response_model=TraversalResult)
def get_graph_traversal(
    request: Request,
    root_id: str = Query(..., description="Starting entity ID (e.g. 'fastapi')"),
    max_depth: int = Query(default=3, ge=1, le=6, description="Maximum traversal hops"),
    max_nodes: int = Query(default=50, ge=1, le=200, description="Maximum node limit"),
    as_of: Optional[datetime] = Query(default=None, description="Temporal point in time"),
    direction: str = Query(default="both", pattern="^(outgoing|incoming|both)$"),
    active_only: bool = Query(default=True, description="When true, excludes superseded/historical edges"),
):
    """Execute bounded temporal graph traversal with configurable depth, node limits, and cycle prevention."""
    graph_store = request.app.state.graph_store
    return graph_store.traverse(
        root_id=root_id,
        max_depth=max_depth,
        max_nodes=max_nodes,
        as_of=as_of,
        direction=direction,
        active_only=active_only,
    )


@router.get("/paths", response_model=List[ExplainablePath])
def get_explainable_paths(
    request: Request,
    source: str = Query(..., description="Source entity ID"),
    target: Optional[str] = Query(default=None, description="Optional target entity ID. If omitted, returns paths to all reachable entities."),
    max_depth: int = Query(default=4, ge=1, le=6),
    max_paths: int = Query(default=10, ge=1, le=50),
    as_of: Optional[datetime] = Query(default=None),
    active_only: bool = Query(default=True),
):
    """Find explainable multi-hop paths between entities backed by evidence provenance."""
    graph_store = request.app.state.graph_store
    return graph_store.find_explainable_paths(
        source_id=source,
        target_id=target,
        max_depth=max_depth,
        max_paths=max_paths,
        as_of=as_of,
        active_only=active_only,
    )


@router.post("/nodes", response_model=TemporalGraphNode)
def add_graph_node(node: TemporalGraphNode, request: Request):
    """Add or update an entity node in the knowledge graph."""
    graph_store = request.app.state.graph_store
    graph_store.add_node(node)
    return node


@router.post("/edges", response_model=TemporalGraphEdge)
def add_graph_edge(
    edge: TemporalGraphEdge,
    request: Request,
    supersede_existing: bool = Query(default=True, description="Preserve historical edges by setting their valid_until"),
):
    """Add a directional relationship edge in the knowledge graph preserving historical relationships."""
    graph_store = request.app.state.graph_store
    return graph_store.add_edge(edge, supersede_existing=supersede_existing)


@router.post("/temporal-rag/investigate", response_model=TemporalGraphRAGResponse)
async def investigate_temporal_graph_rag(
    query: TemporalGraphRAGQuery,
    request: Request,
):
    """Combined Temporal Graph RAG: Semantic retrieval + Bounded temporal graph traversal + Explainable path synthesis."""
    temporal_engine = request.app.state.temporal_graph_rag
    return await temporal_engine.investigate(query)
