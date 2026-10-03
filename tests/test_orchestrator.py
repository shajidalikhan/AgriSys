"""Unit and integration tests for LangGraph Orchestrator and StateGraph."""

import pytest
from agrisys.orchestrator.state import AgriSysState
from agrisys.orchestrator.intent_router import IntentRouter
from agrisys.orchestrator.response_merger import ResponseMerger
from agrisys.orchestrator.memory import SessionMemoryManager
from agrisys.orchestrator.graph import create_agrisys_graph


@pytest.mark.asyncio
async def test_intent_router_classification():
    """Test IntentRouter for single, compound, and multimodal triggers."""
    router = IntentRouter()

    # 1. Single intent: disease
    intents1 = await router.route("my tomato leaf has yellow spots and blight")
    assert "disease" in intents1

    # 2. Single intent: crop recommendation
    intents2 = await router.route("which crop should I plant in kharif season?")
    assert "crop_recommendation" in intents2

    # 3. Single intent: diagram
    intents3 = await router.route("show me drip irrigation layout diagram")
    assert "diagram_request" in intents3

    # 4. Compound intent: crop + diagram
    intents4 = await router.route("recommend crop for black soil and show spacing layout diagram")
    assert "crop_recommendation" in intents4
    assert "diagram_request" in intents4

    # 5. Multimodal implicit trigger
    intents5 = await router.route("check this out", has_image=True)
    assert "disease" in intents5


def test_response_merger_synthesis():
    """Test merging results from multiple agents with confidence aggregation."""
    merger = ResponseMerger()
    agent_results = [
        {
            "agent": "crop_agent",
            "winning_crop": "rice",
            "confidence": 0.92,
            "top_3": [("rice", 0.92), ("maize", 0.08)],
            "advisory": "Rice is optimal for water-logged alluvial soil.",
        },
        {
            "agent": "diagram_agent",
            "visual_type": "planting_spacing",
            "engine": "svg_2d",
            "caption": "Planting layout for rice (20cm x 15cm).",
        }
    ]
    citations = ["ICAR Package of Practices - Rice (2024)"]

    res = merger.merge(
        query="recommend crop and layout",
        agent_results=agent_results,
        citations=citations,
    )
    assert "Rice" in res["merged_response"]
    assert "Planting layout" in res["merged_response"]
    assert "ICAR Package of Practices" in res["merged_response"]
    assert res["confidence_score"] >= 0.85
    assert res["escalate"] is False


def test_session_memory_manager():
    """Test thread-safe session memory manager."""
    mem = SessionMemoryManager()
    mem.append_turn("sess_1", "What crop to sow?", "Rice is recommended.")
    mem.append_turn("sess_1", "Show spacing diagram", "Here is the spacing diagram.")

    history = mem.get_history("sess_1")
    assert len(history) == 2
    assert history[0]["turn"] == 1
    assert history[1]["turn"] == 2

    mem.clear_session("sess_1")
    assert len(mem.get_history("sess_1")) == 0


@pytest.mark.asyncio
async def test_langgraph_stategraph_crop_workflow():
    """Test end-to-end execution of the compiled StateGraph for a crop query."""
    graph = create_agrisys_graph()
    initial_state = {
        "query": "recommend the best crop for Punjab alluvial soil in kharif",
        "image_bytes": None,
        "image_path": None,
        "sensor_data": {"N": 90.0, "P": 42.0, "K": 43.0, "ph": 6.5, "rainfall": 200.0, "season": "kharif"},
        "voice_audio_path": None,
        "language": "en",
        "location": {"state": "Punjab"},
        "session_id": "test_sess",
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
        "merged_response": "",
        "confidence_score": 0.0,
        "hallucination_score": 1.0,
        "escalate": False,
        "tts_audio_path": None,
    }

    final_state = await graph.ainvoke(initial_state)

    assert "crop_recommendation" in final_state["intents"]
    assert final_state["active_crop"] is not None
    assert len(final_state["agent_results"]) >= 1
    assert final_state["confidence_score"] > 0.0
    assert len(final_state["merged_response"]) > 20


@pytest.mark.asyncio
async def test_langgraph_stategraph_diagram_workflow():
    """Test end-to-end execution of the compiled StateGraph for a diagram request."""
    graph = create_agrisys_graph()
    initial_state = {
        "query": "show me drip irrigation layout pipe diagram",
        "image_bytes": None,
        "image_path": None,
        "sensor_data": None,
        "voice_audio_path": None,
        "language": "hi",
        "location": None,
        "session_id": "test_diag_sess",
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
        "merged_response": "",
        "confidence_score": 0.0,
        "hallucination_score": 1.0,
        "escalate": False,
        "tts_audio_path": None,
    }

    final_state = await graph.ainvoke(initial_state)

    assert "diagram_request" in final_state["intents"]
    assert final_state["diagram_code"] is not None
    assert final_state["diagram_type"] is not None
