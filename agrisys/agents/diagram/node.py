"""LangGraph node for the Diagram Generation Agent."""

from __future__ import annotations
import logging
from typing import Any
from agrisys.agents.diagram.agent import DiagramAgent
from agrisys.agents.diagram.models import DiagramRequest
from agrisys.providers.factory import get_llm_provider

logger = logging.getLogger(__name__)


async def diagram_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph state node executing the Diagram Agent."""
    query = state.get("query", "")
    language = state.get("language", "en")
    active_crop = state.get("active_crop") or (state.get("crop_data") or {}).get("winning_crop")

    try:
        llm = get_llm_provider()
    except Exception:
        llm = None

    agent = DiagramAgent(llm_provider=llm)
    req = DiagramRequest(
        query=query,
        crop_name=active_crop,
        language=language,
        context_data=state.get("sensor_data") or {},
    )

    result = await agent.generate_diagram(req)

    return {
        "diagram_code": result.raw_code,
        "diagram_type": result.visual_type.value,
        "svg_schematic": result.raw_code if result.engine_used == "svg_2d" else None,
        "agent_results": [{
            "agent": "diagram_agent",
            "engine": result.engine_used,
            "visual_type": result.visual_type.value,
            "caption": result.caption,
            "is_valid": result.is_valid,
        }],
    }
