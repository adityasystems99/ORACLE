"""Pydantic schemas for evidence-backed impact reports and mitigation playbooks."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .event import EvidenceRef, SeverityLevel
from .graph import BlastRadiusNode


class MitigationAction(BaseModel):
    """Actionable mitigation step with priority and code/command example."""
    step_number: int
    title: str
    description: str
    priority: SeverityLevel
    action_type: str = Field(..., description="e.g. upgrade, config_change, code_refactor, workaround")
    code_or_command: Optional[str] = None
    verification_check: Optional[str] = None
    estimated_effort: str = Field(default="low", description="low | medium | high")


class ImpactReport(BaseModel):
    """Comprehensive, evidence-backed impact dossier for an intelligence event."""
    id: str = Field(..., description="Unique report identifier (e.g. rpt_xxxx)")
    event_id: str = Field(..., description="Originating IntelligenceEvent ID")
    event_title: str
    severity: SeverityLevel
    primary_technology: str
    ecosystem: str
    executive_summary: str = Field(..., description="High-level briefing for tech leads and stakeholders")
    technical_root_cause: str = Field(..., description="Detailed technical breakdown of the breaking change/flaw")
    breaking_changes: List[str] = Field(default_factory=list)
    impacted_components: List[BlastRadiusNode] = Field(default_factory=list)
    evidence_trail: List[EvidenceRef] = Field(default_factory=list, description="Verbatim citations with URLs")
    mitigation_playbook: List[MitigationAction] = Field(default_factory=list)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    llm_provenance: Dict[str, Any] = Field(default_factory=dict, description="Provider, model, prompt tokens, generation time")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_live_data: bool = Field(default=True)
