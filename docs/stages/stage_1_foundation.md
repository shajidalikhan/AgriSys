# Stage 1: Foundation Layer Implementation Detail

## 1. Overview & Objectives
Stage 1 establishes the foundational infrastructure of AgriSys:
- Implements the complete **Provider Abstraction Layer** (§2) guaranteeing that no downstream agent ever imports third-party provider SDKs directly.
- Implements the **RAG Ingestion Pipeline** (§10.1) capable of loading PDF, HTML, CSV, and TXT agronomic manuals, splitting them semantically, extracting ICAR/FAO metadata tags, and embedding them into Qdrant.
- Implements the **Advanced RAG Retrieval Pipeline** (§10.2) combining HyDE query expansion, BM25 sparse keyword retrieval, Qdrant dense vector search, Reciprocal Rank Fusion (RRF), Cross-Encoder candidate reranking, MMR diversity filtering, and metadata boosting.
- Implements the **Hallucination Guard** (§10.3) scoring factual grounding and triggering escalation when confidence drops below 0.70.
- Implements the **FastAPI Backend Shell** (§1.4, §17.1) with health endpoints, REST querying, knowledge ingestion, and real-time streaming over WebSocket (`/ws/chat`).
- Defines container orchestration (`docker-compose.yml`) for Qdrant, Redis, Postgres, MinIO, and Langfuse.

---

## 2. Technologies & Dependencies Used

| Technology / Library | Version | Role in Stage 1 | Rationale |
| :--- | :--- | :--- | :--- |
| **Python** | `3.12.3` | Language runtime | Modern type hints, high performance asyncio, memory efficiency. |
| **FastAPI** | `0.141.1` | REST & WebSocket server | Async-first, automatic OpenAPI docs, native WebSocket support. |
| **Pydantic** | `2.11.7` | Data validation & schemas | Strict type validation, zero magic strings, fast C-core serialization. |
| **Qdrant Client** | `1.19.0` | Vector database client | Production-grade vector store with support for dense cosine distance and rich payload filtering; includes in-memory mode for offline testing. |
| **Rank-BM25** | `0.2.2` | Sparse keyword index | BM25Okapi for term-level precision (pesticide names, exact varieties). |
| **HTTPX** | `0.28.1` | Async HTTP client | High performance async calls to Groq, OpenRouter, and Ollama with SSE streaming. |
| **OpenAI SDK** | `1.97.1` | OpenAI API client | Native async client for GPT-4o / GPT-5.5 completions and embeddings. |
| **PyYAML** | `6.0.3` | Configuration parser | Reading `config/*.yaml` files with variable expansion. |
| **Pytest / Pytest-Asyncio** | `9.1.1` / `1.4.0` | Test framework | Automated unit and integration testing across async endpoints and pipelines. |

---

## 3. Modules & Files Created

### 3.1 Provider Abstraction Layer (`agrisys/providers/`)
- `base.py`:
  - `BaseLLMProvider`: Abstract interface requiring `complete()`, `stream()`, `supports_vision`, `context_window`.
  - `BaseEmbeddingProvider`: Abstract interface requiring `embed_query()`, `embed_documents()`, `dimension`.
  - `StreamingAdapter`: Helper converting non-streaming responses into async token generators (§2.5 Constraint 2).
- `openai_provider.py`:
  - `OpenAIProvider`: Implements `BaseLLMProvider` and `BaseEmbeddingProvider` using AsyncOpenAI.
- `groq_provider.py`:
  - `GroqProvider`: Implements `BaseLLMProvider` with SSE streaming for Llama 3.3 models via HTTPX. Pure text model (Constraint 1: `supports_vision = False`).
- `ollama_provider.py`:
  - `OllamaProvider`: Implements offline local LLM and embedding inference via Ollama server (`localhost:11434`).
- `openrouter_provider.py`:
  - `OpenRouterProvider`: Gateway supporting 200+ models with automatic secondary model fallback.
- `local_embedding.py`:
  - `LocalEmbeddingProvider`: Generates 1024-dimensional vectors matching `multilingual-e5-large`; uses deterministic normalization fallback for fast offline development.
- `factory.py`:
  - Dynamic registries `LLM_PROVIDER_REGISTRY` and `EMBEDDING_PROVIDER_REGISTRY`.
  - Factory functions `get_llm_provider()` and `get_embedding_provider()`.
  - Registration functions `register_llm_provider()` and `register_embedding_provider()` for OCP compliance.

### 3.2 Configuration Management (`agrisys/config.py`, `config/`)
- `config/providers.yaml`: Model definitions, temperatures, dimensions, and API keys.
- `config/agents.yaml`: Feature flags, confidence thresholds, and ensemble weights.
- `config/rag.yaml`: Chunk sizes, top-k parameters, reranker models, and threshold limits.
- `agrisys/config.py`: Environment variable expansion (`${VAR:-default}`) and Pydantic v2 validation models (`ProvidersConfig`, `RAGConfig`, etc.).

### 3.3 RAG Ingestion Pipeline (`agrisys/rag/ingestion/`)
- `models.py`: `Document`, `Chunk`, and `ChunkMetadata`.
- `loaders.py`: `DocumentLoader` with format-specific parsing for PDF, HTML, CSV, and TXT.
- `chunker.py`: `SemanticChunker` dividing text into 512-token windows with 128-token overlaps while respecting sentence and paragraph boundaries.
- `tagger.py`: `MetadataTagger` automatically categorizing source (ICAR/FAO), crop (English & Hindi), state (UP/Punjab/etc.), domain (disease/nutrition/market/weather), and language (`hi`/`en`).
- `upserter.py`: `QdrantUpserter` creating collections and indexing vectors with payloads into Qdrant (with snappy in-memory fallback).
- `pipeline.py`: `IngestionPipeline` orchestrating document loading, chunking, tagging, and upserting.

