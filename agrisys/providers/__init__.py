"""Provider Abstraction Layer Package.

Exports BaseLLMProvider, BaseEmbeddingProvider, concrete providers,
and provider factory methods.
"""

from agrisys.providers.base import (
    BaseLLMProvider,
    BaseEmbeddingProvider,
    StreamingAdapter,
)
from agrisys.providers.openai_provider import OpenAIProvider
from agrisys.providers.groq_provider import GroqProvider
from agrisys.providers.ollama_provider import OllamaProvider
from agrisys.providers.openrouter_provider import OpenRouterProvider
from agrisys.providers.local_embedding import LocalEmbeddingProvider
from agrisys.providers.gemini_provider import GeminiProvider
from agrisys.providers.factory import (
    get_llm_provider,
    get_embedding_provider,
    register_llm_provider,
    register_embedding_provider,
)

__all__ = [
    "BaseLLMProvider",
    "BaseEmbeddingProvider",
    "StreamingAdapter",
    "OpenAIProvider",
    "GroqProvider",
    "OllamaProvider",
    "OpenRouterProvider",
    "LocalEmbeddingProvider",
    "GeminiProvider",
    "get_llm_provider",
    "get_embedding_provider",
    "register_llm_provider",
    "register_embedding_provider",
]
