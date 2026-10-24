"""Document chunker creating stable, source-linked text passages."""

import hashlib
import re
from typing import List, Optional
from ..schemas.rag import DocumentChunk, IngestedDocument


class TextChunker:
    """Splits ingested documents into coherent passages with stable provenance references."""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 80,
    ):
        if chunk_size <= chunk_overlap:
            raise ValueError("chunk_size must be strictly greater than chunk_overlap.")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @staticmethod
    def compute_hash(text: str) -> str:
        """Calculate deterministic SHA-256 hash for chunk contents."""
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

    def split_text(self, text: str) -> List[str]:
        """Split text cleanly respecting paragraph and sentence boundaries."""
        clean_text = text.strip()
        if not clean_text:
            return []

        if len(clean_text) <= self.chunk_size:
            return [clean_text]

        # Break text into structural paragraphs / lines first
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", clean_text) if p.strip()]
        raw_units: List[str] = []
        for p in paragraphs:
            if len(p) <= self.chunk_size:
                raw_units.append(p)
            else:
                # Break long paragraph by sentences
                sentences = re.split(r"(?<=[.!?])\s+", p)
                raw_units.extend([s.strip() for s in sentences if s.strip()])

        # Combine units into sliding windows
        chunks: List[str] = []
        current_chunk: List[str] = []
        current_len = 0

        for unit in raw_units:
            unit_len = len(unit)
            if current_len + unit_len + 1 > self.chunk_size and current_chunk:
                merged = " ".join(current_chunk).strip()
                if merged:
                    chunks.append(merged)

                # Keep overlap from the end of current_chunk
                overlap_units: List[str] = []
                overlap_len = 0
                for u in reversed(current_chunk):
                    if overlap_len + len(u) + 1 <= self.chunk_overlap:
                        overlap_units.insert(0, u)
                        overlap_len += len(u) + 1
                    else:
                        break

                current_chunk = overlap_units + [unit]
                current_len = sum(len(u) for u in current_chunk) + len(current_chunk) - 1
            else:
                current_chunk.append(unit)
                current_len += unit_len + (1 if current_len > 0 else 0)

        if current_chunk:
            final_text = " ".join(current_chunk).strip()
            if final_text and (not chunks or chunks[-1] != final_text):
                chunks.append(final_text)

        # Fallback: if text was unbroken (e.g. huge continuous string), slice deterministically
        if not chunks:
            step = self.chunk_size - self.chunk_overlap
            for i in range(0, len(clean_text), step):
                chunk = clean_text[i : i + self.chunk_size].strip()
                if chunk:
                    chunks.append(chunk)

        return chunks

    def chunk_document(self, doc: IngestedDocument) -> List[DocumentChunk]:
        """Convert an IngestedDocument into DocumentChunks preserving provenance."""
        # Include title in the first context window if present
        text_to_chunk = doc.content
        if doc.title and not doc.content.startswith(doc.title):
            text_to_chunk = f"{doc.title}\n\n{doc.content}"

        text_pieces = self.split_text(text_to_chunk)
        chunks: List[DocumentChunk] = []

        for idx, piece in enumerate(text_pieces):
            chunk_hash = self.compute_hash(piece)
            chunk_id = f"{doc.id}_v{doc.document_version}_c{idx}"

            chunk = DocumentChunk(
                id=chunk_id,
                document_id=doc.id,
                chunk_index=idx,
                content=piece,
                char_count=len(piece),
                source_url=doc.source_url,
                publisher=doc.publisher,
                publication_timestamp=doc.publication_timestamp,
                retrieval_timestamp=doc.retrieval_timestamp,
                content_hash=chunk_hash,
                document_version=doc.document_version,
                ecosystem=doc.ecosystem,
                metadata={
                    "title": doc.title,
                    "source_id": doc.source_id,
                    "total_chunks": len(text_pieces),
                    **doc.metadata,
                },
            )
            chunks.append(chunk)

        return chunks