### 3.4 RAG Retrieval Pipeline (`agrisys/rag/retrieval/`)
- `models.py`: `ScoredChunk` model.
- `hyde.py`: `HyDEExpander` using LLM to generate hypothetical expert manual passages to expand query semantic representation.
- `bm25.py`: `BM25Retriever` computing sparse keyword scores.
- `rrf.py`: `ReciprocalRankFusion` consolidating sparse and dense rankings using $RRF(d) = \sum \frac{1}{60 + \text{rank}}$.
- `reranker.py`: `CrossEncoderReranker` applying full query-passage cross-attention scoring.
- `mmr.py`:
  - `MMRDiversityFilter` computing Maximal Marginal Relevance to remove redundancy and ensure source diversity.
  - `MetadataBooster` boosting scores of chunks matching query crop, state, or domain by configured factor (+0.15).
- `pipeline.py`: `RetrievalPipeline` end-to-end coordinator.

### 3.5 Hallucination Guard (`agrisys/rag/guard.py`)
- `HallucinationVerdict`: Output model containing score (0.0–1.0), unsupported claims list, and verdict (`pass` or `escalate`).
- `HallucinationGuard`: LLM-as-a-Judge using `JUDGE_PROMPT`, with heuristic lexical stopword-filtered fallback and asynchronous KCC escalation webhook.

### 3.6 API Layer (`agrisys/api/main.py`)
- `GET /api/health`: Service health and active build stage.
- `GET /api/health/ready`: Readiness probe checking pipeline readiness.
- `GET /api/providers`: Introspection endpoint listing registered and active LLM/Embedding providers.
- `POST /api/ingest/text`: REST endpoint for indexing text knowledge.
- `POST /api/query`: REST endpoint executing full RAG query, grounding, and hallucination verification.
- `WebSocket /ws/chat`: Real-time streaming WebSocket emitting status events, retrieved sources, token deltas, and hallucination verification results.

---

## 4. SOLID Principles Compliance Matrix

| Principle | Implementation in Stage 1 | Verification |
| :--- | :--- | :--- |
| **SRP** (Single Responsibility) | `BaseLLMProvider` handles text completion only; `DocumentLoader` loads only; `SemanticChunker` chunks only; `HallucinationGuard` judges grounding only. | Each class has exactly one reason to change. |
| **OCP** (Open/Closed) | Adding a new LLM provider requires subclassing `BaseLLMProvider` and calling `register_llm_provider()`. No modifications to existing provider files or API logic. | Tested in `test_provider_factory_and_open_closed_principle`. |
| **LSP** (Liskov Substitution) | Any provider (`OpenAIProvider`, `GroqProvider`, `OllamaProvider`) can be substituted for `BaseLLMProvider` without altering caller code. | Verified across mock and concrete providers. |
| **ISP** (Interface Segregation) | LLM capabilities (`BaseLLMProvider`) are separate from embedding capabilities (`BaseEmbeddingProvider`). Models that only embed implement only `BaseEmbeddingProvider`. | No fat interfaces. |
| **DIP** (Dependency Inversion) | `RetrievalPipeline` and `IngestionPipeline` depend on `BaseEmbeddingProvider` and `BaseLLMProvider` interfaces, not concrete classes. | Dependencies injected via constructors. |

---

## 5. Resilience & Fallback Chains

1. **Vector Store Fallback**:
   - Primary: Remote Qdrant server (`http://localhost:6333`).
   - Fallback: In-memory Qdrant instance (`location=":memory:"`) if remote container is offline during local development or unit testing.
2. **LLM Provider Fallback**:
   - Primary: Configured provider in `config/providers.yaml`.
   - OpenRouter fallback: `default_model` falls back to `fallback_model` upon rate limit or failure.
   - Offline fallback: Structured advisory synthesis directly from retrieved top-scoring chunks.
3. **Embedding Fallback**:
   - Primary: `SentenceTransformer` local model.
   - Fallback: Deterministic normalized hash vector maintaining vocabulary overlap without requiring heavy checkpoint downloads.
4. **Hallucination Verification Fallback**:
   - Primary: LLM-as-a-judge executing `JUDGE_PROMPT`.
   - Fallback: High-precision lexical alignment judge filtering stopwords to evaluate substantive domain terms.

---

## 6. Verification & Automated Test Results

Executed automated test suites:
```powershell
pytest tests/ -v
```

### Test Summary:
- **`tests/test_api.py`**: 5 passed (health, readiness, providers list, ingest & query, WebSocket streaming).
- **`tests/test_providers.py`**: 7 passed (streaming adapter, OpenAI properties, Groq constraints, Ollama properties, OpenRouter fallback, local embedding, factory OCP).
- **`tests/test_rag_ingestion.py`**: 5 passed (metadata tagging in English/Hindi, chunker, TXT loader, CSV loader, Qdrant upserting).
- **`tests/test_rag_retrieval.py`**: 6 passed (HyDE expansion, BM25, RRF fusion, metadata boosting, pipeline retrieval, hallucination guard).

**Total: 23 passed in 18.83s (100% passing).**
