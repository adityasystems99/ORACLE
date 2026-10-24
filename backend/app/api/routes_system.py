"""API routes for system health, configuration, and telemetry stats."""

from fastapi import APIRouter, Request
from ..config import get_settings
from ..schemas.event import IntelligenceEvent
from ..schemas.ingestion import RawSignal
from ..schemas.report import ImpactReport

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get("/health")
def get_system_health(request: Request):
    """Retrieve system diagnostics, counts, and active LLM provider."""
    settings = get_settings()
    disk_store = request.app.state.disk_store
    graph_store = request.app.state.graph_store
    llm_adapter = request.app.state.llm_adapter

    events_count = len(disk_store.load_all("events", IntelligenceEvent))
    signals_count = len(disk_store.load_all("raw_signals", RawSignal))
    reports_count = len(disk_store.load_all("reports", ImpactReport))
    sources = request.app.state.ingestion_engine.get_sources()
    scheduler = getattr(request.app.state, "scheduler_engine", None)
    scheduler_summary = scheduler.get_health().model_dump() if scheduler and hasattr(scheduler, "get_health") else {
        "is_running": False,
        "scheduler_type": "local_polling_monolith",
    }

    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "llm_provider": llm_adapter.provider_name,
        "llm_model": llm_adapter.model_name,
        "sources_count": len(sources),
        "signals_count": signals_count,
        "events_count": events_count,
        "reports_count": reports_count,
        "scheduler": scheduler_summary,
        "graph": {
            "nodes": graph_store.graph.number_of_nodes(),
            "edges": graph_store.graph.number_of_edges(),
        },
    }
