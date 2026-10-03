"""Pydantic models for Web Search Agent in AgriSys."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    """Represents an individual search hit."""
    title: str = Field(description="Title of the web page or document")
    url: str = Field(description="Direct URL to source")
    snippet: str = Field(description="Text snippet / snippet summary from search engine")
    source: str = Field(default="duckduckgo", description="Provider identifier (duckduckgo, tavily)")


class WebSearchQuery(BaseModel):
    """Parameters for executing a web search query."""
    query: str = Field(description="Search terms submitted to provider")
    max_results: int = Field(default=5, ge=1, le=20)
    region: str = Field(default="in-en", description="Search region context")
    safesearch: str = Field(default="moderate", description="Safe search filter level")


class WebSearchReport(BaseModel):
    """Structured report returned by the WebSearchAgent."""
    query: str
    results: List[SearchResultItem] = Field(default_factory=list)
    summary: str = Field(default="", description="Aggregated summary or synthesis of results")
    citations: List[str] = Field(default_factory=list, description="Source URLs and titles")
    provider_used: str = Field(default="duckduckgo")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
