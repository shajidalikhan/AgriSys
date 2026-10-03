"""RAG Infrastructure Package.

Exports ingestion, retrieval, and hallucination guard modules.
"""

from agrisys.rag.ingestion import (
    Document,
    Chunk,
    ChunkMetadata,
    DocumentLoader,
    SemanticChunker,
    MetadataTagger,
    QdrantUpserter,
    IngestionPipeline,
)
from agrisys.rag.retrieval import (
    ScoredChunk,
    HyDEExpander,
    BM25Retriever,
    ReciprocalRankFusion,
    CrossEncoderReranker,
    MMRDiversityFilter,
    MetadataBooster,
    RetrievalPipeline,
)
from agrisys.rag.guard import HallucinationGuard, HallucinationVerdict

__all__ = [
    "Document",
    "Chunk",
    "ChunkMetadata",
    "DocumentLoader",
    "SemanticChunker",
    "MetadataTagger",
    "QdrantUpserter",
    "IngestionPipeline",
    "ScoredChunk",
    "HyDEExpander",
    "BM25Retriever",
    "ReciprocalRankFusion",
    "CrossEncoderReranker",
    "MMRDiversityFilter",
    "MetadataBooster",
    "RetrievalPipeline",
    "HallucinationGuard",
    "HallucinationVerdict",
]
