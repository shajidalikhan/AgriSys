"""RAG Ingestion Pipeline Coordinator.

Orchestrates:
DocumentLoader -> SemanticChunker -> MetadataTagger -> QdrantUpserter
"""

from pathlib import Path
from typing import Dict, List, Optional
import hashlib
from agrisys.providers.base import BaseEmbeddingProvider
from agrisys.rag.ingestion.models import Chunk, Document
from agrisys.rag.ingestion.loaders import DocumentLoader
from agrisys.rag.ingestion.chunker import SemanticChunker
from agrisys.rag.ingestion.tagger import MetadataTagger
from agrisys.rag.ingestion.upserter import QdrantUpserter


class IngestionPipeline:
    """End-to-end ingestion pipeline."""

    def __init__(
        self,
        embedding_provider: BaseEmbeddingProvider,
        upserter: Optional[QdrantUpserter] = None,
        chunk_size: int = 512,
        chunk_overlap: int = 128,
        collection_name: str = "agrisys_knowledge",
    ) -> None:
        self.embedding_provider = embedding_provider
        self.chunker = SemanticChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.upserter = upserter or QdrantUpserter(
            embedding_provider=embedding_provider,
            collection_name=collection_name,
        )

    async def ingest_file(
        self,
        file_path: str | Path,
        source_name: Optional[str] = None,
        base_metadata: Optional[Dict[str, str]] = None,
    ) -> int:
        """Load, chunk, tag, and upsert a file into the knowledge base."""
        docs = DocumentLoader.load(file_path, source_name=source_name)
        total_chunks = 0
        for doc in docs:
            num = await self.ingest_document(doc, base_metadata=base_metadata)
            total_chunks += num
        return total_chunks

    async def ingest_document(
        self,
        document: Document,
        base_metadata: Optional[Dict[str, str]] = None,
    ) -> int:
        """Process a single loaded document into indexed chunks."""
        text_chunks = self.chunker.chunk_document(document)
        if not text_chunks:
            return 0

        combined_meta = {**document.metadata, **(base_metadata or {})}
        doc_hash = hashlib.md5(document.content.encode("utf-8")).hexdigest()[:8]

        chunks_to_index: List[Chunk] = []
        for i, text in enumerate(text_chunks):
            meta = MetadataTagger.tag(
                text=text,
                base_metadata=combined_meta,
                chunk_index=i,
                doc_id=doc_hash,
            )
            chunk_id = f"{doc_hash}_{i}"
            chunks_to_index.append(
                Chunk(
                    id=chunk_id,
                    text=text,
                    metadata=meta,
                )
            )

        return await self.upserter.upsert_chunks(chunks_to_index)
