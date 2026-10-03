"""Provider Factory and Registry.

Enforces DIP (Dependency Inversion Principle) and OCP (Open/Closed Principle).
Higher-level agents request an LLM or Embedding provider without coupling
to concrete implementation classes.
"""

from typing import Any, Dict, Optional, Type
from agrisys.providers.base import BaseLLMProvider, BaseEmbeddingProvider
from agrisys.providers.openai_provider import OpenAIProvider
from agrisys.providers.groq_provider import GroqProvider
from agrisys.providers.ollama_provider import OllamaProvider
from agrisys.providers.openrouter_provider import OpenRouterProvider
from agrisys.providers.local_embedding import LocalEmbeddingProvider
from agrisys.providers.gemini_provider import GeminiProvider

# Registry mapping provider names to concrete classes
LLM_PROVIDER_REGISTRY: Dict[str, Type[BaseLLMProvider]] = {
    "openai": OpenAIProvider,
    "groq": GroqProvider,
    "ollama": OllamaProvider,
    "openrouter": OpenRouterProvider,
    "gemini": GeminiProvider,
    "google": GeminiProvider,
}

EMBEDDING_PROVIDER_REGISTRY: Dict[str, Type[BaseEmbeddingProvider]] = {
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
    "huggingface_local": LocalEmbeddingProvider,
    "local": LocalEmbeddingProvider,
    "gemini": GeminiProvider,
    "google": GeminiProvider,
}


def register_llm_provider(name: str, provider_cls: Type[BaseLLMProvider]) -> None:
    """Register a new LLM provider class dynamically without editing existing code."""
    LLM_PROVIDER_REGISTRY[name.lower()] = provider_cls


def register_embedding_provider(name: str, provider_cls: Type[BaseEmbeddingProvider]) -> None:
    """Register a new Embedding provider class dynamically without editing existing code."""
    EMBEDDING_PROVIDER_REGISTRY[name.lower()] = provider_cls


def get_llm_provider(name: Optional[str] = None, **kwargs: Any) -> BaseLLMProvider:
    """Factory method to instantiate an LLM provider by config name.

    Args:
        name: Provider identifier (e.g., 'gemini', 'openai', 'groq', 'ollama', 'openrouter').
              If None, loads settings from config/providers.yaml.
        **kwargs: Provider constructor arguments.

    Returns:
        Instance conforming to BaseLLMProvider.
    """
    if name is None:
        try:
            from agrisys.config import load_providers_config
            cfg = load_providers_config()
            name = cfg.llm.provider
            if "model" not in kwargs and cfg.llm.model:
                kwargs["model"] = cfg.llm.model
            if "api_key" not in kwargs and cfg.llm.api_key:
                kwargs["api_key"] = cfg.llm.api_key
            if "temperature" not in kwargs:
                kwargs["temperature"] = cfg.llm.temperature
            if "max_tokens" not in kwargs:
                kwargs["max_tokens"] = cfg.llm.max_tokens
        except Exception:
            name = "gemini"

    key = name.lower()
    if key not in LLM_PROVIDER_REGISTRY:
        raise ValueError(
            f"Unknown LLM provider '{name}'. Registered providers: {list(LLM_PROVIDER_REGISTRY.keys())}"
        )
    return LLM_PROVIDER_REGISTRY[key](**kwargs)


def get_embedding_provider(name: str, **kwargs: Any) -> BaseEmbeddingProvider:
    """Factory method to instantiate an Embedding provider by config name.

    Args:
        name: Provider identifier ('huggingface_local', 'openai', 'ollama', 'local').
        **kwargs: Provider constructor arguments.

    Returns:
        Instance conforming to BaseEmbeddingProvider.
    """
    key = name.lower()
    if key not in EMBEDDING_PROVIDER_REGISTRY:
        raise ValueError(
            f"Unknown Embedding provider '{name}'. Registered: {list(EMBEDDING_PROVIDER_REGISTRY.keys())}"
        )
    return EMBEDDING_PROVIDER_REGISTRY[key](**kwargs)
