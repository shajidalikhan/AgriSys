"""FastAPI Application Shell for AgriSys.

Fulfills §1.4, §17.1, and Stage 1h:
- WebSocket endpoint: /ws/chat (streaming completions + sources + hallucination score)
- Health and status endpoints: /api/health, /api/health/ready, /api/providers
- REST query endpoint: /api/query
- Ingestion endpoint: /api/ingest/text
"""

from typing import Any, Dict, List, Optional
import json
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status, UploadFile, File, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agrisys.api.metrics import PrometheusMiddleware, metrics_collector
from agrisys.config import load_providers_config, load_rag_config, ProvidersConfig, RAGConfig
from agrisys.providers.factory import get_llm_provider, get_embedding_provider
from agrisys.rag.ingestion import IngestionPipeline, Document
from agrisys.rag.retrieval import RetrievalPipeline
from agrisys.rag.guard import HallucinationGuard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agrisys.api")

# Application singletons
providers_cfg: Optional[ProvidersConfig] = None
rag_cfg: Optional[RAGConfig] = None
ingestion_pipe: Optional[IngestionPipeline] = None
retrieval_pipe: Optional[RetrievalPipeline] = None
hallucination_guard: Optional[HallucinationGuard] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager initializing configurations, providers, and pipelines."""
    global providers_cfg, rag_cfg, ingestion_pipe, retrieval_pipe, hallucination_guard
    logger.info("Initializing AgriSys API...")

    try:
        providers_cfg = load_providers_config()
        rag_cfg = load_rag_config()

        # Initialize Embedding & LLM providers
        embed_prov = get_embedding_provider(
            providers_cfg.embedding.provider,
            model_name=providers_cfg.embedding.model,
            dimension=providers_cfg.embedding.dimension,
        )

        try:
            llm_prov = get_llm_provider(
                providers_cfg.llm.provider,
                model=providers_cfg.llm.model,
                api_key=providers_cfg.llm.api_key,
                temperature=providers_cfg.llm.temperature,
                max_tokens=providers_cfg.llm.max_tokens,
            )
        except Exception:
            # Fallback or mock provider for offline local testing
            llm_prov = None

        ingestion_pipe = IngestionPipeline(
            embedding_provider=embed_prov,
            chunk_size=rag_cfg.ingestion.chunk_size_tokens,
            chunk_overlap=rag_cfg.ingestion.chunk_overlap_tokens,
            collection_name=rag_cfg.vector_store.collection_name,
        )

        retrieval_pipe = RetrievalPipeline(
            embedding_provider=embed_prov,
            llm_provider=llm_prov,
            qdrant_client=ingestion_pipe.upserter.client,
            collection_name=rag_cfg.vector_store.collection_name,
            hyde_enabled=rag_cfg.retrieval.hyde_enabled,
            top_k_bm25=rag_cfg.retrieval.top_k_bm25,
            top_k_dense=rag_cfg.retrieval.top_k_dense,
            top_k_final=rag_cfg.retrieval.top_k_final,
        )

        hallucination_guard = HallucinationGuard(
            llm_provider=llm_prov,
            threshold=rag_cfg.guard.hallucination_score_threshold,
            escalate_webhook_url=rag_cfg.guard.escalate_webhook_url,
        )
        logger.info("AgriSys pipelines successfully initialized.")
    except Exception as e:
        logger.error("Error during startup initialization: %s", e)

    yield
    logger.info("Shutting down AgriSys API...")


app = FastAPI(
    title="AgriSys API",
    description="Multi-Agent Agricultural Expert System API Shell",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for React 18 frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics middleware (§18.3)
app.add_middleware(PrometheusMiddleware)

# Static audio artifact storage for playback (§11)
audio_dir = Path("data/artifacts/audio")
audio_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/audio", StaticFiles(directory=str(audio_dir)), name="audio")


# === Schemas ===

class QueryRequest(BaseModel):
    query: str = Field(..., json_schema_extra={"example": "How to treat early blight in tomato?"})
    crop: Optional[str] = Field(default=None, json_schema_extra={"example": "tomato"})
    state: Optional[str] = Field(default=None, json_schema_extra={"example": "UP"})
    domain: Optional[str] = Field(default=None, json_schema_extra={"example": "disease"})


class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    hallucination_score: float
    verdict: str
    unsupported_claims: List[str]


class IngestTextRequest(BaseModel):
    content: str = Field(..., description="Document content to index")
    source: str = Field(default="icar", json_schema_extra={"example": "icar"})
    crop: Optional[str] = Field(default=None, json_schema_extra={"example": "tomato"})
    state: Optional[str] = Field(default=None, json_schema_extra={"example": "UP"})
    domain: Optional[str] = Field(default="disease", json_schema_extra={"example": "disease"})


# === Health & Config Endpoints ===

@app.get("/api/health", summary="Health Check")
async def health_check():
    return {
        "status": "ok",
        "service": "AgriSys API",
        "version": "1.0.0",
        "stage": "Stage 1 (Foundation)",
    }


@app.get("/metrics", summary="Prometheus Metrics")
async def prometheus_metrics():
    """Prometheus exposition metrics scraping endpoint (§18.3)."""
    return Response(
        content=metrics_collector.generate_prometheus_output(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.get("/api/health/ready", summary="Readiness Probe")
async def readiness_probe():
    is_ready = retrieval_pipe is not None and ingestion_pipe is not None
    if not is_ready:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Pipelines not ready")
    return {"ready": True}


@app.get("/api/providers", summary="List Registered Providers")
async def list_providers():
    from agrisys.providers.factory import LLM_PROVIDER_REGISTRY, EMBEDDING_PROVIDER_REGISTRY
    return {
        "llm_providers": list(LLM_PROVIDER_REGISTRY.keys()),
        "embedding_providers": list(EMBEDDING_PROVIDER_REGISTRY.keys()),
        "active_llm": providers_cfg.llm.provider if providers_cfg else "not_loaded",
        "active_embedding": providers_cfg.embedding.provider if providers_cfg else "not_loaded",
    }


# === Ingestion Endpoint ===

@app.post("/api/ingest/text", summary="Ingest Raw Knowledge Text")
async def ingest_text(payload: IngestTextRequest):
    if not ingestion_pipe:
        raise HTTPException(status_code=500, detail="Ingestion pipeline not initialized")

    doc = Document(
        content=payload.content,
        metadata={
            "source": payload.source,
            "crop": payload.crop,
            "state": payload.state,
            "domain": payload.domain,
        },
    )
    chunks_count = await ingestion_pipe.ingest_document(doc)
    return {"status": "success", "indexed_chunks": chunks_count}


# === REST Query Endpoint ===

@app.post("/api/query", response_model=QueryResponse, summary="Query Agricultural Knowledge Base")
async def query_knowledge(req: QueryRequest):
    if not retrieval_pipe or not hallucination_guard:
        raise HTTPException(status_code=500, detail="Retrieval pipeline not initialized")

    # Step 1: Retrieve grounded knowledge
    filter_meta = {"crop": req.crop, "state": req.state, "domain": req.domain}
    chunks = await retrieval_pipe.retrieve(req.query, filter_metadata=filter_meta)

    source_texts = [c.text for c in chunks]
    sources_summary = [
        {"id": c.id, "text": c.text, "score": c.score, "metadata": c.metadata}
        for c in chunks
    ]

    # Step 2: Formulate Answer using LLM or structured summary
    context = "\n\n".join(f"[{i+1}] {t}" for i, t in enumerate(source_texts))
    prompt = f"""You are an ICAR agricultural expert advisor.
