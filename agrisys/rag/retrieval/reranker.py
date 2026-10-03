"""Cross-Encoder Reranker for Candidate Passages.

Fulfills §10.2: Reranks top-20 merged candidates using a cross-encoder model
(e.g., cross-encoder/ms-marco-MiniLM-L-6-v2) or semantic alignment fallback.
"""

from typing import List, Optional
import numpy as np
from agrisys.rag.retrieval.models import ScoredChunk


class CrossEncoderReranker:
    """Reranks candidate chunks based on full query-passage cross-attention."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self.model_name = model_name
        self._model = None
        self._initialized = False

    def _init_model(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        try:
            from sentence_transformers import CrossEncoder  # type: ignore
            self._model = CrossEncoder(self.model_name)
        except Exception:
            self._model = None

    def rerank(self, query: str, candidates: List[ScoredChunk], top_k: int = 5) -> List[ScoredChunk]:
        """Score each (query, chunk.text) pair and return the top_k."""
        if not candidates:
            return []

        self._init_model()

        if self._model is not None:
            pairs = [(query, c.text) for c in candidates]
            scores = self._model.predict(pairs)
            for i, score in enumerate(scores):
                candidates[i].score = float(score)
            candidates.sort(key=lambda x: x.score, reverse=True)
            return candidates[:top_k]

        # Resilient heuristic semantic alignment reranker (term coverage + length normalization)
        query_words = set(query.lower().split())
        for c in candidates:
            chunk_words = set(c.text.lower().split())
            overlap = len(query_words.intersection(chunk_words))
            ratio = overlap / max(len(query_words), 1)
            # Combine hybrid RRF score with lexical precision
            c.score = float(c.score * 0.5 + ratio * 0.5)

        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates[:top_k]
