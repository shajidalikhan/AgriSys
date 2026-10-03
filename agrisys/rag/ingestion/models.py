"""Data models for RAG Ingestion Pipeline.

Fulfills §10.1: Structured representation for source documents,
chunks, and ICAR/FAO metadata tags.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """Metadata tags associated with every indexed knowledge chunk."""
    source: str = Field(
        default="icar",
        description="Source authority: icar | fao | kcc | agmarknet | cgiar | custom"
    )
    crop: Optional[str] = Field(
        default=None,
        description="Target crop (e.g. wheat, rice, tomato, mustard)"
    )
    state: Optional[str] = Field(
        default=None,
        description="Geographic region/state in India (e.g. UP, Maharashtra, Punjab)"
    )
    domain: str = Field(
        default="general",
        description="Agricultural domain: disease | nutrition | market | weather | general"
    )
    language: str = Field(
        default="en",
        description="Language code: hi | en"
    )
    date_indexed: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp of when the chunk was indexed"
    )
    doc_id: Optional[str] = Field(default=None)
    chunk_index: int = Field(default=0)
    extra: Dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    """Raw loaded document representation."""
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source_path: Optional[str] = None


class Chunk(BaseModel):
    """Chunked document segment ready for embedding and indexing."""
    id: str
    text: str
    metadata: ChunkMetadata
    vector: Optional[List[float]] = None
