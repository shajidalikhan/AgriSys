# AgriSys Modules & Class Reference

This file documents all modules, interfaces, and primary classes created in AgriSys across stages.

---

## 1. Provider Abstraction Layer (`agrisys.providers`)

- **`BaseLLMProvider`** (`agrisys/providers/base.py`):
  - `complete(messages: List[Dict], **kwargs) -> str`: Non-streaming LLM response.
  - `stream(messages: List[Dict], **kwargs) -> AsyncIterator[str]`: Token streaming.
  - `supports_vision -> bool`: True if model natively accepts image inputs.
  - `context_window -> int`: Token context window size.
- **`BaseEmbeddingProvider`** (`agrisys/providers/base.py`):
  - `embed_query(text: str) -> List[float]`: Single query vector.
  - `embed_documents(texts: List[str]) -> List[List[float]]`: Batch document vectors.
  - `dimension -> int`: Output vector dimensionality.
- **`StreamingAdapter`** (`agrisys/providers/base.py`): Chunk streaming simulator for non-streaming models.
- **`OpenAIProvider`** (`agrisys/providers/openai_provider.py`): OpenAI GPT-4o/5.5 and `text-embedding-3-large`.
- **`GroqProvider`** (`agrisys/providers/groq_provider.py`): Ultra-fast inference via Groq Cloud API with SSE streaming.
- **`OllamaProvider`** (`agrisys/providers/ollama_provider.py`): Local offline LLM and embeddings client.
- **`OpenRouterProvider`** (`agrisys/providers/openrouter_provider.py`): Gateway with automatic secondary model fallback.
- **`LocalEmbeddingProvider`** (`agrisys/providers/local_embedding.py`): Self-hosted / local deterministic embedding provider.
- **`factory`** (`agrisys/providers/factory.py`): Provider registries and DIP factories (`get_llm_provider`, `get_embedding_provider`, `register_llm_provider`, `register_embedding_provider`).

---

## 2. Configuration (`agrisys.config`)

- **`load_providers_config(path) -> ProvidersConfig`**: Reads `config/providers.yaml` with environment variable interpolation.
- **`load_rag_config(path) -> RAGConfig`**: Reads `config/rag.yaml` with environment variable interpolation.
- **Schemas**: `LLMConfig`, `EmbeddingConfig`, `VisionConfig`, `HallucinationGuardConfig`, `IngestionConfig`, `VectorStoreConfig`, `RetrievalConfig`, `GuardConfig`.

---

## 3. RAG Infrastructure (`agrisys.rag`)

- **`Document`**, **`Chunk`**, **`ChunkMetadata`** (`models.py`).
- **`DocumentLoader`** (`loaders.py`): Supports PDF, HTML, CSV, and TXT.
- **`SemanticChunker`** (`chunker.py`): Splits on paragraph/sentence boundaries (512 tokens / 128 overlap).
- **`MetadataTagger`** (`tagger.py`): English and Hindi crop/domain classifier.
- **`QdrantUpserter`** (`upserter.py`): Creates collections and batch upserts points into Qdrant.
- **`IngestionPipeline`** (`pipeline.py`): End-to-end ingestion coordinator.
- **`HyDEExpander`** (`hyde.py`): Generates hypothetical ICAR/FAO document passages.
- **`BM25Retriever`** (`bm25.py`): Sparse BM25Okapi keyword index.
- **`ReciprocalRankFusion`** (`rrf.py`): Merges ranked lists via $RRF(d) = \sum \frac{1}{60 + \text{rank}}$.
- **`CrossEncoderReranker`** (`reranker.py`): Query-passage cross-attention reranking.
- **`MMRDiversityFilter`** (`mmr.py`): Maximal Marginal Relevance selection to eliminate redundancy.
- **`MetadataBooster`** (`mmr.py`): Applies score bonuses for matching crop, state, or domain.
- **`RetrievalPipeline`** (`pipeline.py`): Master hybrid retrieval coordinator.
- **`HallucinationGuard`** (`guard.py`): Fast LLM judge scoring factual alignment with stopword-filtered lexical fallback.

---

## 4. Disease Diagnostic Agent (`agrisys.agents.disease`)

