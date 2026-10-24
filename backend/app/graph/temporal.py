"""Temporal filtering, edge validity checks, and interval logic for knowledge graph."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from ..schemas.graph import TemporalGraphEdge


def parse_timestamp(val: Any) -> Optional[datetime]:
    """Safely parse datetime object or ISO string to UTC datetime."""
    if val is None:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)
    if isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None
    return None


def is_edge_active_at(edge: Union[TemporalGraphEdge, Dict[str, Any]], as_of: Optional[datetime] = None) -> bool:
    """Check if an edge was active at a given point in time.

    Reliability Rule: An edge is active at `as_of` iff:
    `valid_from <= as_of and (valid_until is None or valid_until > as_of)`.
    Outdated or superseded edges are not mistaken for current truth.
    """
    target_time = parse_timestamp(as_of) or datetime.now(timezone.utc)

    if isinstance(edge, dict):
        raw_from = edge.get("valid_from")
        raw_until = edge.get("valid_until") if edge.get("valid_until") is not None else edge.get("valid_to")
    else:
        raw_from = edge.valid_from
        raw_until = edge.valid_until if edge.valid_until is not None else edge.valid_to

    v_from = parse_timestamp(raw_from)
    v_until = parse_timestamp(raw_until)

    if v_from and v_from > target_time:
        return False
    if v_until and v_until <= target_time:
        return False
    return True


def is_edge_historical(edge: Union[TemporalGraphEdge, Dict[str, Any]], as_of: Optional[datetime] = None) -> bool:
    """Check if an edge has been superseded or expired prior to `as_of`."""
    return not is_edge_active_at(edge, as_of)


def filter_active_edges(edges: List[TemporalGraphEdge], as_of: Optional[datetime] = None) -> List[TemporalGraphEdge]:
    """Filter a list of edges returning only those active at `as_of`."""
    return [e for e in edges if is_edge_active_at(e, as_of)]
