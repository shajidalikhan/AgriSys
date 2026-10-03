"""AgriSys Configuration Manager and Pydantic v2 Schemas.

Fulfills Directive 7 (Configuration Over Code) and §2.6:
Parses YAML configurations with environment variable interpolation and Pydantic v2 validation.
"""

from typing import Any, Dict, List, Optional
import os
import re
from pathlib import Path
import yaml
from pydantic import BaseModel, Field, field_validator


def _expand_env_vars(content: str) -> str:
    """Expand ${VAR} and ${VAR:-default} patterns using os.environ."""
    pattern = re.compile(r"\$\{([^}:]+)(?::-([^}]*))?\}")

    def _replace(match: re.Match) -> str:
        var_name = match.group(1)
        default_val = match.group(2) if match.group(2) is not None else ""
        return os.getenv(var_name, default_val)

    return pattern.sub(_replace, content)


class LLMConfig(BaseModel):
    """Configuration schema for primary LLM."""
    provider: str = Field(default="gemini", description="Provider key (gemini, openai, groq, ollama, openrouter)")
    model: str = Field(default="gemini-3.8-flash", description="Model identifier")
    api_key: Optional[str] = Field(default=None, description="API Key")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1)


class EmbeddingConfig(BaseModel):
    """Configuration schema for embeddings."""
    provider: str = Field(default="local", description="Embedding provider (local, openai, ollama, gemini)")
    model: str = Field(default="intfloat/multilingual-e5-large")
    dimension: int = Field(default=1024, ge=64)


class VisionConfig(BaseModel):
    """Configuration schema for orchestrator vision model."""
    provider: str = Field(default="gemini", description="Vision provider (gemini, openai, ollama)")
    model: str = Field(default="gemini-3.8-flash")
    api_key: Optional[str] = Field(default=None)


class HallucinationGuardConfig(BaseModel):
    """Configuration schema for hallucination detection LLM judge."""
    provider: str = Field(default="groq")
    model: str = Field(default="llama-3.3-70b-versatile")


class OpenRouterConfig(BaseModel):
    """Configuration schema for OpenRouter specific settings."""
    api_key: Optional[str] = Field(default=None)
    default_model: str = Field(default="anthropic/claude-3.5-sonnet")
    fallback_model: str = Field(default="meta-llama/llama-3.3-70b-instruct")


class WebSearchConfig(BaseModel):
    """Configuration schema for web search provider."""
    provider: str = Field(default="duckduckgo", description="Search provider (duckduckgo, tavily)")
    api_key: Optional[str] = Field(default=None, description="API Key (for Tavily, etc.)")
    max_results: int = Field(default=5, ge=1, le=20)
    timeout_seconds: int = Field(default=10, ge=1, le=60)


class ProvidersConfig(BaseModel):
    """Root configuration for all AI providers."""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    vision: VisionConfig = Field(default_factory=VisionConfig)
    hallucination_guard: HallucinationGuardConfig = Field(default_factory=HallucinationGuardConfig)
    openrouter: Optional[OpenRouterConfig] = Field(default=None)
    web_search: WebSearchConfig = Field(default_factory=WebSearchConfig)


class IngestionConfig(BaseModel):
    """Configuration for RAG ingestion."""
    chunk_size_tokens: int = Field(default=512)
    chunk_overlap_tokens: int = Field(default=128)
    supported_formats: List[str] = Field(default_factory=lambda: ["pdf", "html", "csv", "txt"])


class VectorStoreConfig(BaseModel):
    """Configuration for vector store."""
    provider: str = Field(default="qdrant")
    collection_name: str = Field(default="agrisys_knowledge")
    qdrant_url: str = Field(default="http://localhost:6333")
    api_key: Optional[str] = Field(default=None)
    distance: str = Field(default="Cosine")


class RetrievalConfig(BaseModel):
    """Configuration for RAG retrieval."""
    hyde_enabled: bool = Field(default=True)
    top_k_bm25: int = Field(default=20)
    top_k_dense: int = Field(default=20)
    top_k_cross_encoder: int = Field(default=5)
    top_k_final: int = Field(default=5)
    cross_encoder_model: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    mmr_lambda: float = Field(default=0.7)
    metadata_boost: float = Field(default=0.15)


class GuardConfig(BaseModel):
    """Configuration for hallucination guard."""
    hallucination_score_threshold: float = Field(default=0.70)
    escalate_webhook_url: Optional[str] = Field(default=None)


class RAGConfig(BaseModel):
    """Root configuration for RAG system."""
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    guard: GuardConfig = Field(default_factory=GuardConfig)


def load_yaml_config(file_path: Path | str) -> Dict[str, Any]:
    """Read a YAML file and interpolate environment variables."""
    p = Path(file_path)
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        raw = f.read()
    expanded = _expand_env_vars(raw)
    data = yaml.safe_load(expanded)
    return data or {}


def load_providers_config(config_path: Path | str = "config/providers.yaml") -> ProvidersConfig:
    """Load and validate ProvidersConfig from YAML file."""
    data = load_yaml_config(config_path)
    return ProvidersConfig.model_validate(data)


def load_rag_config(config_path: Path | str = "config/rag.yaml") -> RAGConfig:
    """Load and validate RAGConfig from YAML file."""
    data = load_yaml_config(config_path)
    return RAGConfig.model_validate(data)
