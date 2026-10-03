"""OpenAI LLM and Embedding Provider.

Fulfills §2.3 and §2.4: Provides OpenAI chat completions, streaming,
and text embeddings using the BaseLLMProvider and BaseEmbeddingProvider interfaces.
"""

from typing import Any, AsyncIterator, Dict, List, Optional
import os
import httpx
from openai import AsyncOpenAI
from agrisys.providers.base import BaseLLMProvider, BaseEmbeddingProvider


class OpenAIProvider(BaseLLMProvider, BaseEmbeddingProvider):
    """OpenAI implementation of BaseLLMProvider and BaseEmbeddingProvider."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        embedding_model: str = "text-embedding-3-large",
        embedding_dimension: int = 3072,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        base_url: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.embedding_model = embedding_model
        self._dimension = embedding_dimension
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url

        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.api_key or "mock-key",
                base_url=self.base_url,
            )
        return self._client

    async def complete(self, messages: List[Dict[str, Any]], **kwargs: Any) -> str:
        """Execute non-streaming completion."""
        client = self._get_client()
        model = kwargs.get("model", self.model)
        temp = kwargs.get("temperature", self.temperature)
        max_t = kwargs.get("max_tokens", self.max_tokens)

        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temp,
            max_tokens=max_t,
        )
        return response.choices[0].message.content or ""

    async def stream(self, messages: List[Dict[str, Any]], **kwargs: Any) -> AsyncIterator[str]:
        """Execute streaming completion yielding delta strings."""
        client = self._get_client()
        model = kwargs.get("model", self.model)
        temp = kwargs.get("temperature", self.temperature)
        max_t = kwargs.get("max_tokens", self.max_tokens)

        response_stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temp,
            max_tokens=max_t,
            stream=True,
        )
        async for chunk in response_stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def embed_query(self, text: str) -> List[float]:
        """Generate embedding vector for a single query text."""
        res = await self.embed_documents([text])
        return res[0]

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for multiple document chunks."""
        client = self._get_client()
        response = await client.embeddings.create(
            model=self.embedding_model,
            input=texts,
            dimensions=self._dimension,
        )
        return [data.embedding for data in response.data]

    @property
    def supports_vision(self) -> bool:
        """OpenAI models with vision capability."""
        vision_models = ["gpt-4o", "gpt-4-turbo", "gpt-4-vision", "gpt-5", "gpt-5.5"]
        return any(vm in self.model.lower() for vm in vision_models)

    @property
    def context_window(self) -> int:
        """Context window length in tokens."""
        if "gpt-5" in self.model.lower():
            return 1_000_000
        return 128_000

    @property
    def dimension(self) -> int:
        """Output embedding dimensions."""
        return self._dimension
