"""End-to-End RAG Retrieval Pipeline.

Fulfills §10.2:
HyDE -> Hybrid (BM25 + Dense Qdrant) -> RRF -> Cross-Encoder -> MMR -> Metadata Boost -> Top-5
"""

from typing import Dict, List, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from agrisys.providers.base import BaseLLMProvider, BaseEmbeddingProvider
from agrisys.rag.ingestion.tagger import MetadataTagger
from agrisys.rag.retrieval.models import ScoredChunk
from agrisys.rag.retrieval.hyde import HyDEExpander
from agrisys.rag.retrieval.bm25 import BM25Retriever
from agrisys.rag.retrieval.rrf import ReciprocalRankFusion
from agrisys.rag.retrieval.reranker import CrossEncoderReranker
from agrisys.rag.retrieval.mmr import MMRDiversityFilter, MetadataBooster


class RetrievalPipeline:
    """Orchestrates multi-stage advanced retrieval pipeline."""

    def __init__(
        self,
        embedding_provider: BaseEmbeddingProvider,
        llm_provider: Optional[BaseLLMProvider] = None,
        qdrant_client: Optional[QdrantClient] = None,
        collection_name: str = "agrisys_knowledge",
        hyde_enabled: bool = True,
        top_k_bm25: int = 20,
        top_k_dense: int = 20,
        top_k_cross: int = 10,
        top_k_final: int = 5,
        mmr_lambda: float = 0.7,
        metadata_boost: float = 0.15,
    ) -> None:
        self.embedding_provider = embedding_provider
        self.llm_provider = llm_provider
        self.collection_name = collection_name
        self.hyde_enabled = hyde_enabled
        self.top_k_bm25 = top_k_bm25
        self.top_k_dense = top_k_dense
        self.top_k_cross = top_k_cross
        self.top_k_final = top_k_final
        self.mmr_lambda = mmr_lambda
        self.metadata_boost = metadata_boost

        self.hyde = HyDEExpander(llm_provider) if hyde_enabled else None
        self.bm25 = BM25Retriever()
        self.reranker = CrossEncoderReranker()

        self._client = qdrant_client

    def set_qdrant_client(self, client: QdrantClient) -> None:
        """Set or update Qdrant client."""
        self._client = client

    def update_bm25_corpus(self, chunks: List[ScoredChunk]) -> None:
        """Keep BM25 index synchronized with indexed corpus."""
        self.bm25.set_corpus(chunks)

    async def retrieve(
        self,
        query: str,
        filter_metadata: Optional[Dict[str, Optional[str]]] = None,
    ) -> List[ScoredChunk]:
        """Execute full hybrid retrieval pipeline.

        Args:
            query: Farmer question or problem statement.
            filter_metadata: Optional explicit or detected metadata (crop, state, domain).

        Returns:
            Top scored chunks ready for LLM context window.
        """
        # Auto-detect metadata from query if not explicitly passed
        if not filter_metadata:
            detected = MetadataTagger.tag(query)
            filter_metadata = {
                "crop": detected.crop,
                "state": detected.state,
                "domain": detected.domain if detected.domain != "general" else None,
            }

        # Step 1: HyDE Query Expansion
        search_query = query
        if self.hyde and self.hyde_enabled:
            search_query = await self.hyde.expand(query)

        # Step 2: Dense Semantic Retrieval from Qdrant
        query_vector = await self.embedding_provider.embed_query(search_query)
        dense_candidates = await self._dense_search(query_vector, top_k=self.top_k_dense)

        # Step 3: BM25 Sparse Retrieval
        # If corpus not explicitly primed in memory, prime from dense candidate pool
        if not self.bm25.chunks and dense_candidates:
            self.bm25.set_corpus(dense_candidates)
        bm25_candidates = self.bm25.retrieve(query, top_k=self.top_k_bm25)

        # Step 4: Hybrid RRF Fusion
        merged_candidates = ReciprocalRankFusion.fuse(
            rankings=[dense_candidates, bm25_candidates],
            top_k=max(self.top_k_dense, self.top_k_bm25),
        )

        if not merged_candidates:
            return []

        # Step 5: Cross-Encoder Reranker
        reranked = self.reranker.rerank(query, merged_candidates, top_k=self.top_k_cross)

        # Step 6: MMR Diversity Filtering
        diverse = MMRDiversityFilter.filter(
            query_vector=query_vector,
            candidates=reranked,
            top_k=self.top_k_final,
            lambda_mult=self.mmr_lambda,
        )

        # Step 7: Metadata Filter Boosting
        final_chunks = MetadataBooster.boost(
            chunks=diverse,
            query_metadata=filter_metadata,
            boost_factor=self.metadata_boost,
        )

        return final_chunks[:self.top_k_final]

    async def _dense_search(self, vector: List[float], top_k: int = 20) -> List[ScoredChunk]:
        """Query Qdrant collection for nearest neighbors."""
        if not self._client:
            return []

        try:
            collections = self._client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                return []

            if hasattr(self._client, "query_points"):
                response = self._client.query_points(
                    collection_name=self.collection_name,
                    query=vector,
                    limit=top_k,
                    with_payload=True,
                    with_vectors=True,
                )
                results = response.points
            else:
                results = self._client.search(
                    collection_name=self.collection_name,
                    query_vector=vector,
                    limit=top_k,
                    with_payload=True,
                    with_vectors=True,
                )

            chunks: List[ScoredChunk] = []
            for r in results:
                payload = r.payload or {}
                vector_val = r.vector if isinstance(r.vector, list) else None
                chunks.append(
                    ScoredChunk(
                        id=str(r.id),
                        text=payload.get("text", ""),
                        score=float(r.score),
                        metadata=payload,
                        vector=vector_val,
                    )
                )
            return chunks
        except Exception:
            return []
