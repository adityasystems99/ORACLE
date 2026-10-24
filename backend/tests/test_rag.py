"""Automated test suite verifying ORACLE Live RAG pipeline."""

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import httpx

from app.config import Settings
from app.ingestion.base import BaseIngestionConnector
from app.ingestion.rss import RSSConnector
from app.main import create_app
from app.retrieval.chunking import TextChunker
from app.retrieval.embeddings import LightweightFeatureEmbedder, get_embedder
from app.retrieval.rag_pipeline import RAGPipeline
from app.retrieval.reranking import HybridLexicalReranker, PassThroughReranker
from app.retrieval.vector_store import VectorStore
from app.schemas.ingestion import IngestionSource, SourceType
from app.schemas.rag import (
    EvidencePassage,
    EvidenceSearchQuery,
    IngestedDocument,
    IngestionStatus,
)
from app.storage.disk_store import DiskStore


# ---------------------------------------------------------------------------
# Test Fixtures & Sample Reproducible Dataset
# ---------------------------------------------------------------------------

SAMPLE_RSS_XML_V1 = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>FastAPI Official Releases</title>
    <link>https://fastapi.tiangolo.com</link>
    <description>FastAPI changelog stream</description>
    <item>
      <title>FastAPI 0.111.0 Released</title>
      <link>https://github.com/fastapi/fastapi/releases/tag/0.111.0</link>
      <description><![CDATA[FastAPI 0.111.0 introduces enhanced Pydantic v2 compatibility and strict validation for query parameters. Deprecates legacy regex keyword in favor of pattern.]]></description>
      <pubDate>Mon, 20 May 2024 10:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>
"""

# Mutated version of the same document for update & versioning verification
SAMPLE_RSS_XML_V2 = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>FastAPI Official Releases</title>
    <link>https://fastapi.tiangolo.com</link>
    <description>FastAPI changelog stream</description>
    <item>
      <title>FastAPI 0.111.0 Released</title>
      <link>https://github.com/fastapi/fastapi/releases/tag/0.111.0</link>
      <description><![CDATA[FastAPI 0.111.0 introduces enhanced Pydantic v2 compatibility and strict validation for query parameters. Deprecates legacy regex keyword in favor of pattern. CRITICAL SECURITY UPDATE: Patched CVE-2024-5555 multipart boundary parser vulnerability.]]></description>
      <pubDate>Tue, 21 May 2024 14:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>
"""

# Feed without publication timestamp to verify rule: do NOT invent timestamps
SAMPLE_RSS_NO_DATE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Undated Tech Advisory</title>
    <link>https://example.com/advisories</link>
    <description>Advisories without upstream date header</description>
    <item>
      <title>Advisory Notice: OpenSSL Cipher Deprecation</title>
      <link>https://example.com/advisories/openssl-notice</link>
      <description>Legacy 3DES ciphers are now disabled by default across all secure endpoints.</description>
    </item>
  </channel>
