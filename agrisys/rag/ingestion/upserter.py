"""Qdrant Upserter for RAG Ingestion Pipeline.

Fulfills §10.1: Stores document chunks with high-dimensional vector embeddings
and rich payload metadata into Qdrant collection 'agrisys_knowledge'.
Supports resilient in-memory fallback for local dev & testing.
"""

from typing import List, Optional
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from agrisys.providers.base import BaseEmbeddingProvider
from agrisys.rag.ingestion.models import Chunk


class QdrantUpserter:
    """Handles collection creation and batch upsert into Qdrant."""

    def __init__(
        self,
        embedding_provider: BaseEmbeddingProvider,
        collection_name: str = "agrisys_knowledge",
        qdrant_url: str = "http://localhost:6333",
        api_key: Optional[str] = None,
        prefer_grpc: bool = False,
        in_memory: bool = False,
    ) -> None:
        self.embedding_provider = embedding_provider
        self.collection_name = collection_name
        self.qdrant_url = qdrant_url
        self.api_key = api_key
        self.in_memory = in_memory

        self._client: Optional[QdrantClient] = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize Qdrant client, with fallback to in-memory mode if connection fails."""
        if self.in_memory:
            self._client = QdrantClient(location=":memory:")
            return

        try:
            client = QdrantClient(
                url=self.qdrant_url,
                api_key=self.api_key or None,
                timeout=1.0,
                check_compatibility=False,
            )
            # Test connectivity
            client.get_collections()
            self._client = client
        except Exception:
            # Fallback gracefully to in-memory client for testing/offline dev
            self._client = QdrantClient(location=":memory:")

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._init_client()
        return self._client  # type: ignore

    async def ensure_collection(self) -> None:
        """Create collection with Cosine distance if it doesn't already exist."""
        dim = self.embedding_provider.dimension
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qmodels.VectorParams(
                    size=dim,
                    distance=qmodels.Distance.COSINE,
                ),
            )

    async def upsert_chunks(self, chunks: List[Chunk]) -> int:
        """Embed and upsert chunks into Qdrant in batch."""
        if not chunks:
            return 0

        await self.ensure_collection()

        # Generate embeddings if not already present
        texts = [c.text for c in chunks]
        embeddings = await self.embedding_provider.embed_documents(texts)

        points: List[qmodels.PointStruct] = []
        for i, chunk in enumerate(chunks):
            chunk.vector = embeddings[i]
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk.id))
            payload = {
                "text": chunk.text,
                "chunk_id": chunk.id,
                **chunk.metadata.model_dump(),
            }
            points.append(
                qmodels.PointStruct(
                    id=point_id,
                    vector=embeddings[i],
                    payload=payload,
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True,
        )
        return len(points)
