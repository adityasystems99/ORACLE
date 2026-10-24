"""API routes for ORACLE Live RAG pipeline: source management, ingestion, and evidence search."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from ..schemas.ingestion import IngestionSource
from ..schemas.rag import (
    EvidenceSearchQuery,
    EvidenceSearchResponse,
    IngestedDocument,
    IngestionRunResult,
)

router = APIRouter(prefix="/api/rag", tags=["Live RAG Pipeline"])


@router.get("/sources", response_model=List[Dict[str, Any]])
def list_rag_sources(request: Request):
    """Retrieve all configured ingestion sources with document counts and health status."""
    engine = request.app.state.ingestion_engine
    rag = request.app.state.rag_pipeline
    sources = engine.get_sources()
    documents = rag.get_all_documents()

    # Count documents per source
    doc_count_by_source: Dict[str, int] = {}
    for d in documents:
        doc_count_by_source[d.source_id] = doc_count_by_source.get(d.source_id, 0) + 1

    results = []
    for s in sources:
        results.append({
            "id": s.id,
            "name": s.name,
            "url": s.url,
            "source_type": s.source_type,
            "enabled": s.enabled,
            "ecosystem": s.ecosystem,
            "refresh_interval_minutes": s.refresh_interval_minutes,
            "last_synced_at": s.last_synced_at,
            "last_status": s.last_status,
            "documents_count": doc_count_by_source.get(s.id, 0),
        })
    return results


@router.post("/sources", response_model=IngestionSource)
def create_rag_source(source: IngestionSource, request: Request):
    """Register or update an external intelligence source connector."""
    engine = request.app.state.ingestion_engine
    engine.add_source(source)
    return source


@router.get("/sources/{source_id}/status")
def get_source_status(source_id: str, request: Request):
    """Inspect incremental ingestion status, version stats, and recent documents for a specific source."""
    engine = request.app.state.ingestion_engine
    rag = request.app.state.rag_pipeline
    sources = [s for s in engine.get_sources() if s.id == source_id]
    if not sources:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found.")

    source = sources[0]
    all_docs = [d for d in rag.get_all_documents() if d.source_id == source_id]

    versions_count = sum(len(d.previous_versions) for d in all_docs)

    return {
        "source": source,
        "total_documents": len(all_docs),
        "total_historical_versions": versions_count,
        "recent_documents": [
            {
                "id": d.id,
                "title": d.title,
                "version": d.document_version,
                "status": d.ingestion_status,
                "publication_timestamp": d.publication_timestamp,
                "retrieval_timestamp": d.retrieval_timestamp,
                "content_hash": d.content_hash,
            }
            for d in all_docs[:10]
        ],
    }


@router.post("/ingest", response_model=IngestionRunResult)
async def trigger_rag_ingest(
    request: Request,
    source_id: Optional[str] = Query(default=None, description="Optional specific source ID to poll"),
):
    """Trigger an on-demand incremental ingestion run with deduplication, versioning, and chunk indexing."""
    rag = request.app.state.rag_pipeline
    return await rag.run_ingestion_pipeline(source_id=source_id)


@router.post("/search", response_model=EvidenceSearchResponse)
def search_evidence_passages(query: EvidenceSearchQuery, request: Request):
    """Perform semantic retrieval and reranking for source-linked evidence passages."""
    rag = request.app.state.rag_pipeline
    return rag.search_evidence(query)


@router.get("/documents", response_model=List[IngestedDocument])
def list_ingested_documents(
    request: Request,
    publisher: Optional[str] = Query(default=None, description="Filter by publisher"),
    ecosystem: Optional[str] = Query(default=None, description="Filter by ecosystem"),
    limit: int = Query(default=50, ge=1, le=200),
):
    """List ingested documents with active version, publication timestamps, and hashes."""
    rag = request.app.state.rag_pipeline
    docs = rag.get_all_documents()
    if publisher:
        docs = [d for d in docs if publisher.lower() in d.publisher.lower()]
    if ecosystem:
        docs = [d for d in docs if d.ecosystem.lower() == ecosystem.lower()]
    return docs[:limit]


@router.get("/documents/{doc_id}", response_model=IngestedDocument)
def get_ingested_document(doc_id: str, request: Request):
    """Retrieve full details of an ingested document including preserved historical version archives."""
    rag = request.app.state.rag_pipeline
    doc = rag.get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    return doc
