"""Seed Agricultural Knowledge Base into Qdrant Vector Store.

Reads curated ICAR, FAO, and Agmarknet packages of practices from
data/processed/icar_fao_knowledge_seed.json and indexes them
via IngestionPipeline.
"""

import asyncio
import json
import logging
from pathlib import Path
from agrisys.config import load_rag_config
from agrisys.providers.factory import get_embedding_provider
from agrisys.rag.ingestion import IngestionPipeline, Document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agrisys.seed")


async def seed_knowledge_base(json_path: str = "data/processed/icar_fao_knowledge_seed.json") -> int:
    path = Path(json_path)
    if not path.exists():
        logger.error("Seed file not found: %s", json_path)
        return 0

    with open(path, "r", encoding="utf-8") as f:
        items = json.load(f)

    rag_cfg = load_rag_config()
    embed_provider = get_embedding_provider("local", dimension=1024)

    pipeline = IngestionPipeline(
        embedding_provider=embed_provider,
        chunk_size=rag_cfg.ingestion.chunk_size_tokens,
        chunk_overlap=rag_cfg.ingestion.chunk_overlap_tokens,
        collection_name=rag_cfg.vector_store.collection_name,
    )

    total_chunks = 0
    for item in items:
        doc = Document(
            content=item["content"],
            metadata={
                "title": item.get("title", ""),
                "crop": item.get("crop"),
                "state": item.get("state"),
                "domain": item.get("domain", "general"),
                "source": item.get("source", "icar"),
                "language": item.get("language", "en"),
            },
        )
        count = await pipeline.ingest_document(doc)
        total_chunks += count
        logger.info("Indexed '%s': %d chunk(s)", item.get("title", "Doc"), count)

    logger.info("Successfully populated vector database with %d chunks.", total_chunks)
    return total_chunks


if __name__ == "__main__":
    asyncio.run(seed_knowledge_base())
