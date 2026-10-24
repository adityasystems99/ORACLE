"""API routes for triggering impact assessments, evidence-grounded investigations, and viewing reports."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from ..impact.report_generator import format_markdown_dossier
from ..schemas.event import IntelligenceEvent
from ..schemas.investigation import InvestigationReport, InvestigationRequest
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


@router.post("/investigate", response_model=InvestigationReport)
async def investigate_impact(payload: InvestigationRequest, request: Request):
    """Execute unified evidence-grounded impact investigation combining Live RAG and Temporal Graph RAG."""
    investigation_service = request.app.state.investigation_service
    report = await investigation_service.investigate(payload)

    # Persist report to disk store for inspection and audit trail
    disk_store = request.app.state.disk_store
    disk_store.upsert_item("investigation_reports", report)

    return report


@router.get("/investigations", response_model=List[InvestigationReport])
def list_investigations(
    request: Request,
    technology: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
):
    """List all generated unified impact investigation reports."""
    disk_store = request.app.state.disk_store
    reports: List[InvestigationReport] = disk_store.load_all("investigation_reports", InvestigationReport)
    reports.sort(key=lambda x: x.investigation_timestamp, reverse=True)

    if technology:
        reports = [
            r for r in reports
            if (r.target_technology and technology.lower() in r.target_technology.lower())
            or technology.lower() in r.query_or_event.lower()
        ]

    return reports[:limit]


@router.get("/investigations/{report_id}", response_model=InvestigationReport)
def get_investigation_report(report_id: str, request: Request):
    """Retrieve an investigation report by ID."""
    disk_store = request.app.state.disk_store
    report = disk_store.get_by_id("investigation_reports", report_id, InvestigationReport)
    if not report:
        raise HTTPException(status_code=404, detail=f"Investigation report '{report_id}' not found.")
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
