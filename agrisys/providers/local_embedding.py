"""Local / HuggingFace Embedding Provider.

Fulfills §2.4 Table 2.2: Provides multilingual text embeddings
(e.g., intfloat/multilingual-e5-large) with offline fallback.
"""

from typing import List, Optional
import hashlib
import numpy as np
from agrisys.providers.base import BaseEmbeddingProvider


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """Embedding provider using local HuggingFace or deterministic fallback."""

    def __init__(
        self,
        model_name: str = "intfloat/multilingual-e5-large",
        dimension: int = 1024,
    ) -> None:
        self.model_name = model_name
        self._dimension = dimension
        self._hf_model = None
        self._initialized = False

    def _init_hf(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            self._hf_model = SentenceTransformer(self.model_name)
        except Exception:
            self._hf_model = None

    async def embed_query(self, text: str) -> List[float]:
        """Embed a single query text."""
        res = await self.embed_documents([text])
        return res[0]

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple document texts."""
        self._init_hf()
        if self._hf_model is not None:
            vectors = self._hf_model.encode(texts, normalize_embeddings=True)
            return vectors.tolist()  # type: ignore

        # Resilient offline deterministic pseudo-semantic embedding for unit tests and offline dev
        results: List[List[float]] = []
        for text in texts:
            vec = self._hash_vector(text, self._dimension)
            results.append(vec)
        return results

    def _hash_vector(self, text: str, dim: int) -> List[float]:
        """Generate a normalized deterministic vector for text."""
        # Split into tokens to capture vocabulary overlap in fallback mode
        tokens = text.lower().split()
        arr = np.zeros(dim, dtype=np.float32)
        if not tokens:
            arr[0] = 1.0
            return arr.tolist()

        for token in tokens:
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            val = (h >> 16) % 1000 / 1000.0 - 0.5
            arr[idx] += float(val)

        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        else:
            arr[0] = 1.0
        return arr.tolist()

    @property
    def dimension(self) -> int:
        return self._dimension
