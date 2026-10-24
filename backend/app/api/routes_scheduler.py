"""FastAPI router for Ingestion Scheduler observability, health, and manual controls."""

import logging
from fastapi import APIRouter, HTTPException, Request
from ..schemas.monitoring import SchedulerHealth

logger = logging.getLogger("oracle.api.scheduler")
router = APIRouter(tags=["Scheduler"])


def get_monitoring_engine(request: Request):
    """Retrieve ScheduledMonitoringEngine from app state."""
    engine = getattr(request.app.state, "scheduler_engine", None)
    if not engine:
        raise HTTPException(status_code=500, detail="MonitoringEngine is not initialized.")
    return engine


@router.get("/scheduler/status", response_model=SchedulerHealth)
def get_scheduler_status(request: Request) -> SchedulerHealth:
    """Retrieve operational health, next scheduled runs, errors, and rates."""
    engine = get_monitoring_engine(request)
    return engine.get_health()


@router.post("/scheduler/run-now")
async def trigger_run_now(request: Request):
    """Trigger immediate polling of all due sources."""
    engine = get_monitoring_engine(request)
    return await engine.run_due_sources()


@router.post("/scheduler/pause")
def pause_scheduler(request: Request):
    """Pause background scheduled polling."""
    engine = get_monitoring_engine(request)
    engine.pause()
    return {"status": "paused", "is_paused": True}


@router.post("/scheduler/resume")
def resume_scheduler(request: Request):
    """Resume background scheduled polling."""
    engine = get_monitoring_engine(request)
    engine.resume()
    return {"status": "resumed", "is_paused": False}