</rss>
"""


@pytest.fixture
def temp_rag_env(tmp_path: Path):
    """Provides an isolated DiskStore, VectorStore, and RAGPipeline."""
    disk_store = DiskStore(tmp_path / "data")
    vector_store = VectorStore(
        persist_dir=tmp_path / "chroma",
        embedder=LightweightFeatureEmbedder(dimension=64),
    )
    chunker = TextChunker(chunk_size=200, chunk_overlap=40)
    reranker = HybridLexicalReranker()
    pipeline = RAGPipeline(
        disk_store=disk_store,
        vector_store=vector_store,
        chunker=chunker,
        reranker=reranker,
    )
    return {
        "disk_store": disk_store,
        "vector_store": vector_store,
        "pipeline": pipeline,
        "chunker": chunker,
        "reranker": reranker,
    }


# ---------------------------------------------------------------------------
# Test 1: Chunking & Stable Provenance References
# ---------------------------------------------------------------------------

def test_chunking_preserves_provenance(temp_rag_env):
    chunker: TextChunker = temp_rag_env["chunker"]
    pub_time = datetime(2024, 5, 20, 10, 0, 0, tzinfo=timezone.utc)
    ret_time = datetime(2024, 5, 20, 10, 5, 0, tzinfo=timezone.utc)

    doc = IngestedDocument(
        id="doc_fastapi_01",
        source_id="src_fastapi",
        source_url="https://github.com/fastapi/fastapi/releases/tag/0.111.0",
        publisher="FastAPI / Tiangolo",
        title="FastAPI 0.111.0 Released",
        content="This is a test release note. It contains multiple sentences designed to verify chunk boundaries.\n\nSecond paragraph discusses migration steps and breaking interface modifications. Ensure regex is replaced with pattern.",
        publication_timestamp=pub_time,
        retrieval_timestamp=ret_time,
        content_hash="abc123hash",
        document_version=1,
        ingestion_status=IngestionStatus.SUCCESS,
        ecosystem="python",
    )

    chunks = chunker.chunk_document(doc)
    assert len(chunks) >= 1

    for idx, c in enumerate(chunks):
        assert c.document_id == "doc_fastapi_01"
        assert c.chunk_index == idx
        assert c.source_url == doc.source_url
        assert c.publisher == "FastAPI / Tiangolo"
        assert c.publication_timestamp == pub_time
        assert c.retrieval_timestamp == ret_time
        assert c.document_version == 1
        assert c.ecosystem == "python"
        assert len(c.content_hash) == 64  # SHA-256


# ---------------------------------------------------------------------------
# Test 2: Ingestion, Deduplication & Version Updates
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_incremental_ingestion_and_deduplication(temp_rag_env, monkeypatch):
    pipeline: RAGPipeline = temp_rag_env["pipeline"]
    disk_store: DiskStore = temp_rag_env["disk_store"]

    source = IngestionSource(
        id="src_fastapi_test",
        name="FastAPI Releases",
        url="https://example.com/fastapi/releases.rss",
        source_type=SourceType.RSS,
        ecosystem="python",
    )
    disk_store.upsert_item("sources", source)

    # Mock HTTP response with V1 XML
    async def mock_fetch_v1(*args, **kwargs):
        return httpx.Response(200, text=SAMPLE_RSS_XML_V1)

    monkeypatch.setattr(BaseIngestionConnector, "fetch_with_retry", mock_fetch_v1)

    # 1. First Ingestion Run -> Document should be newly ingested (version 1)
    res1 = await pipeline.run_ingestion_pipeline("src_fastapi_test")
    assert res1.documents_ingested == 1
    assert res1.documents_updated == 0
    assert res1.documents_unchanged == 0
    assert res1.chunks_indexed >= 1

    docs_v1 = pipeline.get_all_documents()
    assert len(docs_v1) == 1
    doc_v1 = docs_v1[0]
    assert doc_v1.document_version == 1
    assert doc_v1.ingestion_status == IngestionStatus.SUCCESS
    assert len(doc_v1.previous_versions) == 0
    assert doc_v1.publication_timestamp == datetime(2024, 5, 20, 10, 0, 0, tzinfo=timezone.utc)

    # 2. Second Ingestion Run with IDENTICAL content -> Deduplication (unchanged)
    res2 = await pipeline.run_ingestion_pipeline("src_fastapi_test")
    assert res2.documents_ingested == 0
    assert res2.documents_updated == 0
    assert res2.documents_unchanged == 1  # Deduplicated!
    assert res2.chunks_indexed == 0

    doc_after_dedup = pipeline.get_document_by_id(doc_v1.id)
    assert doc_after_dedup.document_version == 1
    assert doc_after_dedup.ingestion_status == IngestionStatus.UNCHANGED

    # 3. Third Ingestion Run with MUTATED content (V2) -> Update & Version History
    async def mock_fetch_v2(*args, **kwargs):
        return httpx.Response(200, text=SAMPLE_RSS_XML_V2)

    monkeypatch.setattr(BaseIngestionConnector, "fetch_with_retry", mock_fetch_v2)

    res3 = await pipeline.run_ingestion_pipeline("src_fastapi_test")
    assert res3.documents_ingested == 0
    assert res3.documents_updated == 1
    assert res3.documents_unchanged == 0
    assert res3.chunks_indexed >= 1

    doc_v2 = pipeline.get_document_by_id(doc_v1.id)
    assert doc_v2.document_version == 2
    assert doc_v2.ingestion_status == IngestionStatus.UPDATED
    assert "CVE-2024-5555" in doc_v2.content

    # Verify previous version history preservation
    assert len(doc_v2.previous_versions) == 1
    archived = doc_v2.previous_versions[0]
    assert archived.version == 1
    assert archived.content_hash == doc_v1.content_hash
    assert "FastAPI 0.111.0 introduces enhanced" in archived.content_preview


# ---------------------------------------------------------------------------
# Test 3: Reliability Rule - Do NOT invent publication timestamps
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_invented_timestamps(temp_rag_env, monkeypatch):
    pipeline: RAGPipeline = temp_rag_env["pipeline"]
    disk_store: DiskStore = temp_rag_env["disk_store"]

    source = IngestionSource(
        id="src_undated",
        name="Undated Feed",
        url="https://example.com/undated.rss",
        source_type=SourceType.RSS,
    )
    disk_store.upsert_item("sources", source)

    async def mock_fetch(*args, **kwargs):
        return httpx.Response(200, text=SAMPLE_RSS_NO_DATE)

    monkeypatch.setattr(BaseIngestionConnector, "fetch_with_retry", mock_fetch)

    await pipeline.run_ingestion_pipeline("src_undated")
    docs = pipeline.get_all_documents()
    assert len(docs) == 1
    # publication_timestamp MUST be None, not datetime.now()!
    assert docs[0].publication_timestamp is None
    # retrieval_timestamp records when ORACLE ingested it
    assert docs[0].retrieval_timestamp is not None


# ---------------------------------------------------------------------------
# Test 4: Semantic Search & Metadata Filtering
# ---------------------------------------------------------------------------

def test_semantic_retrieval_with_metadata_filters(temp_rag_env):
    pipeline: RAGPipeline = temp_rag_env["pipeline"]
    chunker: TextChunker = temp_rag_env["chunker"]

    # Index two documents in different ecosystems and publishers
    doc_python = IngestedDocument(
        id="doc_py_01",
        source_id="src_fastapi",
        source_url="https://fastapi.tiangolo.com/release",
        publisher="FastAPI / Tiangolo",
        title="FastAPI Path Parameters",
        content="FastAPI automatically serializes and validates path parameters using Pydantic schemas. Supports async endpoints.",
        content_hash="pyhash1",
        document_version=1,
        ecosystem="python",
    )
    doc_node = IngestedDocument(
        id="doc_node_01",
        source_id="src_nextjs",
        source_url="https://nextjs.org/releases",
        publisher="Vercel",
        title="Next.js App Router Server Actions",
        content="Next.js server actions provide seamless client-server RPC execution in React Server Components.",
        content_hash="nodehash1",
        document_version=1,
        ecosystem="node",
    )

    pipeline._index_chunks(chunker.chunk_document(doc_python))
    pipeline._index_chunks(chunker.chunk_document(doc_node))

    # Query matching python
    q_python = EvidenceSearchQuery(
        query="Pydantic path parameter validation",
        ecosystem="python",
        top_k=5,
    )
    res_py = pipeline.search_evidence(q_python)
    assert res_py.total_found >= 1
    for p in res_py.passages:
        assert p.metadata.get("ecosystem") == "python"
        assert p.publisher == "FastAPI / Tiangolo"

    # Query matching node with publisher filter
    q_node = EvidenceSearchQuery(
        query="Server actions React",
        publisher="Vercel",
        top_k=5,
    )
    res_node = pipeline.search_evidence(q_node)
    assert res_node.total_found >= 1
    assert res_node.passages[0].publisher == "Vercel"


# ---------------------------------------------------------------------------
# Test 5: Hybrid Reranking Logic
# ---------------------------------------------------------------------------

def test_hybrid_reranker():
    reranker = HybridLexicalReranker(semantic_weight=0.5, lexical_weight=0.5)

    passages = [
        EvidencePassage(
            chunk_id="c1",
            document_id="d1",
            content="General announcement about web framework updates and minor dependency bumps.",
            source_url="https://example.com/1",
            publisher="Generic Org",
            retrieval_timestamp=datetime.now(timezone.utc),
            document_version=1,
            content_hash="h1",
            score=0.80,  # High vector similarity by chance
        ),
        EvidencePassage(
            chunk_id="c2",
            document_id="d2",
            content="Critical security patch for CVE-2024-9999 resolving remote code execution in multipart headers.",
            source_url="https://example.com/2",
            publisher="Security Team",
            retrieval_timestamp=datetime.now(timezone.utc),
            document_version=1,
            content_hash="h2",
            score=0.65,  # Moderate vector similarity
        ),
    ]

    # Technical query specifically searching for CVE-2024-9999
    reranked = reranker.rerank("CVE-2024-9999 remote code execution", passages, top_k=2)
    assert len(reranked) == 2
    # The passage with the exact CVE match should be boosted to rank 1
    assert reranked[0].chunk_id == "c2"
    assert "CVE-2024-9999" in reranked[0].content


# ---------------------------------------------------------------------------
# Test 6: Network Error & Unavailability Resilience (No Crash)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unavailable_source_does_not_crash(temp_rag_env, monkeypatch):
    pipeline: RAGPipeline = temp_rag_env["pipeline"]
    disk_store: DiskStore = temp_rag_env["disk_store"]

    failing_source = IngestionSource(
        id="src_broken",
        name="Broken Endpoint",
        url="https://offline.invalid/feed.xml",
        source_type=SourceType.RSS,
    )
    disk_store.upsert_item("sources", failing_source)

    def mock_network_failure(*args, **kwargs):
        raise httpx.ConnectError("Connection refused by target host")

    monkeypatch.setattr(BaseIngestionConnector, "fetch_with_retry", mock_network_failure)

    # Ingestion run should complete cleanly without throwing an unhandled exception
    result = await pipeline.run_ingestion_pipeline("src_broken")
    assert result.status == "completed"
    assert result.documents_ingested == 0
    assert len(result.errors) == 1
    assert "src_broken" == result.errors[0]["source_id"]


# ---------------------------------------------------------------------------
# Test 7: FastAPI Endpoints Verification
# ---------------------------------------------------------------------------

def test_api_rag_endpoints(monkeypatch):
    app = create_app()
    client = TestClient(app)

    # 1. GET /api/rag/sources
    res_sources = client.get("/api/rag/sources")
    assert res_sources.status_code == 200
    sources_data = res_sources.json()
    assert isinstance(sources_data, list)
    assert len(sources_data) >= 1

    # 2. POST /api/rag/sources (Register new source)
    new_src = {
        "id": "src_pytest_test",
        "name": "Pytest Official News",
        "url": "https://pytest.org/news.rss",
        "source_type": "rss",
        "ecosystem": "python",
        "refresh_interval_minutes": 15,
    }
    res_create = client.post("/api/rag/sources", json=new_src)
    assert res_create.status_code == 200
    assert res_create.json()["id"] == "src_pytest_test"

    # 3. GET /api/rag/sources/{id}/status
    res_status = client.get("/api/rag/sources/src_pytest_test/status")
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert status_data["source"]["id"] == "src_pytest_test"

    # 4. POST /api/rag/search
    search_payload = {
        "query": "FastAPI Pydantic v2 breaking change",
        "top_k": 3,
        "rerank": True,
    }
    res_search = client.post("/api/rag/search", json=search_payload)
    assert res_search.status_code == 200
    search_data = res_search.json()
    assert "query" in search_data
    assert "passages" in search_data
    assert "reranked" in search_data
    assert search_data["reranked"] is True

    # 5. GET /api/rag/documents
    res_docs = client.get("/api/rag/documents")
    assert res_docs.status_code == 200
    assert isinstance(res_docs.json(), list)
