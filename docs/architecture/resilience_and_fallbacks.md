# Resilience, Circuit Breakers & Graceful Degradation Architecture

Fulfills Directive 6 and §7.1: Every external dependency, API call, and model inference in AgriSys must have a documented, tested fallback chain.

---

## 1. Disease Agent Fallback & Resilience Chains (Stage 2)

```
[Input Photo]
    │
    ▼
[Foliage Gatekeeper] ──(Ratio < 12% or Blurry)──► Early rejection with polite guidance
    │
    ▼
[Crop Detector Endpoint] ──(Timeout / Error)──► Farmer text hint fallback ──► Default "tomato"
    │
    ▼
[Crop Specialist Endpoint] ──(Timeout > 4.0s / 503 / 429)──► Universal Multi-Crop Endpoint
                                                                    │ (Timeout / Error)
                                                                    ▼
                                                       Deterministic Local Mock Fallback
    │
    ▼
[Visual Explainability] ──(Remote API: no tensor gradients)──► Adaptive Color-Space Lesion Heatmap
    │
    ▼
[RAG ICAR Treatment] ──(No exact match)──► General KVK / ICAR Extension Advisory
```

### Fallback Implementations in Stage 2:
1. **Plant Leaf Gatekeeper Fallback**: If an image is not a plant leaf or is too blurry, stops execution immediately and provides clear instructions on taking a good leaf photo, avoiding downstream model errors.
2. **Endpoint Timeout & Circuit Breaker**: `SecureModelEndpointClient` enforces a $4.0\text{s}$ timeout with retry limits. If the specialist endpoint fails, `CropModelRouter` automatically redirects inference to the `general_disease_detector`.
3. **Visual Explainability Dual Engine**: When models run over remote HTTP endpoints that do not return PyTorch gradients, `DiseaseGradCAM` automatically activates the color-space lesion segmentation engine, providing identical high-quality visual heatmaps.

---

## 2. Foundation & RAG Fallbacks (Stage 1)

1. **Vector Store Fallback**:
   - Primary: Remote Qdrant server (`http://localhost:6333`).
   - Fallback: Snappy in-memory Qdrant instance (`location=":memory:"`) if Docker container is offline.
2. **LLM Provider Fallback**:
   - OpenRouter: `default_model` automatically falls back to `fallback_model` upon rate limiting.
   - Offline Mode: Direct ICAR chunk synthesis if LLM provider is unconfigured.
3. **Embedding Fallback**:
   - Primary: `SentenceTransformer` local model.
   - Fallback: Deterministic normalized hash vector maintaining vocabulary overlap without requiring heavy checkpoint downloads.
4. **Hallucination Verification Fallback**:
   - Primary: Fast LLM judge executing `JUDGE_PROMPT`.
   - Fallback: High-precision lexical alignment judge filtering stopwords to evaluate substantive domain terms.
