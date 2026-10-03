"""Unit tests for Provider Abstraction Layer (§2).

Tests compliance with SOLID principles, interface contracts,
provider registration, and streaming adapters.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from agrisys.providers.base import BaseLLMProvider, BaseEmbeddingProvider, StreamingAdapter
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


class MockCustomProvider(BaseLLMProvider):
    """Custom provider for testing Open/Closed Principle extension."""
    async def complete(self, messages, **kwargs):
        return "mock response"

    async def stream(self, messages, **kwargs):
        yield "mock "
        yield "stream"

    @property
    def supports_vision(self):
        return True

    @property
    def context_window(self):
        return 64000


@pytest.mark.asyncio
async def test_streaming_adapter():
    """Test StreamingAdapter splits full text into streaming chunks."""
    text = "Hello agricultural expert system"
    tokens = []
    async for token in StreamingAdapter.adapt(text, delay=0.0):
        tokens.append(token)

    reconstructed = "".join(tokens)
    assert reconstructed == text
    assert len(tokens) == 4


def test_openai_provider_properties():
    """Verify OpenAI provider vision and context window detection."""
    p_vision = OpenAIProvider(model="gpt-4o")
    assert p_vision.supports_vision is True
    assert p_vision.context_window == 128_000

    p_gpt5 = OpenAIProvider(model="gpt-5.5")
    assert p_gpt5.supports_vision is True
    assert p_gpt5.context_window == 1_000_000


def test_groq_provider_properties():
    """Verify Groq provider constraints (Constraint 1: no vision)."""
    p = GroqProvider(model="llama-3.3-70b-versatile")
    assert p.supports_vision is False
    assert p.context_window == 128_000


def test_ollama_provider_properties():
    """Verify Ollama provider config."""
    p_text = OllamaProvider(model="llama3.2")
    assert p_text.supports_vision is False

    p_vision = OllamaProvider(model="llava:7b")
    assert p_vision.supports_vision is True


@pytest.mark.asyncio
async def test_openrouter_fallback_mechanism():
    """Verify OpenRouter falls back to secondary model if primary raises error."""
    p = OpenRouterProvider(
        api_key="test-key",
        default_model="primary-fail-model",
        fallback_model="secondary-ok-model",
    )

    call_history = []

    async def mock_call(model, messages, **kwargs):
        call_history.append(model)
        if model == "primary-fail-model":
            raise RuntimeError("Primary rate limited")
        return "Success from fallback"

    p._call_complete = mock_call  # type: ignore

    res = await p.complete([{"role": "user", "content": "test"}])
    assert res == "Success from fallback"
    assert call_history == ["primary-fail-model", "secondary-ok-model"]


@pytest.mark.asyncio
async def test_local_embedding_provider():
    """Verify deterministic local embeddings produce normalized vectors of expected dimension."""
    provider = LocalEmbeddingProvider(dimension=1024)
    query_vec = await provider.embed_query("wheat rust disease management")
    assert len(query_vec) == 1024
    # Check normalized
    import numpy as np
    norm = np.linalg.norm(query_vec)
    assert pytest.approx(norm, 0.01) == 1.0

    docs_vecs = await provider.embed_documents(["doc 1", "doc 2"])
    assert len(docs_vecs) == 2
    assert len(docs_vecs[0]) == 1024


def test_provider_factory_and_open_closed_principle():
    """Test registry retrieval and dynamic registration without code modification."""
    # Register custom provider
    register_llm_provider("custom_mock", MockCustomProvider)
    instance = get_llm_provider("custom_mock")
    assert isinstance(instance, MockCustomProvider)
    assert instance.supports_vision is True

    # Check unknown provider raises descriptive ValueError
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_llm_provider("non_existent_provider_xyz")


def test_gemini_provider_properties():
    """Verify Gemini provider properties (multimodal vision, 1M context, 768 dim)."""
    p = GeminiProvider(model="gemini-3.8-flash")
    assert p.supports_vision is True
    assert p.context_window == 1_000_000
    assert p.dimension == 768
    assert p.base_url == "https://generativelanguage.googleapis.com/v1beta/openai/"


def test_gemini_provider_factory():
    """Verify Gemini provider lookup via factory registry."""
    instance = get_llm_provider("gemini")
    assert isinstance(instance, GeminiProvider)
    assert instance.supports_vision is True

    # Also test google alias
    alias_inst = get_llm_provider("google")
    assert isinstance(alias_inst, GeminiProvider)

    # Embedding registry
    embed_inst = get_embedding_provider("gemini")
    assert isinstance(embed_inst, GeminiProvider)


def test_gemini_default_from_config():
    """Verify parameterless get_llm_provider loads gemini-3.8-flash from providers.yaml."""
    instance = get_llm_provider()
    assert isinstance(instance, GeminiProvider)
    assert instance.model == "gemini-3.8-flash"


@pytest.mark.asyncio
async def test_gemini_complete_mock():
    """Verify GeminiProvider complete method with mocked AsyncOpenAI client."""
    provider = GeminiProvider(api_key="mock-key", model="gemini-3.8-flash")

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Gemini response for agricultural query"
    mock_response.choices = [mock_choice]

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    provider._client = mock_client

    result = await provider.complete([{"role": "user", "content": "How to treat wheat rust?"}])
    assert result == "Gemini response for agricultural query"
    mock_client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_gemini_stream_mock():
    """Verify GeminiProvider stream method with mocked AsyncOpenAI client."""
    provider = GeminiProvider(api_key="mock-key", model="gemini-3.8-flash")

    chunk1 = MagicMock()
    chunk1.choices = [MagicMock(delta=MagicMock(content="Hello "))]
    chunk2 = MagicMock()
    chunk2.choices = [MagicMock(delta=MagicMock(content="farmer"))]

    async def mock_stream_generator(*args, **kwargs):
        for chunk in [chunk1, chunk2]:
            yield chunk

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=mock_stream_generator)
    provider._client = mock_client

    tokens = []
    async for token in provider.stream([{"role": "user", "content": "Hello"}]):
        tokens.append(token)

    assert tokens == ["Hello ", "farmer"]

