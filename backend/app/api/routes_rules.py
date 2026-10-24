"""FastAPI router for managing Autonomous Monitoring Rules and viewing alerts."""

import logging
from typing import List
from fastapi import APIRouter, HTTPException, Query, Request

from ..schemas.monitoring import (
    AlertRecord,
    MonitoringRule,
    MonitoringRuleCreate,
    MonitoringRuleUpdate,
)

logger = logging.getLogger("oracle.api.rules")
router = APIRouter(tags=["Monitoring Rules"])


def get_monitoring_engine(request: Request):
    """Retrieve ScheduledMonitoringEngine from app state."""
    engine = getattr(request.app.state, "scheduler_engine", None)
    if not engine:
        raise HTTPException(status_code=500, detail="MonitoringEngine is not initialized.")
    return engine


@router.get("/rules", response_model=List[MonitoringRule])
def list_rules(request: Request) -> List[MonitoringRule]:
    """List all autonomous monitoring rules."""
    engine = get_monitoring_engine(request)
    return engine.list_rules()


@router.post("/rules", response_model=MonitoringRule)
def create_rule(payload: MonitoringRuleCreate, request: Request) -> MonitoringRule:
    """Create a new autonomous monitoring rule."""
    engine = get_monitoring_engine(request)
    return engine.create_rule(payload)


@router.get("/rules/alerts", response_model=List[AlertRecord])
def list_alerts(request: Request, limit: int = Query(default=50, ge=1, le=200)) -> List[AlertRecord]:
    """Retrieve audit history of dispatched deduplicated alerts."""
    engine = get_monitoring_engine(request)
    return engine.list_alerts(limit=limit)


@router.get("/rules/{rule_id}", response_model=MonitoringRule)
def get_rule(rule_id: str, request: Request) -> MonitoringRule:
    """Fetch details of a single monitoring rule."""
    engine = get_monitoring_engine(request)
    rule = engine.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found.")
    return rule


@router.put("/rules/{rule_id}", response_model=MonitoringRule)
def update_rule(rule_id: str, payload: MonitoringRuleUpdate, request: Request) -> MonitoringRule:
    """Update criteria, alert channels, or notification preferences of a rule."""
    engine = get_monitoring_engine(request)
    rule = engine.update_rule(rule_id, payload)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found.")
    return rule


@router.post("/rules/{rule_id}/pause", response_model=MonitoringRule)
def pause_rule(rule_id: str, request: Request) -> MonitoringRule:
    """Pause execution of a monitoring rule."""
    engine = get_monitoring_engine(request)
    rule = engine.pause_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found.")
    return rule


@router.post("/rules/{rule_id}/resume", response_model=MonitoringRule)
def resume_rule(rule_id: str, request: Request) -> MonitoringRule:
    """Resume execution of a paused monitoring rule."""
    engine = get_monitoring_engine(request)
    rule = engine.resume_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found.")
    return rule


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: str, request: Request):
    """Delete a monitoring rule."""
    engine = get_monitoring_engine(request)
    deleted = engine.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found.")
    return {"status": "deleted", "rule_id": rule_id}
