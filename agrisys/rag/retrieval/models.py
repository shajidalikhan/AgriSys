"""Data models for RAG Retrieval Pipeline."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ScoredChunk(BaseModel):
    """Retrieved chunk annotated with relevance score and metadata."""
    id: str
    text: str
    score: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    vector: Optional[List[float]] = None
