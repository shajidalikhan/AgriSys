"""Asynchronous Web Search Client for AgriSys.

Supports DuckDuckGo and Tavily with automatic fallbacks and graceful error handling.
"""

from __future__ import annotations
import asyncio
import logging
from typing import Any, List
import httpx
from agrisys.agents.web_search.models import SearchResultItem, WebSearchQuery
from agrisys.config import load_providers_config

logger = logging.getLogger(__name__)


class WebSearchClient:
    """Multi-provider search client supporting DuckDuckGo and Tavily."""

    def __init__(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        timeout: int = 10,
    ):
        providers_cfg = load_providers_config()
        web_cfg = providers_cfg.web_search

        self.provider = provider or web_cfg.provider or "duckduckgo"
        self.api_key = api_key or web_cfg.api_key or ""
        self.timeout = timeout or web_cfg.timeout_seconds or 10

    async def search(self, query: WebSearchQuery | str) -> list[SearchResultItem]:
        """Execute web search across configured provider with fallback."""
        if isinstance(query, str):
            query = WebSearchQuery(query=query)

        results: list[SearchResultItem] = []

        # 1. Primary provider execution
        if self.provider.lower() == "tavily" and self.api_key:
            results = await self._search_tavily(query)
        elif self.provider.lower() == "duckduckgo":
            results = await self._search_duckduckgo(query)

        # 2. Fallback execution if primary yielded no results or error
        if not results:
            if self.provider.lower() != "duckduckgo":
                logger.info("Falling back to DuckDuckGo search...")
                results = await self._search_duckduckgo(query)
            elif self.api_key:
                logger.info("Falling back to Tavily search...")
                results = await self._search_tavily(query)

        # 3. Direct HTTP scrape fallback if library was rate limited
        if not results:
            results = await self._search_ddg_html_fallback(query)

        return results

    async def _search_duckduckgo(self, query: WebSearchQuery) -> list[SearchResultItem]:
        """Perform search using duckduckgo_search library in a worker thread."""
        loop = asyncio.get_running_loop()

        def _sync_ddg_call() -> list[dict[str, Any]]:
            try:
                from duckduckgo_search import DDGS
                with DDGS(timeout=self.timeout) as ddgs:
                    raw_res = list(
                        ddgs.text(
                            query.query,
                            region=query.region,
                            safesearch=query.safesearch,
                            max_results=query.max_results,
                        )
                    )
                    return raw_res
            except Exception as e:
                logger.warning(f"DuckDuckGo search error: {e}")
                return []

        raw_results = await loop.run_in_executor(None, _sync_ddg_call)

        items: list[SearchResultItem] = []
        for r in raw_results:
            title = r.get("title") or "Web Search Result"
            url = r.get("href") or r.get("link") or r.get("url") or ""
            body = r.get("body") or r.get("snippet") or ""
            if url:
                items.append(
                    SearchResultItem(
                        title=title.strip(),
                        url=url.strip(),
                        snippet=body.strip(),
                        source="duckduckgo",
                    )
                )
        return items

    async def _search_tavily(self, query: WebSearchQuery) -> list[SearchResultItem]:
        """Perform search using Tavily API."""
        if not self.api_key:
            logger.warning("Tavily search requested but no API key configured.")
            return []

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.api_key,
            "query": query.query,
            "search_depth": "basic",
            "include_answer": False,
            "max_results": query.max_results,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    items: list[SearchResultItem] = []
                    for r in data.get("results", []):
                        items.append(
                            SearchResultItem(
                                title=r.get("title", "Tavily Result").strip(),
                                url=r.get("url", "").strip(),
                                snippet=r.get("content", "").strip(),
                                source="tavily",
                            )
                        )
                    return items
                else:
                    logger.warning(f"Tavily returned status {resp.status_code}: {resp.text}")
        except Exception as err:
            logger.warning(f"Tavily search exception: {err}")

        return []

    async def _search_ddg_html_fallback(self, query: WebSearchQuery) -> list[SearchResultItem]:
        """Lightweight direct HTTP fallback to DuckDuckGo HTML endpoint."""
        endpoint = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        data = {"q": query.query}

        try:
            async with httpx.AsyncClient(headers=headers, timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.post(endpoint, data=data)
                if resp.status_code == 200:
                    import re
                    # Simple regex parser for result title and snippets in html
                    titles = re.findall(r'<a class="result__url"[^>]*href="([^"]+)"[^>]*>', resp.text)
                    snippets = re.findall(r'<a class="result__snippet"[^>]*>([\s\S]*?)</a>', resp.text)
                    items: list[SearchResultItem] = []
                    for u, s in zip(titles[:query.max_results], snippets[:query.max_results]):
                        clean_snippet = re.sub(r"<[^>]+>", "", s).strip()
                        items.append(
                            SearchResultItem(
                                title="DuckDuckGo Search Result",
                                url=u.strip(),
                                snippet=clean_snippet,
                                source="duckduckgo_html",
                            )
                        )
                    return items
        except Exception as e:
            logger.debug(f"Direct HTML search fallback failed: {e}")

        return []
