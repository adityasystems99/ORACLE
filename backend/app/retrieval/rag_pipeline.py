"""ORACLE Live RAG Pipeline orchestrator."""

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional
from .chunking import TextChunker
from .reranking import BaseReranker, HybridLexicalReranker
from .vector_store import VectorStore
from ..config import get_settings
from ..ingestion.engine import CONNECTOR_REGISTRY
from ..schemas.ingestion import IngestionSource
from ..schemas.rag import (
    DocumentChunk,
    DocumentVersionRecord,
    EvidencePassage,
    EvidenceSearchQuery,
    EvidenceSearchResponse,
    IngestedDocument,
    IngestionRunResult,
    IngestionStatus,
)
from ..storage.disk_store import DiskStore

logger = logging.getLogger("oracle.rag")

EVIDENCE_COLLECTION = "oracle_evidence"


class RAGPipeline:
    """Orchestrates reliable ingestion, versioning, chunking, indexing, and retrieval."""

    def __init__(
        self,
        disk_store: DiskStore,
        vector_store: VectorStore,
        chunker: Optional[TextChunker] = None,
        reranker: Optional[BaseReranker] = None,
    ):
        self.settings = get_settings()
        self.disk_store = disk_store
        self.vector_store = vector_store
        self.chunker = chunker or TextChunker(chunk_size=480, chunk_overlap=80)
        self.reranker = reranker or HybridLexicalReranker()

    def get_all_documents(self) -> List[IngestedDocument]:
        """Load all ingested canonical documents."""
        return self.disk_store.load_all("documents", IngestedDocument)

    def get_document_by_id(self, doc_id: str) -> Optional[IngestedDocument]:
        """Retrieve a specific document with its complete version history."""
        docs = self.get_all_documents()
        for d in docs:
            if d.id == doc_id:
                return d
        return None

    def _index_chunks(self, chunks: List[DocumentChunk]) -> None:
        """Upsert document chunks with vector embeddings and metadata filters."""
        if not chunks:
            return

        ids = [c.id for c in chunks]
        texts = [c.content for c in chunks]
        metadatas = [
            {
                "chunk_id": c.id,
                "document_id": c.document_id,
                "source_url": c.source_url,
                "publisher": c.publisher,
                "publication_timestamp": c.publication_timestamp.isoformat() if c.publication_timestamp else "",
                "retrieval_timestamp": c.retrieval_timestamp.isoformat(),
                "document_version": c.document_version,
                "content_hash": c.content_hash,
                "ecosystem": c.ecosystem,
                "chunk_index": c.chunk_index,
            }
            for c in chunks
        ]

        self.vector_store.upsert_documents(
            collection_name=EVIDENCE_COLLECTION,
            ids=ids,
            documents=texts,
            metadatas=metadatas,
        )

        # Also persist chunk objects to disk store for inspection
        for c in chunks:
            self.disk_store.upsert_item("chunks", c)

    async def ingest_source(self, source: IngestionSource) -> Dict[str, Any]:
        """Poll and incrementally ingest a single source with deduplication and versioning."""
        connector_cls = CONNECTOR_REGISTRY.get(source.source_type)
        if not connector_cls:
            error_msg = f"No connector registered for source type: {source.source_type}"
            logger.error(error_msg)
            return {"ingested": 0, "updated": 0, "unchanged": 0, "chunks": 0, "error": error_msg}

        connector = connector_cls(source)
        try:
            # 1. Fetch normalized documents with provenance
            raw_docs = await connector.fetch_documents()
            source.last_synced_at = datetime.now(timezone.utc)
            source.last_status = "success"
            self.disk_store.upsert_item("sources", source)
        except Exception as e:
            source.last_synced_at = datetime.now(timezone.utc)
            source.last_status = f"error: {str(e)}"
            self.disk_store.upsert_item("sources", source)
            logger.error(f"Error executing connector for {source.id}: {e}", exc_info=True)
            return {"ingested": 0, "updated": 0, "unchanged": 0, "chunks": 0, "error": str(e)}

        stored_docs_map = {d.id: d for d in self.get_all_documents()}
        new_count = 0
        updated_count = 0
        unchanged_count = 0
        chunks_count = 0

        for incoming in raw_docs:
            if incoming.id not in stored_docs_map:
                # Brand new document
                incoming.document_version = 1
                incoming.ingestion_status = IngestionStatus.SUCCESS
                stored_docs_map[incoming.id] = incoming

                # Chunk and index
                chunks = self.chunker.chunk_document(incoming)
                self._index_chunks(chunks)
                chunks_count += len(chunks)
                new_count += 1
                logger.info(f"Ingested new document: {incoming.title} ({len(chunks)} chunks)")

            else:
                existing = stored_docs_map[incoming.id]
                if incoming.content_hash == existing.content_hash:
                    # Content is identical -> deduplicated
                    existing.retrieval_timestamp = datetime.now(timezone.utc)
                    existing.ingestion_status = IngestionStatus.UNCHANGED
                    unchanged_count += 1
                else:
                    # Content has mutated! Archive previous version and increment
                    archive_version = DocumentVersionRecord(
                        version=existing.document_version,
                        content_hash=existing.content_hash,
                        archived_at=datetime.now(timezone.utc),
                        content_preview=existing.content[:240],
                        publication_timestamp=existing.publication_timestamp,
                    )
                    existing.previous_versions.append(archive_version)
                    existing.document_version += 1
                    existing.content = incoming.content
                    existing.title = incoming.title
                    existing.content_hash = incoming.content_hash
                    existing.publication_timestamp = incoming.publication_timestamp or existing.publication_timestamp
                    existing.retrieval_timestamp = datetime.now(timezone.utc)
                    existing.ingestion_status = IngestionStatus.UPDATED

                    # Re-chunk updated document version and index
                    chunks = self.chunker.chunk_document(existing)
                    self._index_chunks(chunks)
                    chunks_count += len(chunks)
                    updated_count += 1
                    logger.info(
                        f"Detected mutation for document {existing.id} -> updated to version {existing.document_version} ({len(chunks)} chunks)"
                    )

        # Persist documents to disk store
        self.disk_store.save_all("documents", list(stored_docs_map.values()))

        return {
            "ingested": new_count,
            "updated": updated_count,
            "unchanged": unchanged_count,
            "chunks": chunks_count,
            "error": None,
        }

    async def ingest_documents(self, raw_docs: List[IngestedDocument]) -> Dict[str, Any]:
        """Directly ingest, version, chunk, and index a batch of documents."""
        stored_docs_map = {d.id: d for d in self.get_all_documents()}
        new_count = 0
        updated_count = 0
        unchanged_count = 0
        chunks_count = 0

        for incoming in raw_docs:
            if incoming.id not in stored_docs_map:
                incoming.document_version = 1
                incoming.ingestion_status = IngestionStatus.SUCCESS
                stored_docs_map[incoming.id] = incoming
                chunks = self.chunker.chunk_document(incoming)
                self._index_chunks(chunks)
                chunks_count += len(chunks)
                new_count += 1
            else:
                existing = stored_docs_map[incoming.id]
                if incoming.content_hash == existing.content_hash:
                    existing.retrieval_timestamp = datetime.now(timezone.utc)
                    existing.ingestion_status = IngestionStatus.UNCHANGED
                    unchanged_count += 1
                else:
                    archive_version = DocumentVersionRecord(
                        version=existing.document_version,
                        content_hash=existing.content_hash,
                        archived_at=datetime.now(timezone.utc),
                        content_preview=existing.content[:240],
                        publication_timestamp=existing.publication_timestamp,
                    )
                    existing.previous_versions.append(archive_version)
                    existing.document_version += 1
                    existing.content = incoming.content
                    existing.title = incoming.title
                    existing.content_hash = incoming.content_hash
                    existing.publication_timestamp = incoming.publication_timestamp or existing.publication_timestamp
                    existing.retrieval_timestamp = datetime.now(timezone.utc)
                    existing.ingestion_status = IngestionStatus.UPDATED
                    chunks = self.chunker.chunk_document(existing)
                    self._index_chunks(chunks)
                    chunks_count += len(chunks)
                    updated_count += 1

        self.disk_store.save_all("documents", list(stored_docs_map.values()))
        return {
            "ingested": new_count,
            "updated": updated_count,
            "unchanged": unchanged_count,
            "chunks": chunks_count,
            "error": None,
        }

    async def run_ingestion_pipeline(self, source_id: Optional[str] = None) -> IngestionRunResult:
        """Run incremental ingestion across all enabled sources or a specific source."""
        all_sources = self.disk_store.load_all("sources", IngestionSource)
        if source_id:
            target_sources = [s for s in all_sources if s.id == source_id]
        else:
            target_sources = [s for s in all_sources if s.enabled]

        total_ingested = 0
        total_updated = 0
        total_unchanged = 0
        total_chunks = 0
        errors: List[Dict[str, str]] = []

        for source in target_sources:
            res = await self.ingest_source(source)
            total_ingested += res["ingested"]
            total_updated += res["updated"]
            total_unchanged += res["unchanged"]
            total_chunks += res["chunks"]
            if res.get("error"):
                errors.append({"source_id": source.id, "error": res["error"]})

        return IngestionRunResult(
            status="completed",
            sources_processed=len(target_sources),
            documents_ingested=total_ingested,
            documents_updated=total_updated,
            documents_unchanged=total_unchanged,
            chunks_indexed=total_chunks,
            errors=errors,
        )

    def search_evidence(self, query: EvidenceSearchQuery) -> EvidenceSearchResponse:
        """Retrieve source-linked evidence passages with metadata filtering and reranking."""
        return self.search(query)

    def search(self, query: EvidenceSearchQuery) -> EvidenceSearchResponse:
        """Retrieve source-linked evidence passages with metadata filtering and reranking."""
        start_time = time.perf_counter()

        # Build metadata where filter
        where_filter: Dict[str, Any] = {}
        if query.publisher:
            where_filter["publisher"] = query.publisher
        if query.ecosystem:
            where_filter["ecosystem"] = query.ecosystem
        if query.document_version is not None:
            where_filter["document_version"] = query.document_version

        # Oversample candidates if reranking is enabled
        fetch_limit = query.top_k * 3 if query.rerank else query.top_k

        raw_matches = self.vector_store.query_similar(
            collection_name=EVIDENCE_COLLECTION,
            query_text=query.query,
            n_results=fetch_limit,
            where=where_filter if where_filter else None,
        )

        passages: List[EvidencePassage] = []
        for match in raw_matches:
            meta = match.get("metadata", {})
            score = float(match.get("score", 0.0))

            if score < query.min_score:
                continue

            pub_dt_str = meta.get("publication_timestamp")
            pub_dt = datetime.fromisoformat(pub_dt_str) if pub_dt_str else None

            ret_dt_str = meta.get("retrieval_timestamp")
            ret_dt = (
                datetime.fromisoformat(ret_dt_str)
                if ret_dt_str
                else datetime.now(timezone.utc)
            )

            passage = EvidencePassage(
                chunk_id=meta.get("chunk_id", match.get("id", "chunk_unknown")),
                document_id=meta.get("document_id", "doc_unknown"),
                content=match.get("document", ""),
                title=meta.get("title") or meta.get("document_title"),
                source_url=meta.get("source_url", ""),
                publisher=meta.get("publisher", "Unknown Publisher"),
                publication_timestamp=pub_dt,
                retrieval_timestamp=ret_dt,
                document_version=int(meta.get("document_version", 1)),
                content_hash=meta.get("content_hash", ""),
                score=score,
                metadata=meta,
            )
            passages.append(passage)

        # Apply reranker if requested
        if query.rerank and self.reranker:
            if passages:
                passages = self.reranker.rerank(query.query, passages, top_k=query.top_k)
            reranked = True
        else:
            passages = passages[: query.top_k]
            reranked = False

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return EvidenceSearchResponse(
            query=query.query,
            total_found=len(passages),
            passages=passages,
            reranked=reranked,
            execution_time_ms=duration_ms,
        )


LiveRAGPipeline = RAGPipeline

