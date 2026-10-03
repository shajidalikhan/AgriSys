# SOLID Architecture Principles Compliance Matrix

This document records how each module, class, and agent in AgriSys adheres to the five SOLID principles (§1.2).

---

## 1. Single Responsibility Principle (SRP)
*Each class or module does exactly one thing and has only one reason to change.*

| Component | Single Responsibility |
| :--- | :--- |
| `BaseLLMProvider` | Provides LLM completions and token streaming only. Does not handle vector storage or prompts. |
| `BaseEmbeddingProvider` | Generates dense embeddings only. |
| `DocumentLoader` | Extracts text and raw metadata from physical file formats (PDF, HTML, CSV, TXT). |
| `SemanticChunker` | Chunks text on paragraph and sentence boundaries with token constraints. |
| `MetadataTagger` | Classifies agronomic metadata (crop, state, domain, language). |
| `QdrantUpserter` | Interfaces with Qdrant collection for indexing vectors. |
| `HallucinationGuard` | Evaluates factual alignment of responses against retrieved sources. |
| `ImagePreprocessor` | Validates image format, checks blur, runs leaf gatekeeping, and applies CLAHE enhancement. |
| `CropDetector` | Identifies the crop type and resolves text/vision consensus. |
| `CropModelRouter` | Dispatches image inference to crop-specific or general model endpoints. |
| `WeightedEnsembleVoter` | Combines multi-model predictions via weighted majority voting and computes severity grade. |
| `DiseaseGradCAM` | Generates visual explainability heatmaps and bounding boxes only. |
| `AgriChainDiagnosticEngine` | Synthesizes agronomic diagnostic reports and retrieves RAG treatment protocols. |
| `disease_agent_node` | Single LangGraph node function interfacing with state dictionary. |

---

## 2. Open/Closed Principle (OCP)
*Open for extension, closed for modification.*

- **LLM Providers**: Adding a new provider (e.g. Anthropic, Mistral, Gemini) is achieved by subclassing `BaseLLMProvider` and calling `register_llm_provider("name", cls)`. No existing provider code or agent logic is modified.
- **Disease Model Tools**: Adding a new vision model (whether a new HuggingFace Hub model or custom local container endpoint) is achieved by adding a single dictionary entry to `MODEL_REGISTRY` in `registry.py` or calling `register_disease_tool("name", tool)`. The `CropModelRouter` dynamically discovers and routes to it.

---

## 3. Liskov Substitution Principle (LSP)
*Subtypes must be substitutable for their base types without altering system correctness.*

- Any `BaseLLMProvider` subclass (`OpenAIProvider`, `GroqProvider`, `OllamaProvider`, `OpenRouterProvider`) can replace any other without breaking callers.
- Any `BaseDiseaseModelTool` subclass (`EndpointDiseaseModelTool`, custom tools) can be substituted in `MODEL_REGISTRY`. The `CropModelRouter` and `WeightedEnsembleVoter` interact with the uniform `predict()` interface.

---

## 4. Interface Segregation Principle (ISP)
*Clients should not be forced to depend on methods they do not use. No fat interfaces.*

- `BaseLLMProvider` and `BaseEmbeddingProvider` are cleanly separated. Embedding models do not have to implement chat completion methods.
- `BaseDiseaseModelTool` exposes only `name`, `crops_supported`, `role`, `weight`, and `predict()`. It does not force vision models to know about RAG, prompts, or LangGraph state.

---

## 5. Dependency Inversion Principle (DIP)
*High-level modules do not depend on low-level modules. Both depend on abstractions.*

- `RetrievalPipeline` and `IngestionPipeline` depend on `BaseEmbeddingProvider` and `BaseLLMProvider` abstractions, injected via constructors.
- `AgriChainDiagnosticEngine` and `DiseaseAgent` depend on `RetrievalPipeline` and `BaseDiseaseModelTool` abstractions, never on concrete vendor SDKs or specific database drivers.
