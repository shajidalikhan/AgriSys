"""Reciprocal Rank Fusion (RRF) for Hybrid Retrieval.

Fulfills §10.2: Merges BM25 sparse rankings and Qdrant dense semantic rankings
using the formula: score = sum(1 / (k + rank_i)) with k=60.
"""

from typing import Dict, List
from agrisys.rag.retrieval.models import ScoredChunk


class ReciprocalRankFusion:
    """Merges multiple ranked lists of chunks."""

    @staticmethod
    def fuse(
        rankings: List[List[ScoredChunk]],
        k: int = 60,
        top_k: int = 20,
    ) -> List[ScoredChunk]:
        """Merge ranked result lists into a single consolidated ranking."""
        chunk_map: Dict[str, ScoredChunk] = {}
        rrf_scores: Dict[str, float] = {}

        for rank_list in rankings:
            for rank, chunk in enumerate(rank_list):
                cid = chunk.id
                if cid not in chunk_map:
                    chunk_map[cid] = chunk
                    rrf_scores[cid] = 0.0

                # 0-indexed rank -> rank + 1
                rrf_scores[cid] += 1.0 / (k + (rank + 1))

        # Sort by merged RRF score
        sorted_cids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

        results: List[ScoredChunk] = []
        for cid in sorted_cids[:top_k]:
            original = chunk_map[cid]
            results.append(
                ScoredChunk(
                    id=original.id,
                    text=original.text,
                    score=rrf_scores[cid],
                    metadata=original.metadata,
                    vector=original.vector,
                )
            )
        return results
