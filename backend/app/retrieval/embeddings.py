"""Embedding generation interface with fallback support."""

import abc
import hashlib
import logging
import math
import re
from typing import List, Optional
from ..config import get_settings

logger = logging.getLogger(__name__)


class BaseEmbeddingProvider(abc.ABC):
    """Abstract interface for generating vector embeddings."""

    @abc.abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for a single text."""
        pass

    @abc.abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        pass


class LightweightFeatureEmbedder(BaseEmbeddingProvider):
    """Deterministic, high-performance semantic hash & term frequency embedder.

    Produces normalized 128-dimensional dense vectors suitable for cosine similarity
    without requiring external model binaries or heavy torch dependencies.
    """

    def __init__(self, dimension: int = 128):
        self.dimension = dimension

    def _tokenize(self, text: str) -> List[str]:
        words = re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text.lower())
        # Character n-grams for typo resilience
        ngrams = [text[i : i + 3].lower() for i in range(len(text) - 2)] if len(text) >= 3 else []
        return words + ngrams[:50]

    def embed_text(self, text: str) -> List[float]:
        tokens = self._tokenize(text)
        vector = [0.0] * self.dimension
        if not tokens:
            return vector

        for token in tokens:
            # Deterministic bucket hash
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            sign = 1.0 if (h // self.dimension) % 2 == 0 else -1.0
            vector[idx] += sign * (1.0 + math.log(1 + tokens.count(token)))

        # L2 Normalization
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [x / norm for x in vector]

        return vector

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


class SentenceTransformerEmbedder(BaseEmbeddingProvider):
    """Embedder using huggingface sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name, device=device)
            self._active = True
        except Exception as e:
            logger.warning(f"SentenceTransformer not available ({e}), falling back to LightweightFeatureEmbedder.")
            self._active = False
            self.fallback = LightweightFeatureEmbedder()

    def embed_text(self, text: str) -> List[float]:
        if not self._active:
            return self.fallback.embed_text(text)
        emb = self.model.encode(text, convert_to_numpy=True)
        return emb.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self._active:
            return self.fallback.embed_batch(texts)
        embs = self.model.encode(texts, convert_to_numpy=True)
        return embs.tolist()


def get_embedder() -> BaseEmbeddingProvider:
    """Factory creating appropriate embedder based on settings and available packages."""
    settings = get_settings()
    try:
        import sentence_transformers  # noqa: F401
        return SentenceTransformerEmbedder(
            model_name=settings.EMBEDDING_MODEL_NAME,
            device=settings.EMBEDDING_DEVICE,
        )
    except ImportError:
        return LightweightFeatureEmbedder()
