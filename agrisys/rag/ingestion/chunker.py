"""Semantic Chunker for RAG Ingestion Pipeline.

Fulfills §10.1:
- chunk_size: 512 tokens
- chunk_overlap: 128 tokens
- respects paragraph and sentence boundaries
"""

from typing import List
import re
from agrisys.rag.ingestion.models import Document


class SemanticChunker:
    """Chunks documents into overlapping segments respecting semantic boundaries."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 128,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, document: Document) -> List[str]:
        """Split a document into coherent chunks."""
        text = document.content.strip()
        if not text:
            return []

        # Split into paragraphs first
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if not paragraphs:
            paragraphs = [text]

        # Break long paragraphs into sentences if needed
        units: List[str] = []
        for para in paragraphs:
            # Estimate word/token count (~1 token ~ 0.75 words, so 512 tokens ~ 384 words)
            words = para.split()
            if len(words) > int(self.chunk_size * 0.75):
                sentences = re.split(r"(?<=[.!?।])\s+", para)
                units.extend([s.strip() for s in sentences if s.strip()])
            else:
                units.append(para)

        # Assemble chunks with overlap
        chunks: List[str] = []
        current_chunk_words: List[str] = []
        target_words = int(self.chunk_size * 0.75)
        overlap_words = int(self.chunk_overlap * 0.75)

        for unit in units:
            unit_words = unit.split()
            if len(current_chunk_words) + len(unit_words) <= target_words:
                current_chunk_words.extend(unit_words)
            else:
                if current_chunk_words:
                    chunks.append(" ".join(current_chunk_words))
                    # Retain trailing overlap
                    current_chunk_words = current_chunk_words[-overlap_words:] + unit_words
                else:
                    # Single unit exceeds chunk size, split by words
                    chunks.append(" ".join(unit_words[:target_words]))
                    current_chunk_words = unit_words[target_words - overlap_words:]

        if current_chunk_words:
            chunks.append(" ".join(current_chunk_words))

        return chunks
