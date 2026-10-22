"""Pydantic schemas for classified intelligence events and evidence provenance."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChangeCategory(str, Enum):
    """Semantic category of detected technological change."""
    BREAKING_CHANGE = "breaking_change"
    DEPRECATION = "deprecation"
    SECURITY_VULNERABILITY = "security_vulnerability"
    OUTAGE = "outage"
    PERFORMANCE_REGRESSION = "performance_regression"
    MAJOR_RELEASE = "major_release"
    PATCH = "patch"
    GENERAL_UPDATE = "general_update"


class SeverityLevel(str, Enum):
    """Impact severity rating."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class EvidenceRef(BaseModel):
    """Direct ground-truth citation backing an intelligence event or impact claim."""
    source_url: str = Field(..., description="Canonical URL where the fact was published")
    source_type: str = Field(..., description="Source type, e.g. github_release, cve, rss")
    title: str = Field(..., description="Title of the source document")
    snippet: str = Field(..., description="Verbatim text snippet proving the occurrence")
    published_at: Optional[datetime] = None
    content_hash: str = Field(..., description="SHA-256 hash of the verbatim content")


class IntelligenceEvent(BaseModel):
    """Validated technological intelligence event with full evidence provenance."""
    id: str = Field(..., description="Unique event identifier (e.g. evt_xxxx)")
    raw_signal_id: str = Field(..., description="Foreign key to the originating RawSignal")
    category: ChangeCategory = Field(..., description="Classified change category")
    severity: SeverityLevel = Field(..., description="Calculated severity level")
    title: str = Field(..., description="Concise, informative title of the intelligence event")
    summary: str = Field(..., description="Objective summary of the change and its context")
    primary_technology: str = Field(..., description="Core technology or library affected (e.g. fastapi, pydantic)")
    affected_entities: List[str] = Field(default_factory=list, description="List of related packages, libraries, or tools")
    version_affected: Optional[str] = None
    version_fixed: Optional[str] = None
    cve_id: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of classification")
    detection_rationale: str = Field(..., description="Why this item was flagged as a meaningful change")
    evidence: List[EvidenceRef] = Field(default_factory=list, description="Ground-truth citations backing this event")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_live_data: bool = Field(default=True, description="Strictly true for live ingested data; false if synthetic test fixture")
    metadata: Dict[str, Any] = Field(default_factory=dict)