- **`GatekeeperResult`**, **`CropDetectionResult`**, **`DiseasePrediction`**, **`DiseaseDiagnosticReport`** (`models.py`).
- **`ImagePreprocessor`** (`preprocessor.py`): Format check, blur detection, leaf gatekeeper, EXIF stripper, CLAHE contrast enhancement in LAB space, and dual bytes/tensor output.
- **`SecureModelEndpointClient`** (`client.py`): Secure HTTP/REST client for HuggingFace / local endpoints with Bearer auth, PlantVillage label parsing, and circuit breaker.
- **`BaseDiseaseModelTool`** & **`EndpointDiseaseModelTool`** (`registry.py`): Modular tool abstraction for disease models.
- **`MODEL_REGISTRY`** (`registry.py`): Pluggable catalog of crop detection, specialist, and universal disease model tools.
- **`CropDetector`** (`crop_detector.py`): Dedicated crop identification with user text hint consensus resolver.
- **`WeightedEnsembleVoter`** (`ensemble.py`): Accuracy-weighted majority voting and quantitative severity level mapper (0 to 5).
- **`CropModelRouter`** (`model_router.py`): Routes detected crop to specialist tools with automatic universal fallback.
- **`AgriChainDiagnosticEngine`** (`chain.py`): CoT reasoning engine querying Stage 1 RAG for ICAR/FAO treatment protocols.
- **`DiseaseGradCAM`** (`agrisys/xai/gradcam.py`): Dual explainability (tensor Grad-CAM for local models and adaptive color-space lesion heatmap with bounding boxes for API models).
- **`DiseaseAgent`** & **`disease_agent_node`** (`node.py`): Master diagnostic agent and LangGraph state node.

---

## 5. Crop Recommendation Agent (`agrisys.agents.crop`)

- **`CropInputFeatures`**, **`CropRecommendation`**, **`CropRecommendationOutput`**, **`WhatIfSimulationResult`** (`models.py`): Pydantic v2 schemas.
- **`BaseCropModelTool`** (`registry.py`): Abstract interface for crop recommendation models.
- **`CROP_MODEL_REGISTRY`** (`registry.py`): Pluggable catalog for crop models (`LocalXGBoostCropModelTool`, `LocalRandomForestCropModelTool`, `EndpointCropModelTool`).
- **`LocalXGBoostCropModelTool`** (`xgb_tool.py`): Gradient-boosted multi-class tree inference.
- **`LocalRandomForestCropModelTool`** (`rf_tool.py`): Bagging decision tree inference for high noise tolerance.
- **`EndpointCropModelTool`** (`endpoint_tool.py`): Bearer token authenticated remote model client with circuit breaker.
- **`CropEnsembleVoter`** (`ensemble.py`): Weighted probability voter combining XGBoost and Random Forest.
- **`CropFeasibilityGuard`** (`feasibility_guard.py`): Agronomic validator for seasonality (Kharif/Rabi/Zaid), water source compatibility, and soil pH boundaries.
- **`CropSimulationService`** (`simulator.py`): Real-time What-If sensitivity perturbation analyzer.
- **`CropRecommendationAgent`** (`agent.py`): Master coordinator enriching top crops with Stage 1 RAG ICAR Package of Practices.
- **`crop_agent_node`** (`node.py`): LangGraph state node.

---

## 6. Visual Diagramming Agent (`agrisys.agents.diagram`)

- **`DiagramRequest`**, **`DiagramOutput`**, **`VisualType`** (`models.py`): Schemas for diagram requests and outputs.
- **`BaseVisualEngine`** (`engines/base.py`): Interface for visual rendering engines.
- **`MermaidEngine`** (`engines/mermaid_engine.py`): Generates Mermaid.js workflows, IPM trees, sowing calendars (`gantt`), and timelines.
- **`SvgSchematicEngine`** (`engines/svg_schematic_engine.py`): Parametric 2D vector schematic builder for measured planting spacing grids, drip irrigation layouts, raised bed cross-sections, canopy pruning guides, and trap grids.
- **`SelfHealingSyntaxLinter`** (`sanitizer.py`): Validates Mermaid and SVG XML DOM; auto-repairs unescaped characters and malformed tags.
- **`BilingualLabelInjector`** (`translator.py`): Translates and formats annotations in Hindi + English.
- **`DiagramAgent`** (`agent.py`): Master visual diagramming agent.
- **`diagram_agent_node`** (`node.py`): LangGraph state node.

---

## 7. Explainable AI Layer — SHAP (`agrisys.xai`)

- **`CropSHAPExplainer`** (`shap_explainer.py`): TreeExplainer for crop model ensembles, bilingual Hindi/English feature labels, positive drivers vs limiting factors, and algorithmic margin contribution fallback.

---

## 8. LangGraph Orchestrator (`agrisys.orchestrator`)

