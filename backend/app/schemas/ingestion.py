"""Pydantic schemas for data ingestion sources and raw signals."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, HttpUrl


class SourceType(str, Enum):
    """Categorization of external intelligence sources."""
    RSS = "rss"
    GITHUB_RELEASES = "github_releases"
    SECURITY_ADVISORY = "security_advisory"
    STATUS_PAGE = "status_page"
    CHANGELOG = "changelog"


class IngestionSource(BaseModel):
    """Configuration and state for an external intelligence source."""
    id: str = Field(..., description="Unique alphanumeric identifier for the source")
    name: str = Field(..., description="Human-readable title of the source feed")
    url: str = Field(..., description="Target HTTP(S) URL to monitor")
    source_type: SourceType = Field(..., description="Type of source connector")
    enabled: bool = Field(default=True, description="Whether this source is actively polled")
    ecosystem: str = Field(default="generic", description="Target ecosystem, e.g. python, node, cloud")
    refresh_interval_minutes: int = Field(default=30, ge=1, le=1440)
    last_synced_at: Optional[datetime] = None
    last_status: Optional[str] = "initialized"
    etag: Optional[str] = None
    last_modified: Optional[str] = None


class RawSignal(BaseModel):
    """Normalized raw signal captured from an external ingestion connector."""
    id: str = Field(..., description="Unique hash-based ID of the raw item")
    source_id: str = Field(..., description="ID of the originating IngestionSource")
    source_type: SourceType = Field(..., description="Type of source connector")
    title: str = Field(..., description="Title of the announcement, release, or advisory")
    url: str = Field(..., description="Canonical URL of the content")
    content: str = Field(..., description="Cleaned textual content or body")
    published_at: Optional[datetime] = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    content_hash: str = Field(..., description="SHA-256 fingerprint for idempotency and change detection")
    metadata: Dict[str, Any] = Field(default_factory=dict)
