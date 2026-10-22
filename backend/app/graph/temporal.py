"""Temporal filtering and edge validity checks for knowledge graph."""

from datetime import datetime, timezone
from typing import Optional
from ..schemas.graph import TemporalGraphEdge


def is_edge_active_at(edge: TemporalGraphEdge, as_of: Optional[datetime] = None) -> bool:
    """Check if an edge was active at a given timestamp."""
    target_time = as_of or datetime.now(timezone.utc)
    v_from = datetime.fromisoformat(edge.valid_from) if isinstance(edge.valid_from, str) else edge.valid_from
    v_to = datetime.fromisoformat(edge.valid_to) if isinstance(edge.valid_to, str) else edge.valid_to

    if v_from > target_time:
        return False
    if v_to and v_to <= target_time:
        return False
    return True
