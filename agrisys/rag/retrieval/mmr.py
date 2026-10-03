"""MMR (Maximal Marginal Relevance) Diversity Filter & Metadata Booster.

Fulfills §10.2:
- Removes near-duplicate chunks while ensuring source diversity
- Boosts chunks matching query metadata (crop + state + domain)
"""

from typing import Dict, List, Optional
import numpy as np
from agrisys.rag.retrieval.models import ScoredChunk


class MMRDiversityFilter:
    """Filters chunks to maximize relevance while penalizing mutual redundancy."""

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        a = np.array(v1, dtype=np.float32)
        b = np.array(v2, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    @classmethod
    def filter(
        cls,
        query_vector: List[float],
        candidates: List[ScoredChunk],
        top_k: int = 5,
        lambda_mult: float = 0.7,
    ) -> List[ScoredChunk]:
        """Apply MMR selection algorithm."""
        if not candidates or len(candidates) <= top_k:
            return candidates

        # If candidates lack vectors, compute fallback text Jaccard similarity
        has_vectors = all(c.vector is not None for c in candidates)

        selected: List[ScoredChunk] = []
        remaining = candidates.copy()

        while len(selected) < top_k and remaining:
            best_idx = -1
            best_mmr_score = -float("inf")

            for i, cand in enumerate(remaining):
                if has_vectors and cand.vector and query_vector:
                    sim_to_query = cls.cosine_similarity(cand.vector, query_vector)
                else:
                    sim_to_query = cand.score

                # Maximum similarity to already selected chunks
                if not selected:
                    max_sim_to_selected = 0.0
                else:
                    if has_vectors and cand.vector:
                        sims = [cls.cosine_similarity(cand.vector, s.vector) for s in selected if s.vector]
                        max_sim_to_selected = max(sims) if sims else 0.0
                    else:
                        cand_words = set(cand.text.lower().split())
                        sims = [
                            len(cand_words.intersection(set(s.text.lower().split())))
                            / max(len(cand_words.union(set(s.text.lower().split()))), 1)
                            for s in selected
                        ]
                        max_sim_to_selected = max(sims) if sims else 0.0

                mmr_score = lambda_mult * sim_to_query - (1.0 - lambda_mult) * max_sim_to_selected

                # Minor bonus for source diversity
                sources_selected = {s.metadata.get("source") for s in selected if s.metadata}
                cand_source = cand.metadata.get("source")
                if cand_source and cand_source not in sources_selected:
                    mmr_score += 0.05

                if mmr_score > best_mmr_score:
                    best_mmr_score = mmr_score
                    best_idx = i

            if best_idx != -1:
                selected.append(remaining.pop(best_idx))
            else:
                break

        return selected


class MetadataBooster:
    """Boosts chunk relevance scores matching detected query metadata."""

    @staticmethod
    def boost(
        chunks: List[ScoredChunk],
        query_metadata: Dict[str, Optional[str]],
        boost_factor: float = 0.15,
    ) -> List[ScoredChunk]:
        """Add bonus score if chunk crop, state, or domain matches."""
        target_crop = query_metadata.get("crop")
        target_state = query_metadata.get("state")
        target_domain = query_metadata.get("domain")

        for c in chunks:
            meta = c.metadata or {}
            boost = 0.0
            if target_crop and meta.get("crop") and target_crop.lower() == meta["crop"].lower():
                boost += boost_factor
            if target_state and meta.get("state") and target_state.lower() == meta["state"].lower():
                boost += boost_factor
            if target_domain and meta.get("domain") and target_domain.lower() == meta["domain"].lower():
                boost += boost_factor
            c.score += boost

        chunks.sort(key=lambda x: x.score, reverse=True)
        return chunks
