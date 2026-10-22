"""API routes for ingestion sources and synchronization."""

from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from ..schemas.event import IntelligenceEvent
from ..schemas.ingestion import IngestionSource, RawSignal

router = APIRouter(prefix="/api/ingest", tags=["Ingestion"])


@router.get("/sources", response_model=List[IngestionSource])
def get_sources(request: Request):
    """Retrieve all configured ingestion sources and their current health status."""
    engine = request.app.state.ingestion_engine
    return engine.get_sources()


@router.post("/sources", response_model=IngestionSource)
def add_source(source: IngestionSource, request: Request):
    """Register or update an ingestion source."""
    engine = request.app.state.ingestion_engine
    engine.add_source(source)
    return source


@router.post("/sync")
async def trigger_sync(request: Request, source_id: Optional[str] = None):
    """Trigger an on-demand live ingestion and change detection run."""
    engine = request.app.state.ingestion_engine
    detector = request.app.state.change_detector
    vector_store = request.app.state.vector_store

    new_signals: List[RawSignal] = await engine.run_sync(source_id=source_id)
    new_events: List[IntelligenceEvent] = detector.process_signals(new_signals)

    # Index new events in vector store
    if new_events:
        vector_store.upsert_documents(
            collection_name="events",
            ids=[e.id for e in new_events],
            documents=[f"{e.title}\n{e.summary}" for e in new_events],
            metadatas=[{
                "category": e.category.value,
                "severity": e.severity.value,
                "technology": e.primary_technology,
            } for e in new_events],
        )

    return {
        "status": "success",
        "signals_ingested": len(new_signals),
        "events_detected": len(new_events),
        "event_ids": [e.id for e in new_events],
    }
