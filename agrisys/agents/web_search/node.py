"""LangGraph state node for the Web Search Specialist Agent."""

from __future__ import annotations
import logging
from typing import Any
from agrisys.agents.web_search.agent import WebSearchAgent

logger = logging.getLogger(__name__)


async def web_search_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph state node executing the Web Search Agent."""
    query = state.get("query", "")
    crop = state.get("active_crop")
    language = state.get("language", "en")
    location = state.get("location") or {}

    loc_str = location.get("district") or location.get("state") or location.get("name") or None

    agent = WebSearchAgent()
    report = await agent.search_and_synthesize(
        query=query,
        crop=crop,
        location=loc_str,
        language=language,
    )

    # Convert top search results into pseudo RAG chunks for grounding and citation downstream
    chunks = [
        {
            "content": f"{item.title}: {item.snippet}",
            "source": item.url,
            "score": 0.90,
            "metadata": {"title": item.title, "url": item.url, "source": "web_search"},
        }
        for item in report.results[:4]
    ]

    return {
        "web_search_data": report.model_dump(),
        "citations": report.citations,
        "rag_chunks": chunks,
        "agent_results": [
            {
                "agent": "web_search_agent",
                "query": report.query,
                "summary": report.summary,
                "source_count": len(report.results),
                "top_sources": [r.url for r in report.results[:3]],
            }
        ],
    }
