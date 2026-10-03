"""Unit tests for RAG Retrieval Pipeline (§10.2) and Hallucination Guard (§10.3).

Tests HyDE, BM25, RRF, Cross-Encoder, MMR, and Hallucination detection.
"""

import pytest
from agrisys.providers.base import BaseLLMProvider
from agrisys.providers.local_embedding import LocalEmbeddingProvider
from agrisys.rag.retrieval.models import ScoredChunk
from agrisys.rag.retrieval.hyde import HyDEExpander
from agrisys.rag.retrieval.bm25 import BM25Retriever
from agrisys.rag.retrieval.rrf import ReciprocalRankFusion
from agrisys.rag.retrieval.reranker import CrossEncoderReranker
from agrisys.rag.retrieval.mmr import MMRDiversityFilter, MetadataBooster
from agrisys.rag.retrieval.pipeline import RetrievalPipeline
from agrisys.rag.ingestion.upserter import QdrantUpserter
from agrisys.rag.ingestion.models import Chunk, ChunkMetadata
from agrisys.rag.guard import HallucinationGuard


class MockLLM(BaseLLMProvider):
    def __init__(self, response_text: str = "Hypothetical advisory text"):
        self.response_text = response_text

    async def complete(self, messages, **kwargs):
        return self.response_text

    async def stream(self, messages, **kwargs):
        yield self.response_text

    @property
    def supports_vision(self):
        return False

    @property
    def context_window(self):
        return 4096


@pytest.mark.asyncio
async def test_hyde_expansion():
    """Verify HyDE appends hypothetical passage to user query."""
    llm = MockLLM(response_text="Early blight in tomato is caused by Alternaria solani.")
    expander = HyDEExpander(llm)
    result = await expander.expand("How to treat tomato early blight?")

    assert "How to treat tomato early blight?" in result
    assert "Alternaria solani" in result


def test_bm25_retriever():
    """Test BM25 keyword matching."""
    chunks = [
        ScoredChunk(id="1", text="Early blight in tomato caused by fungal spores"),
        ScoredChunk(id="2", text="Fertilizer dose of Urea and DAP for wheat crops"),
        ScoredChunk(id="3", text="Mandi wholesale prices of potato in Agra"),
    ]
    bm25 = BM25Retriever(chunks)
    results = bm25.retrieve("tomato blight", top_k=1)

    assert len(results) == 1
    assert results[0].id == "1"


def test_reciprocal_rank_fusion():
    """Verify RRF merges sparse and dense rankings correctly."""
    dense_ranking = [
        ScoredChunk(id="doc_a", text="A"),
        ScoredChunk(id="doc_b", text="B"),
    ]
    bm25_ranking = [
        ScoredChunk(id="doc_b", text="B"),
        ScoredChunk(id="doc_c", text="C"),
    ]

    merged = ReciprocalRankFusion.fuse([dense_ranking, bm25_ranking], k=60, top_k=3)
    # doc_b appears in both rankings, so it should have the highest cumulative RRF score
    assert merged[0].id == "doc_b"


def test_metadata_booster():
    """Verify chunks matching crop/state receive score boost."""
    chunks = [
        ScoredChunk(id="1", text="Tomato care", score=0.5, metadata={"crop": "tomato", "state": "UP"}),
        ScoredChunk(id="2", text="Wheat care", score=0.6, metadata={"crop": "wheat", "state": "Punjab"}),
    ]

    boosted = MetadataBooster.boost(chunks, query_metadata={"crop": "tomato", "state": "UP"}, boost_factor=0.2)
    # Chunk 1 gets 0.5 + 0.2 + 0.2 = 0.9, beating Chunk 2's 0.6
    assert boosted[0].id == "1"


@pytest.mark.asyncio
async def test_retrieval_pipeline_end_to_end():
    """Verify complete retrieval pipeline with in-memory Qdrant store."""
    embed_provider = LocalEmbeddingProvider(dimension=256)
    upserter = QdrantUpserter(
        embedding_provider=embed_provider,
        collection_name="test_retrieval_knowledge",
        in_memory=True,
    )

    # Ingest test chunks
    test_chunks = [
        Chunk(
            id="c1",
            text="Tomato early blight is treated with Mancozeb 75 WP at 2g per liter water.",
            metadata=ChunkMetadata(source="icar", crop="tomato", state="UP", domain="disease"),
        ),
        Chunk(
            id="c2",
            text="Rice brown planthopper infestation can be controlled with Pymetrozine.",
            metadata=ChunkMetadata(source="icar", crop="rice", state="AP", domain="disease"),
        ),
        Chunk(
            id="c3",
            text="Wheat MSP for current rabi season is set at Rs 2275 per quintal.",
            metadata=ChunkMetadata(source="agmarknet", crop="wheat", state="UP", domain="market"),
        ),
    ]
    await upserter.upsert_chunks(test_chunks)

    pipeline = RetrievalPipeline(
        embedding_provider=embed_provider,
        llm_provider=None,
        qdrant_client=upserter.client,
        collection_name="test_retrieval_knowledge",
        hyde_enabled=False,
        top_k_final=2,
    )

    results = await pipeline.retrieve("treatment for early blight in tomato in UP")
    assert len(results) > 0
    assert results[0].metadata.get("crop") == "tomato"


@pytest.mark.asyncio
async def test_hallucination_guard_verdicts():
    """Verify hallucination guard passes grounded answers and escalates ungrounded ones."""
    guard = HallucinationGuard(llm_provider=None, threshold=0.70)

    # Grounded answer: terms exist in source
    source = ["Tomato early blight can be managed by spraying Mancozeb 75 WP at recommended dosage."]
    grounded_answer = "You should spray Mancozeb 75 WP to manage tomato early blight according to ICAR."
    v_pass = await guard.verify(grounded_answer, source)
    assert v_pass.score >= 0.70
    assert v_pass.verdict == "pass"

    # Fabricated answer: completely unrelated medical prescription
    fabricated_answer = "Take paracetamol antibiotic amoxicillin twice daily with warm milk."
    v_fail = await guard.verify(fabricated_answer, source)
    assert v_fail.score < 0.70
    assert v_fail.verdict == "escalate"
    assert len(v_fail.unsupported_claims) > 0
