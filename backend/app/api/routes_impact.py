"""API routes for triggering impact assessments and viewing evidence-backed reports."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from ..impact.report_generator import format_markdown_dossier
from ..schemas.event import IntelligenceEvent
from ..schemas.report import ImpactReport

router = APIRouter(prefix="/api/impact", tags=["Impact Analysis"])


class AnalyzeRequest(BaseModel):
    event_id: str = Field(..., description="ID of the event to analyze")
    max_depth: int = Field(default=3, ge=1, le=5)


@router.post("/analyze", response_model=ImpactReport)
async def analyze_event_impact(payload: AnalyzeRequest, request: Request):
    """Generate an evidence-backed impact report for a detected intelligence event."""
    disk_store = request.app.state.disk_store
    analyzer = request.app.state.impact_analyzer

    event = disk_store.get_by_id("events", payload.event_id, IntelligenceEvent)
    if not event:
        raise HTTPException(status_code=404, detail=f"Intelligence event '{payload.event_id}' not found.")

    report = await analyzer.generate_impact_report(event=event, max_graph_depth=payload.max_depth)
    return report


@router.get("/reports", response_model=List[ImpactReport])
def list_reports(
    request: Request,
    technology: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
):
    """List all generated impact dossiers."""
    disk_store = request.app.state.disk_store
    reports: List[ImpactReport] = disk_store.load_all("reports", ImpactReport)
    reports.sort(key=lambda x: x.generated_at, reverse=True)

    if technology:
        reports = [r for r in reports if technology.lower() in r.primary_technology.lower()]

    return reports[:limit]


@router.get("/reports/{report_id}", response_model=ImpactReport)
def get_report(report_id: str, request: Request):
    """Retrieve an impact dossier by ID."""
    disk_store = request.app.state.disk_store
    report = disk_store.get_by_id("reports", report_id, ImpactReport)
    if not report:
        raise HTTPException(status_code=404, detail=f"Impact report '{report_id}' not found.")
    return report


@router.get("/reports/{report_id}/markdown", response_class=PlainTextResponse)
def get_report_markdown(report_id: str, request: Request):
    """Export the impact report as a formatted Markdown briefing."""
    disk_store = request.app.state.disk_store
    report = disk_store.get_by_id("reports", report_id, ImpactReport)
    if not report:
        raise HTTPException(status_code=404, detail=f"Impact report '{report_id}' not found.")
    return format_markdown_dossier(report)
