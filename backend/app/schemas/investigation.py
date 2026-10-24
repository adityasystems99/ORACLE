"""Pydantic schemas for ORACLE's Evidence-Grounded Impact Investigation Engine."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
from .event import SeverityLevel


class ImpactCategory(str, Enum):
    """Categorization of technological impact."""
    API_DEPRECATION = "api_deprecation"
    BREAKING_CHANGE = "breaking_change"
    SECURITY_VULNERABILITY = "security_vulnerability"
    DEPENDENCY_CONFLICT = "dependency_conflict"
    SERVICE_OUTAGE = "service_outage"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    SPECIFICATION_UPDATE = "specification_update"


class ImpactStatus(str, Enum):
    """Distinguishes empirical certainty from potential blast radius."""
    CONFIRMED = "confirmed"              # Proved via direct dependency manifest or authoritative announcement
    POTENTIAL = "potential"              # Exposed via dependency graph, but internal execution unverified
    SUPERSEDED = "superseded"            # Outdated claim superseded by newer release or patch
    UNVERIFIED = "unverified"            # Unknown connection requiring private repository verification


class FindingPriority(str, Enum):
    """Operational triage priority for engineering teams."""
    P0_CRITICAL = "P0_CRITICAL"          # Immediate action required (active exploit or imminent breaking sunset)
    P1_HIGH = "P1_HIGH"                  # Urgent action required in current sprint
    P2_MEDIUM = "P2_MEDIUM"              # Scheduled maintenance / standard upgrade
    P3_LOW = "P3_LOW"                    # Informational or low-risk exposure


class EvidenceItem(BaseModel):
    """A granular piece of verifiable evidence backing a finding."""
    evidence_id: str
    source_url: str
    publisher: str
    title: str
    snippet: str
    publication_timestamp: Optional[datetime] = None
    retrieval_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    document_version: int = 1
    is_superseded: bool = False
    content_hash: str


class InvestigationFinding(BaseModel):
    """Detailed evidence-backed finding for a single affected component or API."""
    id: str = Field(..., description="Unique finding ID")
    summary: str = Field(..., description="Clear, factual summary of the impact")
    affected_entity: str = Field(..., description="Canonical ID of the affected component")
    affected_entity_name: str
    affected_entity_type: str
    impact_category: ImpactCategory
    impact_status: ImpactStatus
    severity: SeverityLevel
    priority: FindingPriority
    severity_and_priority_explanation: str = Field(..., description="Transparent rationale explaining the severity and priority")
    evidence_and_sources: List[EvidenceItem] = Field(default_factory=list)
    supporting_graph_path: List[str] = Field(default_factory=list, description="Sequence of relationship edges linking source to target")
    graph_path_explanation: str = Field(..., description="Human-readable explanation of the relationship chain")
    known_facts: List[str] = Field(default_factory=list, description="Empirically verified facts directly grounded in evidence")
    inferences_and_assumptions: List[str] = Field(default_factory=list, description="Explicitly stated assumptions and graph inferences")
    confidence_limitations: List[str] = Field(default_factory=list, description="Identified unknowns and boundaries of current evidence")
    suggested_next_steps: List[str] = Field(default_factory=list, description="Actionable verification and remediation steps")
    last_verified_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    causation_disclaimer: str = Field(
        default="A graph connection indicates exposure/dependency, not proven causal impact or internal execution.",
        description="Reliability Rule: Graph connection alone does not prove causation.",
    )
    internal_verification_note: str = Field(
        ...,
        description="Explicit notice regarding private repository and internal AST availability",
    )
    score: float = Field(default=0.0, ge=0.0, le=100.0, description="Deterministic ranking score")


class InvestigationReport(BaseModel):
    """Complete, evidence-grounded investigation report."""
    id: str = Field(..., description="Report identifier")
    query_or_event: str
    investigation_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    target_technology: Optional[str] = None
    executive_summary: str
    total_findings: int
    confirmed_impacts_count: int
    potential_impacts_count: int
    findings: List[InvestigationFinding] = Field(default_factory=list)
    superseded_claims: List[str] = Field(default_factory=list, description="Outdated claims detected from historical versions")
    conflicts_and_contradictions: List[str] = Field(default_factory=list, description="Conflicting evidence across sources")
    unknowns_and_open_questions: List[str] = Field(default_factory=list, description="Explicit open questions that cannot be answered yet")
    evidence_citations: List[EvidenceItem] = Field(default_factory=list)
    internal_impact_verification_status: str = Field(
        default="Internal repository dependencies cannot be fully verified without private codebase AST / lockfile access."
    )
    ranking_rules_applied: List[str] = Field(default_factory=list)
    llm_assisted: bool = False
    llm_provenance: Optional[Dict[str, Any]] = None


class InvestigationRequest(BaseModel):
    """Request payload to trigger an evidence-grounded impact investigation."""
    query: str = Field(..., min_length=2, description="Question, breaking change description, or CVE identifier")
    event_id: Optional[str] = Field(default=None, description="Optional associated IntelligenceEvent ID")
    target_technology: Optional[str] = Field(default=None, description="Optional root technology or package key")
    as_of: Optional[datetime] = Field(default=None, description="Point in time for temporal filtering")
    max_graph_depth: int = Field(default=3, ge=1, le=6, description="Maximum graph hops to traverse")
    max_candidates: int = Field(default=10, ge=1, le=50, description="Maximum number of findings to return")
    include_historical: bool = Field(default=True, description="Whether to analyze superseded versions")
    min_severity: Optional[SeverityLevel] = Field(default=None, description="Optional filter by minimum severity")

    @model_validator(mode="before")
    @classmethod
    def sanitize_inputs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Gracefully clamp max_graph_depth if out of bounds
            if "max_graph_depth" in data and isinstance(data["max_graph_depth"], int):
                data["max_graph_depth"] = min(max(1, data["max_graph_depth"]), 6)
            # Gracefully clamp max_candidates if out of bounds
            if "max_candidates" in data and isinstance(data["max_candidates"], int):
                data["max_candidates"] = min(max(1, data["max_candidates"]), 50)
            # Safely parse as_of string if provided
            if "as_of" in data and isinstance(data["as_of"], str):
                try:
                    data["as_of"] = datetime.fromisoformat(data["as_of"].replace("Z", "+00:00"))
                except Exception:
                    data["as_of"] = None
        return data
