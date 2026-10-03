"""Web Search Specialist Agent for AgriSys Multi-Agent Ecosystem."""

from __future__ import annotations
import logging
from typing import Any, List
from agrisys.agents.web_search.client import WebSearchClient
from agrisys.agents.web_search.models import SearchResultItem, WebSearchQuery, WebSearchReport
from agrisys.providers.base import BaseLLMProvider
from agrisys.providers.factory import get_llm_provider

logger = logging.getLogger(__name__)

PRIORITY_DOMAINS = [
    "gov.in",
    "nic.in",
    "icar.org.in",
    "farmer.gov.in",
    "pmkisan.gov.in",
    "agricoop.nic.in",
    "enam.gov.in",
]


class WebSearchAgent:
    """Specialist agent responsible for retrieving and synthesizing live web information."""

    def __init__(
        self,
        client: WebSearchClient | None = None,
        llm_provider: BaseLLMProvider | None = None,
    ):
        self.client = client or WebSearchClient()
        self.llm_provider = llm_provider

    def _get_llm(self) -> BaseLLMProvider | None:
        if self.llm_provider:
            return self.llm_provider
        try:
            return get_llm_provider()
        except Exception:
            return None

    def formulate_query(self, user_query: str, crop: str | None = None, location: str | None = None) -> str:
        """Enriches the query with context if needed (e.g. adding India/agriculture terms)."""
        terms = [user_query.strip()]
        q_lower = user_query.lower()

        # If it's an agricultural query without geographic anchor, anchor to India
        if "india" not in q_lower and "state" not in q_lower:
            terms.append("India agriculture")

        if crop and crop.lower() not in q_lower:
            terms.append(crop)

        if location and location.lower() not in q_lower:
            terms.append(location)

        return " ".join(terms)

    async def search_and_synthesize(
        self,
        query: str,
        crop: str | None = None,
        location: str | None = None,
        language: str = "en",
        max_results: int = 5,
    ) -> WebSearchReport:
        """Executes targeted search and synthesizes actionable findings."""
        refined_query = self.formulate_query(query, crop=crop, location=location)

        search_req = WebSearchQuery(query=refined_query, max_results=max_results)
        results = await self.client.search(search_req)

        # Re-rank: boost priority domains (ICAR, gov.in, etc.)
        def _domain_score(item: SearchResultItem) -> int:
            return 2 if any(domain in item.url.lower() for domain in PRIORITY_DOMAINS) else 1

        ranked_results = sorted(results, key=_domain_score, reverse=True)

        citations: list[str] = []
        for item in ranked_results:
            citation_str = f"Web Source: [{item.title}]({item.url})"
            if citation_str not in citations:
                citations.append(citation_str)

        # Synthesize advisory
        llm = self._get_llm()
        summary = ""

        if ranked_results and llm:
            try:
                context_block = "\n\n".join(
                    [f"Title: {r.title}\nSource: {r.url}\nExcerpt: {r.snippet}" for r in ranked_results[:4]]
                )
                prompt = (
                    f"You are AgriSys Web Search Agent. Synthesize an agricultural advisory based on the latest web findings.\n"
                    f"User Query: {query}\n\n"
                    f"Web Findings:\n{context_block}\n\n"
                    f"Language: {language}\n"
                    f"Provide a concise, direct, factual summary citing relevant scheme names, guidelines, or portals."
                )
                summary = await llm.complete([{"role": "user", "content": prompt}])
            except Exception as err:
                logger.warning(f"LLM web search synthesis error: {err}")

        if not summary:
            # Fallback heuristic summary
            if ranked_results:
                bullet_points = [f"- **{r.title}**: {r.snippet}" for r in ranked_results[:3]]
                summary = "Latest web search findings:\n" + "\n".join(bullet_points)
            else:
                summary = f"No live web search results found for query: '{query}'. Please verify official agricultural portals."

        return WebSearchReport(
            query=refined_query,
            results=ranked_results,
            summary=summary,
            citations=citations,
            provider_used=self.client.provider,
        )
