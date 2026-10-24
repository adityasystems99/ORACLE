"""Pydantic schemas for ORACLE Live RAG pipeline."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IngestionStatus(str, Enum):
    """Status outcomes for document ingestion."""
    SUCCESS = "success"
    UNCHANGED = "unchanged"
    UPDATED = "updated"
    FAILED = "failed"


class DocumentVersionRecord(BaseModel):
    """Archived historical version of an ingested document."""
    version: int = Field(..., description="1-based document version number")
    content_hash: str = Field(..., description="SHA-256 fingerprint of the historical content")
    archived_at: datetime = Field(..., description="Timestamp when this version was superseded")
    content_preview: str = Field(..., description="Preview snippet of the historical content")
    publication_timestamp: Optional[datetime] = Field(
        default=None,
        description="Original upstream publication date of this version if known",
    )


class IngestedDocument(BaseModel):
    """Canonical document ingested from an external technology source."""
    id: str = Field(..., description="Deterministic unique identifier based on canonical URL")
    source_id: str = Field(..., description="Originating IngestionSource ID")
    source_url: str = Field(..., description="Canonical URL of the document")
    publisher: str = Field(..., description="Publisher or maintainer organization (e.g. FastAPI / Tiangolo, PSF)")
    title: str = Field(..., description="Title of the announcement, release, or advisory")
    content: str = Field(..., description="Full cleaned textual content")
    publication_timestamp: Optional[datetime] = Field(
        default=None,
        description="Authoritative upstream publication timestamp. None if not provided by source.",
    )
    retrieval_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when ORACLE ingested or updated this document",
    )
    content_hash: str = Field(..., description="SHA-256 hash of title and cleaned content")
    document_version: int = Field(default=1, ge=1, description="Incrementing document version number")
    ingestion_status: IngestionStatus = Field(default=IngestionStatus.SUCCESS)
    previous_versions: List[DocumentVersionRecord] = Field(
        default_factory=list,
        description="Historical versions preserved upon detected content mutations",
    )
    ecosystem: str = Field(default="generic", description="Target ecosystem (python, node, cloud, security)")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    """Segment of an ingested document maintaining stable provenance references."""
    id: str = Field(..., description="Stable chunk identifier (e.g. docId_v1_c0)")
    document_id: str = Field(..., description="ID of parent IngestedDocument")
    chunk_index: int = Field(..., ge=0, description="Sequential index within document")
    content: str = Field(..., description="Textual chunk content")
    char_count: int = Field(..., ge=0)
    source_url: str = Field(..., description="Canonical source URL")
    publisher: str = Field(..., description="Publisher name")
    publication_timestamp: Optional[datetime] = Field(
        default=None,
        description="Authoritative publication timestamp",
    )
    retrieval_timestamp: datetime = Field(..., description="Retrieval timestamp")
    content_hash: str = Field(..., description="SHA-256 hash of this chunk's content")
    document_version: int = Field(..., ge=1, description="Document version at time of chunking")
    ecosystem: str = Field(default="generic")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidencePassage(BaseModel):
    """Source-linked retrieved passage with relevance scoring and full provenance."""
    chunk_id: str
    document_id: str
    content: str
    title: Optional[str] = None
    source_url: str
    publisher: str
    publication_timestamp: Optional[datetime] = None
    retrieval_timestamp: datetime
    document_version: int
    content_hash: str
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0.0 to 1.0)")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceSearchQuery(BaseModel):
    """Parameters for semantic evidence retrieval."""
    query: str = Field(..., min_length=2, description="Natural language search or technical query")
    top_k: int = Field(default=5, ge=1, le=50, description="Maximum passages to return")
    publisher: Optional[str] = Field(default=None, description="Optional metadata filter by publisher")
    ecosystem: Optional[str] = Field(default=None, description="Optional metadata filter by ecosystem")
    document_version: Optional[int] = Field(default=None, description="Optional filter by document version")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum relevance threshold")
    rerank: bool = Field(default=True, description="Whether to apply semantic/lexical hybrid reranking")


class EvidenceSearchResponse(BaseModel):
    """Response containing retrieved evidence passages with provenance."""
    query: str
    total_found: int
    passages: List[EvidencePassage]
    reranked: bool
    execution_time_ms: float


class IngestionRunResult(BaseModel):
    """Metrics resulting from an incremental ingestion run."""
    status: str
    sources_processed: int
    documents_ingested: int
    documents_updated: int
    documents_unchanged: int
    chunks_indexed: int
    errors: List[Dict[str, str]] = Field(default_factory=list)
