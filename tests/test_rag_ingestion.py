"""Unit tests for RAG Ingestion Pipeline (§10.1).

Tests loaders, semantic chunker, metadata tagger, and Qdrant upserter.
"""

import pytest
from pathlib import Path
from agrisys.providers.local_embedding import LocalEmbeddingProvider
from agrisys.rag.ingestion.models import Document, ChunkMetadata
from agrisys.rag.ingestion.loaders import DocumentLoader
from agrisys.rag.ingestion.chunker import SemanticChunker
from agrisys.rag.ingestion.tagger import MetadataTagger
from agrisys.rag.ingestion.upserter import QdrantUpserter
from agrisys.rag.ingestion.pipeline import IngestionPipeline


def test_metadata_tagger_detection():
    """Verify metadata tagger automatically detects crop, state, domain, and language."""
    # English tomato disease text in UP
    text_en = "Early blight in tomato crops in Uttar Pradesh causes concentric rings. Spray Mancozeb fungicide."
    meta = MetadataTagger.tag(text_en, base_metadata={"source": "icar"})

    assert meta.source == "icar"
    assert meta.crop == "tomato"
    assert meta.state == "UP"
    assert meta.domain == "disease"
    assert meta.language == "en"

    # Hindi text detection
    text_hi = "टमाटर की फसल में अगेती झुलसा रोग के लक्षण दिखाई देने पर कवकनाशी का छिड़काव करें।"
    meta_hi = MetadataTagger.tag(text_hi)
    assert meta_hi.language == "hi"
    assert meta_hi.domain == "disease"


def test_semantic_chunker():
    """Verify semantic chunker splits text while respecting boundary constraints."""
    chunker = SemanticChunker(chunk_size=30, chunk_overlap=10)
    content = (
        "Paragraph one discusses wheat rust in Punjab. It causes orange pustules on leaves.\n\n"
        "Paragraph two discusses soil nutrition and NPK fertilizer dosage for paddy crops in Haryana.\n\n"
        "Paragraph three covers mandi price trends in UP."
    )
    doc = Document(content=content)
    chunks = chunker.chunk_document(doc)

    assert len(chunks) >= 2
    for c in chunks:
        assert len(c.split()) > 0


def test_document_loader_txt(tmp_path: Path):
    """Test plain text loading."""
    p = tmp_path / "sample_advisory.txt"
    p.write_text("ICAR advisory for rice blast disease management in Bihar.", encoding="utf-8")

    docs = DocumentLoader.load(p, source_name="icar")
    assert len(docs) == 1
    assert "rice blast" in docs[0].content
    assert docs[0].metadata["source"] == "icar"


def test_document_loader_csv(tmp_path: Path):
    """Test CSV tabular document loading."""
    p = tmp_path / "mandi_prices.csv"
    p.write_text("Commodity,Mandi,Price\nWheat,Lucknow,2275\nTomato,Agra,1800\n", encoding="utf-8")

    docs = DocumentLoader.load(p, source_name="agmarknet")
    assert len(docs) == 2
    assert "Wheat" in docs[0].content
    assert docs[0].metadata["source"] == "agmarknet"


@pytest.mark.asyncio
async def test_qdrant_upserter_and_pipeline(tmp_path: Path):
    """Test full ingestion pipeline with in-memory Qdrant client."""
    p = tmp_path / "wheat_guide.txt"
    p.write_text(
        "Yellow rust in wheat is prevalent in Punjab and Haryana during cool humid weather. "
        "Apply Propiconazole 25 EC at 0.1% to control fungal spread.",
        encoding="utf-8",
    )

    embed_provider = LocalEmbeddingProvider(dimension=256)
    upserter = QdrantUpserter(
        embedding_provider=embed_provider,
        collection_name="test_agrisys_knowledge",
        in_memory=True,
    )

    pipeline = IngestionPipeline(
        embedding_provider=embed_provider,
        upserter=upserter,
        collection_name="test_agrisys_knowledge",
    )

    count = await pipeline.ingest_file(p, source_name="icar")
    assert count >= 1

    # Verify Qdrant points count
    points_count = upserter.client.count(collection_name="test_agrisys_knowledge").count
    assert points_count == count
