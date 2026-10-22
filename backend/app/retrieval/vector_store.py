"""Vector storage and similarity retrieval engine supporting ChromaDB with fallback."""

import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional
from .embeddings import BaseEmbeddingProvider, get_embedder
from ..config import get_settings

logger = logging.getLogger(__name__)


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class VectorStore:
    """Unified Vector Store supporting ChromaDB with persistent fallback."""

    def __init__(
        self,
        persist_dir: Optional[Path] = None,
        embedder: Optional[BaseEmbeddingProvider] = None,
    ):
        self.settings = get_settings()
        self.persist_dir = persist_dir or self.settings.CHROMA_PERSIST_DIR
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.embedder = embedder or get_embedder()

        self.chroma_client = None
        self._init_chroma()

        # In-memory index with disk sync for fallback or hybrid access
        self.local_indices: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._load_local_indices()

    def _init_chroma(self) -> None:
        """Attempt to initialize ChromaDB PersistentClient."""
        try:
            import chromadb
            self.chroma_client = chromadb.PersistentClient(path=str(self.persist_dir))
            logger.info(f"Initialized ChromaDB persistent client at {self.persist_dir}")
        except Exception as e:
            logger.info(f"ChromaDB not active ({e}); using persistent vector index at {self.persist_dir}")
            self.chroma_client = None

    def _get_local_file(self, collection_name: str) -> Path:
        return self.persist_dir / f"vector_index_{collection_name}.json"

    def _load_local_indices(self) -> None:
        for p in self.persist_dir.glob("vector_index_*.json"):
            col_name = p.stem.replace("vector_index_", "")
            try:
                with open(p, "r", encoding="utf-8") as f:
                    self.local_indices[col_name] = json.load(f)
            except Exception as e:
                logger.error(f"Error loading local vector index {p}: {e}")

    def _save_local_index(self, collection_name: str) -> None:
        p = self._get_local_file(collection_name)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.local_indices.get(collection_name, {}), f, indent=2)

    def upsert_documents(
        self,
        collection_name: str,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Add or update documents with vector embeddings."""
        if not ids or not documents:
            return

        embeddings = self.embedder.embed_batch(documents)
        metas = metadatas or [{} for _ in ids]

        # 1. Update ChromaDB if available
        if self.chroma_client:
            try:
                col = self.chroma_client.get_or_create_collection(name=collection_name)
                col.upsert(
                    ids=ids,
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metas,
                )
            except Exception as e:
                logger.error(f"ChromaDB upsert failed, falling back to local: {e}")

        # 2. Update persistent local index
        if collection_name not in self.local_indices:
            self.local_indices[collection_name] = {}

        for doc_id, doc, emb, meta in zip(ids, documents, embeddings, metas):
            self.local_indices[collection_name][doc_id] = {
                "document": doc,
                "embedding": emb,
                "metadata": meta,
            }

        self._save_local_index(collection_name)

    def query_similar(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve most similar documents based on cosine distance."""
        query_emb = self.embedder.embed_text(query_text)

        # 1. Try ChromaDB
        if self.chroma_client:
            try:
                col = self.chroma_client.get_collection(name=collection_name)
                results = col.query(
                    query_embeddings=[query_emb],
                    n_results=n_results,
                    include=["documents", "metadatas", "distances"],
                )
                output = []
                if results and "ids" in results and results["ids"]:
                    for doc_id, doc, meta, dist in zip(
                        results["ids"][0],
                        results["documents"][0],
                        results["metadatas"][0],
                        results["distances"][0] if "distances" in results else [0.0] * len(results["ids"][0]),
                    ):
                        output.append({
                            "id": doc_id,
                            "document": doc,
                            "metadata": meta,
                            "score": round(1.0 - dist if dist <= 1.0 else 0.5, 3),
                        })
                return output
            except Exception as e:
                logger.debug(f"ChromaDB query failed or collection empty: {e}")

        # 2. Local index fallback
        col_data = self.local_indices.get(collection_name, {})
        if not col_data:
            return []

        scored = []
        for doc_id, item in col_data.items():
            emb = item.get("embedding", [])
            score = cosine_similarity(query_emb, emb)
            scored.append({
                "id": doc_id,
                "document": item.get("document", ""),
                "metadata": item.get("metadata", {}),
                "score": round(score, 3),
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:n_results]
