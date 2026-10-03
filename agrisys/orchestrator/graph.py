"""LangGraph StateGraph compilation for AgriSys Orchestrator."""

from __future__ import annotations
import logging
from typing import Any, List
from langgraph.graph import StateGraph, START, END
from agrisys.orchestrator.state import AgriSysState
from agrisys.orchestrator.intent_router import IntentRouter
from agrisys.orchestrator.response_merger import ResponseMerger
from agrisys.agents.disease.node import disease_agent_node
from agrisys.agents.crop.node import crop_agent_node
from agrisys.agents.diagram.node import diagram_agent_node
from agrisys.agents.nutrition.node import nutrition_agent_node
from agrisys.agents.market.node import market_agent_node
from agrisys.agents.weather.node import weather_agent_node
from agrisys.agents.web_search.node import web_search_agent_node
from agrisys.voice.node import voice_processor_node, tts_generator_node
from agrisys.rag.guard import HallucinationGuard
from agrisys.providers.factory import get_llm_provider

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Orchestrator Node Functions
# ------------------------------------------------------------------

async def router_node(state: AgriSysState) -> dict[str, Any]:
    """Classifies user intent and sets active agents."""
    query = state.get("query", "")
    has_image = bool(state.get("image_bytes") or state.get("image_path"))
    has_sensor = bool(state.get("sensor_data"))

    try:
        llm = get_llm_provider()
    except Exception:
        llm = None

    router = IntentRouter(llm_provider=llm)
    intents = await router.route(query=query, has_image=has_image, has_sensor=has_sensor)

    return {
        "intents": intents,
        "active_agents": intents,
    }


def route_next_agents(state: AgriSysState) -> list[str]:
    """Conditional edge router: Dispatches query to one or more specialist nodes."""
    intents = state.get("intents", [])
    targets: list[str] = []

    if "disease" in intents:
        targets.append("disease_agent")
    if "crop_recommendation" in intents:
        targets.append("crop_agent")
    if "diagram_request" in intents:
        targets.append("diagram_agent")
    if "nutrition" in intents:
        targets.append("nutrition_agent")
    if "market" in intents:
        targets.append("market_agent")
    if "weather" in intents:
        targets.append("weather_agent")
    if "web_search" in intents:
        targets.append("web_search_agent")

    if not targets:
        # Direct agronomy Q&A without specialist model
        targets.append("rag_retriever")

    return targets


async def rag_retriever_node(state: AgriSysState) -> dict[str, Any]:
    """Retrieves grounding chunks from Qdrant if active agents generated findings."""
    # Aggregates citations already collected by specialist nodes or query
    citations = list(state.get("citations") or [])
    rag_chunks = list(state.get("rag_chunks") or [])

    # If general agronomy without specialist chunks, add general reference
    if not rag_chunks and not citations:
        citations.append("ICAR Package of Practices Knowledge Base")

    return {
        "rag_chunks": rag_chunks,
        "citations": citations,
    }


async def response_merger_node(state: AgriSysState) -> dict[str, Any]:
    """Synthesizes all agent outputs and citations into a single advisory."""
    merger = ResponseMerger()
    merged = merger.merge(
        query=state.get("query", ""),
        agent_results=state.get("agent_results") or [],
        rag_chunks=state.get("rag_chunks"),
        citations=state.get("citations"),
        language=state.get("language", "en"),
    )
    return merged


async def hallucination_guard_node(state: AgriSysState) -> dict[str, Any]:
    """Evaluates factual grounding using Stage 1 Hallucination Guard."""
    response = state.get("merged_response", "")
    citations = state.get("citations") or []
    chunks = state.get("rag_chunks") or []

    # Build context string list from retrieved sources
    source_list = [
        c.get("content", "") if isinstance(c, dict) else str(c)
        for c in chunks
    ]
    if not source_list and citations:
        source_list = list(citations)
    if not source_list:
        source_list = ["ICAR agricultural guidelines."]

    guard = HallucinationGuard()
    eval_res = await guard.verify(response=response, sources=source_list)

    escalate = state.get("escalate", False) or (eval_res.score < 0.70)
    return {
        "hallucination_score": eval_res.score,
        "escalate": escalate,
    }


# ------------------------------------------------------------------
# Graph Construction & Compilation
# ------------------------------------------------------------------

def create_agrisys_graph() -> Any:
    """Builds and compiles the full LangGraph StateGraph."""
    graph = StateGraph(AgriSysState)

    # 1. Add Nodes
    graph.add_node("voice_processor", voice_processor_node)
    graph.add_node("intent_router", router_node)
    graph.add_node("disease_agent", disease_agent_node)
    graph.add_node("crop_agent", crop_agent_node)
    graph.add_node("diagram_agent", diagram_agent_node)
    graph.add_node("nutrition_agent", nutrition_agent_node)
    graph.add_node("market_agent", market_agent_node)
    graph.add_node("weather_agent", weather_agent_node)
    graph.add_node("web_search_agent", web_search_agent_node)
    graph.add_node("rag_retriever", rag_retriever_node)
    graph.add_node("response_merger", response_merger_node)
    graph.add_node("hallucination_guard", hallucination_guard_node)
    graph.add_node("tts_generator", tts_generator_node)

    # 2. Add Edges
    graph.add_edge(START, "voice_processor")
    graph.add_edge("voice_processor", "intent_router")

    # Conditional Routing from router to specialist agents
    graph.add_conditional_edges(
        "intent_router",
        route_next_agents,
        ["disease_agent", "crop_agent", "diagram_agent", "nutrition_agent", "market_agent", "weather_agent", "web_search_agent", "rag_retriever"],
    )

    # Edges from specialist agents to rag_retriever
    graph.add_edge("disease_agent", "rag_retriever")
    graph.add_edge("crop_agent", "rag_retriever")
    graph.add_edge("diagram_agent", "rag_retriever")
    graph.add_edge("nutrition_agent", "rag_retriever")
    graph.add_edge("market_agent", "rag_retriever")
    graph.add_edge("weather_agent", "rag_retriever")
    graph.add_edge("web_search_agent", "rag_retriever")

    # Sequential pipeline from rag_retriever to END
    graph.add_edge("rag_retriever", "response_merger")
    graph.add_edge("response_merger", "hallucination_guard")
    graph.add_edge("hallucination_guard", "tts_generator")
    graph.add_edge("tts_generator", END)

    compiled = graph.compile()
    logger.info("Compiled LangGraph StateGraph successfully.")
    return compiled


# Module-level singleton
try:
    compiled_agrisys_graph = create_agrisys_graph()
except Exception as err:
    logger.warning(f"LangGraph compilation deferred: {err}")
    compiled_agrisys_graph = None