- **`AgriSysState`** (`state.py`): Master TypedDict with `operator.add` reducers for multi-agent results, RAG chunks, and citations.
- **`IntentRouter`** (`intent_router.py`): Three-tier hybrid intent classifier (regex keyword matcher + LLM structured classification + BERT hook).
- **`ResponseMerger`** (`response_merger.py`): Synthesizes multi-agent findings into a cohesive farmer advisory with citations and confidence scoring.
- **`SessionMemoryManager`** (`memory.py`): Thread-safe in-memory session store with Redis adapter hook.
- **`create_agrisys_graph`** & **`compiled_graph`** (`graph.py`): LangGraph StateGraph compiling Disease, Crop, Diagram, Nutrition, Market, Weather, RAG, and Guard nodes.

---

## 9. Nutrition Deficiency Agent (`agrisys.agents.nutrition`)

- **`SoilSensorReading`**, **`DeficiencyPrediction`**, **`FertilizerDoseRecommendation`**, **`NutritionReport`** (`models.py`): Pydantic v2 schemas.
- **`ResNet50FeatureExtractor`** (`fusion_model.py`): 2048-dimensional visual feature extractor from leaf imagery.
- **`SensorNormalizer`** (`fusion_model.py`): Normalizes continuous 6-channel soil sensors ($N, P, K, pH, EC, \text{moisture}$) to $[0, 1]$.
- **`CrossModalNutritionFusionNet`** (`fusion_model.py`): PyTorch cross-modal network ($2054 \to 512 \to 128 \to 64$) with dual prediction heads (12 deficiency classes and 3 continuous NPK doses).
- **`SoilHealthCardEvaluator`** (`shc_rules.py`): ICAR Soil Health Card rating evaluator and commercial fertilizer calculator (Urea, DAP, MOP per ha and per acre).
- **`NutritionAgent`** (`agent.py`): Master agent coordinating preprocessing, multimodal fusion inference, and bilingual farmer advisory generation.
- **`nutrition_agent_node`** (`node.py`): LangGraph state node.

---

## 10. Market Price Intelligence Agent (`agrisys.agents.market`)

- **`MandiRecord`**, **`PriceForecastPoint`**, **`MSPComparison`**, **`MarketAdvisoryReport`** (`models.py`): Pydantic v2 schemas.
- **`CACP_MSP_DATABASE`** & **`compare_msp`** (`msp_database.py`): Benchmark MSP evaluation for 13+ mandatory commodities.
- **`IQRAnomalyFilter`** (`anomaly_filter.py`): Interquartile range outlier rejection for reported mandi transactions.
- **`haversine_distance`** & **`HaversineMandiRanker`** (`haversine_ranker.py`): Geodesic distance calculation and net profit mandi ranking after freight logistics.
- **`BasePriceForecaster`**, **`StatisticalPriceForecaster`**, **`ProphetPriceForecaster`** (`forecaster.py`): 7-day multi-day modal price trajectory forecaster with weekly seasonality.
- **`MandiDataClient`** (`data_client.py`): Agmarknet/eNAM client with 10-minute Redis caching and in-memory TTL fallback.
- **`MarketAgent`** (`agent.py`): Master agent coordinating mandi intelligence and Sell/Hold advisories.
- **`market_agent_node`** (`node.py`): LangGraph state node.

---

## 11. Weather & Precision Irrigation Agent (`agrisys.agents.weather`)

- **`DailyWeatherForecast`**, **`EToCalculationResult`**, **`WeatherAlert`**, **`WeatherReport`** (`models.py`): Pydantic v2 schemas.
- **`FAO56PenmanMonteithCalculator`** (`eto_calculator.py`): Standardized FAO-56 Penman-Monteith reference evapotranspiration ($ET_0$) and crop demand ($ET_c$) with $K_c$ coefficients for 15+ crops.
- **`WeatherAlertEngine`** (`alerts.py`): Hazard detector for frost, heatwaves, heavy downpours, and gale-force lodging winds.
- **`WeatherClient`** (`client.py`): 4-tier meteorological fallback client (IMD $\to$ Open-Meteo $\to$ Redis Cache $\to$ Offline Baseline).
- **`WeatherAgent`** (`agent.py`): Master agent coordinating forecasts, irrigation runtimes, and bilingual advisories.
- **`weather_agent_node`** (`node.py`): LangGraph state node.

---

## 12. Multilingual Voice Pipeline (`agrisys.voice`)

