"""Provider Abstraction Layer: Base Interfaces.

This module defines the abstract base classes for LLM and Embedding providers
in adherence to the SOLID principles (specifically SRP, LSP, ISP, and DIP).
No agent should import provider-specific SDKs directly; all interaction
must flow through these interfaces.
"""

from abc import ABC, abstractmethod
import asyncio
from typing import Any, AsyncIterator, Dict, List, Optional


class BaseLLMProvider(ABC):
    """Single Responsibility: provide LLM completions and streaming only."""

    @abstractmethod
    async def complete(self, messages: List[Dict[str, Any]], **kwargs: Any) -> str:
        """Execute a non-streaming chat completion.

        Args:
            messages: List of message dictionaries with 'role' and 'content'.
            **kwargs: Provider-specific overrides (temperature, max_tokens, etc.).

        Returns:
            The completion text from the LLM.
        """
        ...

    @abstractmethod
    async def stream(self, messages: List[Dict[str, Any]], **kwargs: Any) -> AsyncIterator[str]:
        """Execute a streaming chat completion yielding token chunks.

        Args:
            messages: List of message dictionaries with 'role' and 'content'.
            **kwargs: Provider-specific overrides.

        Yields:
            Token string deltas as they are received.
        """
        ...

    @property
    @abstractmethod
    def supports_vision(self) -> bool:
        """Whether this provider and model natively accept image inputs."""
        ...

    @property
    @abstractmethod
    def context_window(self) -> int:
        """Maximum context length in tokens supported by this model."""
        ...


class BaseEmbeddingProvider(ABC):
    """Single Responsibility: provide text embeddings only."""

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """Embed a single query string.

        Args:
            text: Query string to encode.

        Returns:
            Dense vector representation.
        """
        ...

    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of document strings in batch.

        Args:
            texts: List of document chunks.

        Returns:
            List of dense vectors.
        """
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimensionality of output embedding vectors."""
        ...


class StreamingAdapter:
    """Simulates streaming token-by-token delivery for non-streaming providers.

    Fulfills §2.5 Constraint 2: ensures UI receives chunked streaming
    even if the underlying provider or model returns complete text in one block.
    """

    @staticmethod
    async def adapt(full_text: str, chunk_size: int = 4, delay: float = 0.01) -> AsyncIterator[str]:
        """Chunk a complete string into streaming tokens with small delay.

        Args:
            full_text: The complete text response.
            chunk_size: Number of characters or word pieces per chunk.
            delay: Simulated delay in seconds between tokens.

        Yields:
            Text chunks sequentially.
        """
        words = full_text.split(" ")
        for i, word in enumerate(words):
            token = word if i == len(words) - 1 else word + " "
            yield token
            if delay > 0:
                await asyncio.sleep(delay)
