"""Pydantic schemas for ORACLE's Conversational Investigation Copilot."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GroundingStatus(str, Enum):
    """Integrity and grounding verification status of copilot output."""
    FULLY_GROUNDED = "fully_grounded"
    PARTIALLY_GROUNDED = "partially_grounded"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class EvidenceCitation(BaseModel):
    """Ground-truth citation linked to a physical source document."""
    chunk_id: str = Field(..., description="Unique chunk or passage ID")
    source_url: str = Field(..., description="Canonical source URL")
    publisher: str = Field(..., description="Source publisher or organization")
    title: str = Field(..., description="Title of the source document")
    snippet: str = Field(..., description="Exact textual excerpt from the document")
    publication_timestamp: Optional[datetime] = Field(default=None, description="When the document was published")
    retrieval_timestamp: Optional[datetime] = Field(default=None, description="When the document was ingested")
    document_version: int = Field(default=1, description="Version of the ingested document")
    content_hash: str = Field(..., description="Cryptographic SHA256 fingerprint")
    is_superseded: bool = Field(default=False, description="Whether this version was superseded by a newer version")


class CopilotCodeSnippet(BaseModel):
    """Code or configuration snippet for mitigation or verification."""
    language: str = "bash"
    code: str
    filename: Optional[str] = None


class CopilotMessage(BaseModel):
    """A single turn in an investigation conversation."""
    id: str = Field(..., description="Unique message ID")
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text in Markdown")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    citations: List[EvidenceCitation] = Field(default_factory=list, description="Ground-truth citations")
    graph_paths: List[str] = Field(default_factory=list, description="Supporting paths from knowledge graph")
    suggested_follow_ups: List[str] = Field(default_factory=list, description="Context-preserving suggested follow-ups")
    code_snippets: Optional[List[CopilotCodeSnippet]] = Field(default=None, description="Code or command snippets")
    uncertainty_notes: List[str] = Field(default_factory=list, description="Explicit uncertainty and evidence limits")
    grounding_status: GroundingStatus = Field(default=GroundingStatus.FULLY_GROUNDED)


class CopilotSession(BaseModel):
    """Persistent investigation session containing multi-turn conversation state."""
    id: str = Field(..., description="Unique session ID")
    title: str = Field(..., description="Investigation title")
    primary_technology: str = Field(..., description="Primary package or technology under investigation")
    severity: str = Field(default="high", description="Severity classification")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = Field(default="active", description="'active', 'resolved', or 'archived'")
    messages: List[CopilotMessage] = Field(default_factory=list)


class CopilotChatRequest(BaseModel):
    """User message payload for copilot chat."""
    message: str = Field(..., min_length=1, description="User question or follow-up")
    as_of: Optional[datetime] = Field(default=None, description="Temporal point in time for graph evaluation")
    target_technology: Optional[str] = Field(default=None, description="Override target technology")


class CopilotCreateSessionRequest(BaseModel):
    """Payload to create a new investigation session."""
    title: Optional[str] = Field(default="Live Investigation", description="Investigation title")
    primary_technology: Optional[str] = Field(default="general", description="Primary technology")
    severity: Optional[str] = Field(default="high", description="Initial severity")
