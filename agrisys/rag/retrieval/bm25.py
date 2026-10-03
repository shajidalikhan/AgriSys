"""BM25 Sparse Keyword Retriever.

Fulfills §10.2: Sparse keyword retrieval matching agricultural terminology
(e.g., specific pesticide names, disease symptoms, or mandi names).
"""

from typing import List, Optional
import re
from rank_bm25 import BM25Okapi
from agrisys.rag.retrieval.models import ScoredChunk


class BM25Retriever:
    """In-memory BM25 index over indexed chunks."""

    def __init__(self, chunks: Optional[List[ScoredChunk]] = None) -> None:
        self.chunks: List[ScoredChunk] = chunks or []
        self._bm25: Optional[BM25Okapi] = None
        if self.chunks:
            self._build_index()

    def set_corpus(self, chunks: List[ScoredChunk]) -> None:
        """Update the corpus and rebuild index."""
        self.chunks = chunks
        self._build_index()

    def _tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r"\b\w+\b", text)]

    def _build_index(self) -> None:
        tokenized_corpus = [self._tokenize(c.text) for c in self.chunks]
        if tokenized_corpus:
            self._bm25 = BM25Okapi(tokenized_corpus)

    def retrieve(self, query: str, top_k: int = 20) -> List[ScoredChunk]:
        """Score all chunks against query and return top_k candidates."""
        if not self._bm25 or not self.chunks:
            return []

        tokenized_query = self._tokenize(query)
        if not tokenized_query:
            return self.chunks[:top_k]

        scores = self._bm25.get_scores(tokenized_query)
        scored_pairs = list(zip(self.chunks, scores))
        scored_pairs.sort(key=lambda x: x[1], reverse=True)

        results: List[ScoredChunk] = []
        for chunk, score in scored_pairs[:top_k]:
            results.append(
                ScoredChunk(
                    id=chunk.id,
                    text=chunk.text,
                    score=float(score),
                    metadata=chunk.metadata,
                    vector=chunk.vector,
                )
            )
        return results
