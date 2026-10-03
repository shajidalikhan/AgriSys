"""Master LangGraph State schema for AgriSys multi-agent orchestration."""

from __future__ import annotations
import operator
from typing import Annotated, Any, Dict, List, TypedDict


class AgriSysState(TypedDict):
    """
    Unified state schema passed through LangGraph nodes.
    Uses operator.add to accumulate findings, RAG chunks, and citations across parallel agents.
    """
    # 1. Inputs
    query: str
    image_bytes: bytes | None
    image_path: str | None
    sensor_data: dict[str, Any] | None
    voice_audio_path: str | None
    audio_bytes: bytes | None
    generate_tts: bool
    language: str
    location: dict[str, Any] | None

    # 2. Session Context
    session_id: str
    turn_number: int
    history: list[dict[str, Any]]

    # 3. Dynamic Routing & Agent State
    intents: list[str]
    active_agents: list[str]
    active_crop: str | None

    # 4. Agent Accumulated Outputs (operator.add reducer)
    agent_results: Annotated[list[dict[str, Any]], operator.add]
    rag_chunks: Annotated[list[dict[str, Any]], operator.add]
    citations: Annotated[list[str], operator.add]

    # 5. Visual & Explainability Artifacts
    grad_cam_path: str | None
    shap_values: dict[str, Any] | None
    diagram_code: str | None
    diagram_type: str | None
    svg_schematic: str | None

    # 6. Structured Domain Payloads
    diagnostic_report: dict[str, Any] | None
    crop_data: dict[str, Any] | None
    nutrition_data: dict[str, Any] | None
    market_data: dict[str, Any] | None
    weather_data: dict[str, Any] | None
    web_search_data: dict[str, Any] | None

    # 7. Final Response & Quality Controls
    merged_response: str
    confidence_score: float
    hallucination_score: float
    escalate: bool
    tts_audio_path: str | None
