"""Ollama Local LLM and Embedding Provider.

Fulfills §2.3 and §2.4: Provides offline local inference via Ollama,
implementing BaseLLMProvider and BaseEmbeddingProvider.
"""

from typing import Any, AsyncIterator, Dict, List, Optional
import json
import os
import httpx
from agrisys.providers.base import BaseLLMProvider, BaseEmbeddingProvider


class OllamaProvider(BaseLLMProvider, BaseEmbeddingProvider):
    """Ollama local server implementation."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: str = "llama3.2",
        embedding_model: str = "nomic-embed-text",
        embedding_dimension: int = 768,
        temperature: float = 0.1,
        context_len: int = 8192,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model = model
        self.embedding_model = embedding_model
        self._dimension = embedding_dimension
        self.temperature = temperature
        self._context_len = context_len
        self.timeout = timeout

    async def complete(self, messages: List[Dict[str, Any]], **kwargs: Any) -> str:
        """Execute non-streaming completion via Ollama."""
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")

    async def stream(self, messages: List[Dict[str, Any]], **kwargs: Any) -> AsyncIterator[str]:
        """Execute streaming completion via Ollama yielding newline-delimited JSON chunks."""
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        delta = chunk.get("message", {}).get("content", "")
                        if delta:
                            yield delta
                    except json.JSONDecodeError:
                        continue

    async def embed_query(self, text: str) -> List[float]:
        """Embed a single query using Ollama embedding model."""
        res = await self.embed_documents([text])
        return res[0]

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed document chunks via Ollama embeddings API."""
        url = f"{self.base_url}/api/embeddings"
        embeddings: List[List[float]] = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for text in texts:
                resp = await client.post(url, json={"model": self.embedding_model, "prompt": text})
                resp.raise_for_status()
                data = resp.json()
                embeddings.append(data.get("embedding", []))

        return embeddings

    @property
    def supports_vision(self) -> bool:
        """True if model is known to be vision-capable."""
        vision_indicators = ["vision", "llava", "bakllava", "moondream"]
        return any(v in self.model.lower() for v in vision_indicators)

    @property
    def context_window(self) -> int:
        """Context window length for current model."""
        return self._context_len

    @property
    def dimension(self) -> int:
        """Embedding vector dimension."""
        return self._dimension