Answer the farmer's question using ONLY the provided verified context.
If the answer is not in the context, clearly advise consulting a local Krishi Vigyan Kendra.

CONTEXT:
{context}

FARMER QUESTION:
{req.query}

ADVISORY:"""

    answer_text = ""
    llm = retrieval_pipe.llm_provider
    if llm:
        try:
            answer_text = await llm.complete(
                [{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1024,
            )
        except Exception:
            answer_text = f"Based on ICAR guidelines: {source_texts[0]}" if source_texts else "No matching agricultural advisory found."
    else:
        answer_text = f"Based on ICAR guidelines: {source_texts[0]}" if source_texts else "No matching agricultural advisory found."

    # Step 3: Run Hallucination Guard
    verdict = await hallucination_guard.verify(answer_text, source_texts)

    return QueryResponse(
        answer=answer_text,
        sources=sources_summary,
        hallucination_score=verdict.score,
        verdict=verdict.verdict,
        unsupported_claims=verdict.unsupported_claims,
    )


# === Stage 3 Endpoints: Crop, Diagram, Orchestrator ===

from agrisys.agents.crop.models import CropInputFeatures, WhatIfSimulationRequest
from agrisys.agents.crop.agent import CropRecommendationAgent
from agrisys.agents.crop.simulator import CropSimulationService
from agrisys.agents.diagram.models import DiagramRequest
from agrisys.agents.diagram.agent import DiagramAgent
from agrisys.orchestrator.graph import create_agrisys_graph


@app.post("/api/crop/recommend", summary="Crop Recommendation with SHAP & Feasibility")
async def recommend_crop_endpoint(features: CropInputFeatures, language: str = "en"):
    """Recommends crops using weighted ensemble with SHAP TreeExplainer and feasibility checks."""
    try:
        agent = CropRecommendationAgent(rag_pipeline=retrieval_pipe)
        report = await agent.recommend(features=features, top_k=3, language=language)
        return report.model_dump()
    except Exception as e:
        logger.error(f"Crop recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/crop/simulate", summary="What-If Sensitivity Simulation")
async def simulate_crop_endpoint(request: WhatIfSimulationRequest):
    """Simulates perturbations in nutrients or climate parameters to observe recommendation shifts."""
    try:
        simulator = CropSimulationService()
        result = await simulator.simulate(request)
        return result.model_dump()
    except Exception as e:
        logger.error(f"Crop simulation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/diagram/generate", summary="Generate Mermaid / 2D SVG Agricultural Schematics")
async def generate_diagram_endpoint(request: DiagramRequest):
    """Generates workflows (Mermaid) or measured 2D SVG agricultural schematics."""
    try:
        llm = retrieval_pipe.llm_provider if retrieval_pipe else None
        agent = DiagramAgent(llm_provider=llm)
        output = await agent.generate_diagram(request)
        return output.model_dump()
    except Exception as e:
        logger.error(f"Diagram generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class OrchestrateRequest(BaseModel):
    query: str = "Suggest fertilizer dose for yellow leaves in tomato"
    sensor_data: Optional[Dict[str, Any]] = None
    voice_audio_path: Optional[str] = None
    generate_tts: bool = False
    language: str = "en"
    session_id: str = "default_session"


@app.post("/api/orchestrate", summary="LangGraph Multi-Agent Orchestrator")
async def orchestrate_endpoint(req: OrchestrateRequest):
    """Dispatches query through LangGraph StateGraph connecting Disease, Crop, Diagram, Nutrition, Market, Weather, Voice, and RAG."""
    try:
        graph = create_agrisys_graph()
        initial_state = {
            "query": req.query,
            "image_bytes": None,
            "image_path": None,
            "sensor_data": req.sensor_data,
            "voice_audio_path": req.voice_audio_path,
            "audio_bytes": None,
            "generate_tts": req.generate_tts,
            "language": req.language,
            "location": None,
            "session_id": req.session_id,
            "turn_number": 1,
            "history": [],
            "intents": [],
            "active_agents": [],
            "active_crop": None,
            "agent_results": [],
            "rag_chunks": [],
            "citations": [],
            "grad_cam_path": None,
            "shap_values": None,
            "diagram_code": None,
            "diagram_type": None,
            "svg_schematic": None,
            "diagnostic_report": None,
            "crop_data": None,
            "nutrition_data": None,
            "market_data": None,
            "weather_data": None,
            "merged_response": "",
            "confidence_score": 0.0,
            "hallucination_score": 1.0,
            "escalate": False,
            "tts_audio_path": None,
        }

        final_state = await graph.ainvoke(initial_state)
        return {
            "query": final_state.get("query"),
            "language": final_state.get("language"),
            "intents": final_state.get("intents"),
            "merged_response": final_state.get("merged_response"),
            "confidence_score": final_state.get("confidence_score"),
            "escalate": final_state.get("escalate"),
            "diagram_code": final_state.get("diagram_code"),
            "svg_schematic": final_state.get("svg_schematic"),
            "shap_values": final_state.get("shap_values"),
            "nutrition_data": final_state.get("nutrition_data"),
            "market_data": final_state.get("market_data"),
            "weather_data": final_state.get("weather_data"),
            "agent_results": final_state.get("agent_results"),
            "citations": final_state.get("citations"),
            "tts_audio_path": final_state.get("tts_audio_path"),
        }
    except Exception as e:
        logger.error(f"Orchestration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class NutritionDiagnoseRequest(BaseModel):
    crop: str = "Tomato"
    sensor_data: Optional[Dict[str, Any]] = None
    language: str = "en"


@app.post("/api/nutrition/diagnose", summary="Crop Nutrition Deficiency & Precision Fertilizer Dosing")
async def diagnose_nutrition_endpoint(req: NutritionDiagnoseRequest):
    """Diagnoses crop nutrient deficiencies and computes precision commercial fertilizer doses (Urea, DAP, MOP)."""
    try:
        from agrisys.agents.nutrition import NutritionAgent, SoilSensorReading
        sensor_obj = None
        if req.sensor_data:
            sensor_obj = SoilSensorReading(
                nitrogen=float(req.sensor_data.get("nitrogen", req.sensor_data.get("N", 240.0))),
                phosphorus=float(req.sensor_data.get("phosphorus", req.sensor_data.get("P", 14.0))),
                potassium=float(req.sensor_data.get("potassium", req.sensor_data.get("K", 150.0))),
                ph=float(req.sensor_data.get("ph", req.sensor_data.get("pH", 6.8))),
                electrical_conductivity=float(req.sensor_data.get("electrical_conductivity", req.sensor_data.get("ec", req.sensor_data.get("EC", 0.65)))),
                soil_moisture=float(req.sensor_data.get("soil_moisture", req.sensor_data.get("moisture", 45.0))),
            )
        agent = NutritionAgent()
        report = agent.diagnose(sensor_data=sensor_obj, crop=req.crop, language=req.language)
        return report.model_dump()
    except Exception as e:
        logger.error(f"Nutrition diagnosis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class MarketAdvisoryRequest(BaseModel):
    commodity: str = "Tomato"
    latitude: float = 26.8467
    longitude: float = 80.9462
    location_name: str = "Lucknow, Uttar Pradesh"
    language: str = "en"


@app.post("/api/market/advisory", summary="Mandi Market Price Intelligence & Sell/Hold Advisory")
async def market_advisory_endpoint(req: MarketAdvisoryRequest):
    """Generates APMC mandi price rankings, 7-day price trajectory, MSP comparison, and Sell/Hold advisory."""
    try:
        from agrisys.agents.market import MarketAgent
        agent = MarketAgent()
        report = await agent.advise(
            commodity=req.commodity,
            origin_lat=req.latitude,
            origin_lon=req.longitude,
            location_name=req.location_name,
            language=req.language,
        )
        return report.model_dump()
    except Exception as e:
        logger.error(f"Market advisory error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class WeatherForecastRequest(BaseModel):
    crop: str = "Wheat"
    crop_stage: str = "Mid"
    latitude: float = 26.8467
    longitude: float = 80.9462
    location_name: str = "Lucknow, Uttar Pradesh"
    language: str = "en"


@app.post("/api/weather/forecast", summary="Weather Forecast, FAO-56 ETo & Precision Irrigation")
async def weather_forecast_endpoint(req: WeatherForecastRequest):
    """Fetches 7-day meteorological forecast, calculates FAO-56 ETo, detects hazard alerts, and advises irrigation."""
    try:
        from agrisys.agents.weather import WeatherAgent
        agent = WeatherAgent()
        report = await agent.get_advisory(
            crop=req.crop,
            crop_stage=req.crop_stage,
            latitude=req.latitude,
            longitude=req.longitude,
            location_name=req.location_name,
            language=req.language,
        )
        return report.model_dump()
    except Exception as e:
        logger.error(f"Weather advisory error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === Voice Pipeline Endpoints (§11) ===

class SynthesizeSpeechRequest(BaseModel):
    text: str = Field(..., json_schema_extra={"example": "यूरिया 50 किलोग्राम प्रति एकड़ डालें।"})
    language: str = Field(default="hi", json_schema_extra={"example": "hi"})
    speed: float = Field(default=1.0)


@app.post("/api/voice/transcribe", summary="Transcribe Multilingual Spoken Audio")
async def voice_transcribe_endpoint(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
):
    """
    Transcribes farmer speech in Hindi, Marathi, Telugu, Tamil, or English with Indic text normalization.
    Returns normalized text, detected language, and saved audio artifact path.
    """
    try:
        from agrisys.voice.pipeline import VoicePipeline
        audio_bytes = await file.read()
        pipeline = VoicePipeline()
        result, saved_path = await pipeline.process_incoming_audio(
            audio_bytes=audio_bytes,
            language=language if language and language != "auto" else None,
            filename=file.filename or "recording.wav",
        )
        return {
            "raw_transcript": result.raw_transcript,
            "normalized_transcript": result.normalized_transcript,
            "detected_language": result.detected_language,
            "confidence": result.confidence,
            "duration_seconds": result.duration_seconds,
            "audio_path": saved_path,
        }
    except Exception as e:
        logger.error(f"Voice transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/voice/synthesize", summary="Synthesize Indic Speech from Advisory Text")
async def voice_synthesize_endpoint(req: SynthesizeSpeechRequest):
    """
    Synthesizes natural agricultural voice response in Indic languages.
    Returns audio artifact path, web-accessible URL, and metadata.
    """
    try:
        from agrisys.voice.pipeline import VoicePipeline
        pipeline = VoicePipeline()
        result = await pipeline.generate_speech_response(
            text=req.text,
            language=req.language,
            speed=req.speed,
        )
        return result.model_dump()
    except Exception as e:
        logger.error(f"Voice synthesis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === WebSocket Streaming Chat Endpoint ===


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint streaming LLM response tokens, sources, and guard verdict."""
    await websocket.accept()
    logger.info("WebSocket client connected")

    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                query = payload.get("message", "").strip()
            except json.JSONDecodeError:
                query = data.strip()

            if not query:
                continue

            # Notify UI that retrieval is starting
            await websocket.send_json({"type": "status", "stage": "retrieving_knowledge"})

            chunks = await retrieval_pipe.retrieve(query) if retrieval_pipe else []
            source_texts = [c.text for c in chunks]

            # Send retrieved sources to frontend
            await websocket.send_json({
                "type": "sources",
                "sources": [{"id": c.id, "text": c.text, "metadata": c.metadata, "score": c.score} for c in chunks],
            })

            # Stream response tokens
            await websocket.send_json({"type": "status", "stage": "generating_advisory"})

            context = "\n\n".join(f"[{i+1}] {t}" for i, t in enumerate(source_texts))
            system_prompt = f"You are AgriSys, an agricultural expert AI. Ground your advice in this context:\n{context}"
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query},
            ]

            full_answer = ""
            llm = retrieval_pipe.llm_provider if retrieval_pipe else None
            if llm:
                try:
                    async for token in llm.stream(messages):
                        full_answer += token
                        await websocket.send_json({"type": "token", "content": token})
                except Exception:
                    fallback_text = f"Advisory based on ICAR sources: {source_texts[0]}" if source_texts else "Please contact local Krishi Vigyan Kendra."
                    full_answer = fallback_text
                    await websocket.send_json({"type": "token", "content": fallback_text})
            else:
                fallback_text = f"Advisory based on ICAR sources: {source_texts[0]}" if source_texts else "No matching agricultural advisory found."
                full_answer = fallback_text
                await websocket.send_json({"type": "token", "content": fallback_text})

            # Run Hallucination Guard
            if hallucination_guard:
                verdict = await hallucination_guard.verify(full_answer, source_texts)
                await websocket.send_json({
                    "type": "guard",
                    "score": verdict.score,
                    "verdict": verdict.verdict,
                    "unsupported_claims": verdict.unsupported_claims,
                })

            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
