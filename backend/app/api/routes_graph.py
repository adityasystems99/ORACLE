"""API routes for Knowledge Graph exploration and blast radius queries."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request
from ..schemas.graph import (
    BlastRadiusReport,
    GraphSnapshot,
    TemporalGraphEdge,
    TemporalGraphNode,
)

router = APIRouter(prefix="/api/graph", tags=["Knowledge Graph"])


@router.get("/snapshot", response_model=GraphSnapshot)
def get_graph_snapshot(request: Request):
    """Retrieve full temporal knowledge graph snapshot for rendering and visualization."""
    graph_store = request.app.state.graph_store
    return graph_store.get_snapshot()


@router.get("/blast-radius", response_model=BlastRadiusReport)
def get_blast_radius(
    request: Request,
    entity: str = Query(..., description="Root entity identifier (e.g. 'pydantic', 'fastapi')"),
    max_depth: int = Query(default=3, ge=1, le=6),
    event_id: Optional[str] = Query(default=None),
):
    """Calculate the dependency explosion / blast radius for a given technology."""
    graph_store = request.app.state.graph_store
    return graph_store.calculate_blast_radius(root_entity_id=entity, max_depth=max_depth, event_id=event_id)


@router.post("/nodes", response_model=TemporalGraphNode)
def add_graph_node(node: TemporalGraphNode, request: Request):
    """Add or update an entity node in the knowledge graph."""
    graph_store = request.app.state.graph_store
    graph_store.add_node(node)
    return node


@router.post("/edges", response_model=TemporalGraphEdge)
def add_graph_edge(edge: TemporalGraphEdge, request: Request):
    """Add a directional relationship edge in the knowledge graph."""
    graph_store = request.app.state.graph_store
    graph_store.add_edge(edge)
    return edge