- **`TranscriptionResult`**, **`SynthesisResult`**, **`AudioMetadata`** (`models.py`): Pydantic v2 schemas for vernacular voice processing and audio artifacts.
- **`IndicTextNormalizer`** (`normalizer.py`): Unicode NFC canonicalization, ZWNJ/ZWJ stripping, Devanagari digit conversion, danda punctuation normalization, and agricultural abbreviation expansion.
- **`IndicLanguageDetector`** (`normalizer.py`): Multi-script range classifier detecting 9+ Indian languages and English with distinctive Marathi Devanagari discrimination.
- **`AudioStorageManager`** (`storage.py`): Disk audio persistence with UUID tracking and duration calculation via standard Python `wave`.
- **`BaseASRProvider`**, **`WhisperASRProvider`**, **`BhashiniASRProvider`**, **`MockASRProvider`**, **`ASRProviderFactory`** (`asr.py`): Pluggable Automated Speech Recognition provider layer.
- **`BaseTTSProvider`**, **`OpenAITTSProvider`**, **`BhashiniTTSProvider`**, **`MockTTSProvider`**, **`TTSProviderFactory`** (`tts.py`): Pluggable Text-to-Speech synthesis layer producing standardized 16kHz mono audio.
- **`VoicePipeline`** (`pipeline.py`): Master coordinator executing incoming microphone processing, normalization, and spoken speech generation.
- **`voice_processor_node`** & **`tts_generator_node`** (`node.py`): LangGraph state nodes for voice input transcription and speech advisory output synthesis.
- **`scripts/training/finetune_whisper.py`**: HuggingFace Transformers LoRA fine-tuning script for agricultural vernacular speech.

---

## 13. Frontend Web Application & PWA (`frontend/`)

- **`Navbar`** (`src/components/layout/Navbar.jsx`): Top navigation bar with branding, real-time backend health status indicator, and multilingual language selector.
- **`Sidebar`** (`src/components/layout/Sidebar.jsx`): Vertical navigation bar across all 6 specialist agent workspaces.
- **`StreamingChat`** (`src/components/chat/StreamingChat.jsx`): WebSocket streaming advisory chat with token animations, grounded source chips, and Hallucination Guard score badge.
- **`DiseasePanel`** (`src/components/disease/DiseasePanel.jsx`): Leaf image drag & drop uploader, Grad-CAM visual heatmap toggle, and structured IPM chemical & bio-control treatment cards.
- **`NutritionPanel`** (`src/components/nutrition/NutritionPanel.jsx`): Interactive Soil Health Card sliders (N, P, K, pH) and precision commercial fertilizer dosing (Urea, DAP, MOP per acre/ha).
- **`MarketPanel`** (`src/components/market/MarketPanel.jsx`): APMC mandi net profit ranking, 7-day Recharts price trajectory with MSP floor comparison, and Sell vs Hold recommendation.
- **`WeatherPanel`** (`src/components/weather/WeatherPanel.jsx`): 7-day meteorological forecast cards, extreme weather hazard banners, and FAO-56 Penman-Monteith precision irrigation drip runtime calculator.
- **`VoiceStudio`** (`src/components/voice/VoiceStudio.jsx`): Vernacular microphone recorder with live waveform pulses, Indic ASR transcription, and neural TTS voice playback.
- **`LanguageContext`** (`src/context/LanguageContext.jsx`): Bilingual & vernacular translations for English, Hindi, Marathi, Telugu, and Tamil.
- **`API & WebSocket Clients`** (`src/api/client.js`, `src/api/websocket.js`): REST client connecting to FastAPI backend and WebSocket client connecting to `/ws/chat`.
- **`PWA Manifest & Service Worker`** (`public/manifest.json`, `public/sw.js`): Standalone mobile installation support and offline asset caching.

---

## 14. Production Deployment, CI/CD & Monitoring (`agrisys.api.metrics`, Docker, CI/CD)

- **`MetricsCollector`** & **`PrometheusMiddleware`** (`agrisys/api/metrics.py`): In-memory metric aggregator and FastAPI middleware tracking requests, durations, agent invocations, and hallucination scores.
- **`GET /metrics`** (`agrisys/api/main.py`): Prometheus exposition endpoint for scraping.
- **`config/prometheus.yml`**: Prometheus scrape configuration targeting `api:8000` with 15s interval.
- **`frontend/Dockerfile`** & **`frontend/nginx.conf`**: Multi-stage Node.js build $\to$ Nginx Alpine reverse proxy container for production React PWA.
- **`docker-compose.yml`**: 8-service production topology: `api`, `frontend`, `qdrant`, `redis`, `postgres`, `minio`, `langfuse`, `prometheus`, `grafana`.
- **`.github/workflows/ci.yml`**: GitHub Actions automated pipeline executing Python 3.12 test suite, Node 22 frontend build, and Docker compose configuration linting.

