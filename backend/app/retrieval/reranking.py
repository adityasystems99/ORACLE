"""Replaceable reranking interfaces for semantic search refinement."""

import abc
import math
import re
from typing import List
from ..schemas.rag import EvidencePassage


class BaseReranker(abc.ABC):
    """Abstract protocol for reranking retrieved evidence passages."""

    @abc.abstractmethod
    def rerank(
        self,
        query: str,
        passages: List[EvidencePassage],
        top_k: int = 5,
    ) -> List[EvidencePassage]:
        """Rerank passages against the user query."""
        pass


class PassThroughReranker(BaseReranker):
    """Identity reranker preserving vector similarity ranking order."""

    def rerank(
        self,
        query: str,
        passages: List[EvidencePassage],
        top_k: int = 5,
    ) -> List[EvidencePassage]:
        return passages[:top_k]


class HybridLexicalReranker(BaseReranker):
    """Combines dense semantic vector scores with exact term and technical entity scoring.

    Substantially improves precision for queries referencing specific CVE identifiers,
    version numbers, parameter flags, and package names.
    """

    def __init__(self, semantic_weight: float = 0.65, lexical_weight: float = 0.35):
        self.semantic_weight = semantic_weight
        self.lexical_weight = lexical_weight

    def _extract_query_tokens(self, query: str) -> List[str]:
        # Extract alphanumeric words and technical tokens (e.g. "0.111.0", "CVE-2024-1234")
        return [t.lower() for t in re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", query)]

    def _calculate_lexical_score(self, query_tokens: List[str], text: str) -> float:
        if not query_tokens:
            return 0.0

        lower_text = text.lower()
        matched = 0
        bonus = 0.0

        for token in query_tokens:
            # Word boundary check
            count = len(re.findall(re.escape(token), lower_text))
            if count > 0:
                matched += 1
                # Diminishing returns on multiple occurrences
                bonus += math.log(1 + count)

            # Extra weight for version numbers and CVE identifiers
            if re.match(r"(cve-\d+|\d+\.\d+)", token):
                if token in lower_text:
                    bonus += 1.5

        token_coverage = matched / len(query_tokens)
        raw_score = (token_coverage * 0.7) + (min(bonus, 3.0) / 3.0 * 0.3)
        return min(raw_score, 1.0)

    def rerank(
        self,
        query: str,
        passages: List[EvidencePassage],
        top_k: int = 5,
    ) -> List[EvidencePassage]:
        if not passages:
            return []

        tokens = self._extract_query_tokens(query)
        reranked_items: List[EvidencePassage] = []

        for p in passages:
            lexical_score = self._calculate_lexical_score(tokens, p.content)
            composite_score = (p.score * self.semantic_weight) + (lexical_score * self.lexical_weight)
            normalized_score = round(min(max(composite_score, 0.0), 1.0), 4)

            # Create updated passage with composite score and rerank metadata
            updated = EvidencePassage(
                chunk_id=p.chunk_id,
                document_id=p.document_id,
                content=p.content,
                source_url=p.source_url,
                publisher=p.publisher,
                publication_timestamp=p.publication_timestamp,
                retrieval_timestamp=p.retrieval_timestamp,
                document_version=p.document_version,
                content_hash=p.content_hash,
                score=normalized_score,
                metadata={
                    **p.metadata,
                    "original_vector_score": p.score,
                    "lexical_match_score": round(lexical_score, 4),
                },
            )
            reranked_items.append(updated)

        reranked_items.sort(key=lambda x: x.score, reverse=True)
        return reranked_items[:top_k]
