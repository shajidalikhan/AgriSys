"""HyDE (Hypothetical Document Embeddings) Query Expansion.

Fulfills §10.2:
- LLM generates a hypothetical expert document/answer to the user query
- The hypothetical document is embedded and used as the query vector
- Resilient fallback to raw query on timeout or LLM failure
"""

from typing import Optional
from agrisys.providers.base import BaseLLMProvider

HYDE_PROMPT_TEMPLATE = """You are an expert agricultural scientist.
Write a concise, factual excerpt from an ICAR or FAO agricultural advisory manual that directly answers the farmer's question below.
Do not include conversational filler. Write only the informative passage.

Question: {query}
Passage:"""


class HyDEExpander:
    """Generates hypothetical agricultural documents for enhanced semantic retrieval."""

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None) -> None:
        self.llm_provider = llm_provider

    async def expand(self, query: str) -> str:
        """Generate hypothetical answer document or fallback to query."""
        if not self.llm_provider:
            return query

        try:
            prompt = HYDE_PROMPT_TEMPLATE.format(query=query)
            messages = [{"role": "user", "content": prompt}]
            hypothetical_doc = await self.llm_provider.complete(messages, max_tokens=256, temperature=0.3)
            cleaned = hypothetical_doc.strip()
            if cleaned and len(cleaned) > 20:
                return f"{query}\n{cleaned}"
            return query
        except Exception:
            # Fallback gracefully to raw query
            return query
