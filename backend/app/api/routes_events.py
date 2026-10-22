"""API routes for querying and inspecting intelligence events."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from ..schemas.event import ChangeCategory, IntelligenceEvent, SeverityLevel

router = APIRouter(prefix="/api/events", tags=["Events"])


@router.get("", response_model=List[IntelligenceEvent])
def list_events(
    request: Request,
    category: Optional[ChangeCategory] = None,
    severity: Optional[SeverityLevel] = None,
    technology: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    """List detected intelligence events with filtering and sorting."""
    disk_store = request.app.state.disk_store
    events: List[IntelligenceEvent] = disk_store.load_all("events", IntelligenceEvent)

    # Sort descending by timestamp
    events.sort(key=lambda x: x.timestamp, reverse=True)

    filtered = []
    for e in events:
        if category and e.category != category:
            continue
        if severity and e.severity != severity:
            continue
        if technology and technology.lower() not in e.primary_technology.lower():
            continue
        filtered.append(e)
        if len(filtered) >= limit:
            break

    return filtered


@router.get("/{event_id}", response_model=IntelligenceEvent)
def get_event(event_id: str, request: Request):
    """Retrieve details for a single intelligence event by ID."""
    disk_store = request.app.state.disk_store
    event = disk_store.get_by_id("events", event_id, IntelligenceEvent)
    if not event:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found.")
    return event
