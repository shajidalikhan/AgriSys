"""Google Gemini LLM and Embedding Provider.

Fulfills §2.3 and §2.4: Provides Google Gemini chat completions, streaming,
multimodal vision, and embeddings using the BaseLLMProvider and BaseEmbeddingProvider interfaces.
Utilizes the official Google Generative Language OpenAI-compatible endpoint.
"""

from typing import Any, AsyncIterator, Dict, List, Optional
import os
from openai import AsyncOpenAI
from agrisys.providers.base import BaseLLMProvider, BaseEmbeddingProvider


class GeminiProvider(BaseLLMProvider, BaseEmbeddingProvider):
    """Google Gemini implementation of BaseLLMProvider and BaseEmbeddingProvider."""

    DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-3.8-flash",
        embedding_model: str = "text-embedding-004",
        embedding_dimension: int = 768,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model
        self.embedding_model = embedding_model
        self._dimension = embedding_dimension
        self.temperature = temperature
        self.max_tokens = max_tokens
        # Google Generative Language OpenAI compatibility endpoint
        raw_base = base_url or os.getenv("GEMINI_BASE_URL", self.DEFAULT_BASE_URL)
        self.base_url = raw_base.rstrip("/") + "/"
        self.timeout = timeout

        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.api_key or "mock-gemini-key",
                base_url=self.base_url,
                timeout=self.timeout,
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
        )
        return [data.embedding for data in response.data]

    @property
    def supports_vision(self) -> bool:
        """Google Gemini models natively support multimodal vision inputs."""
        return True

    @property
    def context_window(self) -> int:
        """Gemini Flash/Pro architectures feature a 1,000,000+ token context window."""
        return 1_000_000

    @property
    def dimension(self) -> int:
        """Output embedding dimensions."""
        return self._dimension
