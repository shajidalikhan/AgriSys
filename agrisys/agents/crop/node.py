"""LangGraph node for the Crop Recommendation Agent."""

from __future__ import annotations
import logging
from typing import Any
from agrisys.agents.crop.models import CropInputFeatures
from agrisys.agents.crop.agent import CropRecommendationAgent

logger = logging.getLogger(__name__)


async def crop_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph state node executing the Crop Recommendation Agent."""
    sensor_data = state.get("sensor_data") or {}
    language = state.get("language", "en")

    # Extract or provide standard regional defaults
    features = CropInputFeatures(
        N=float(sensor_data.get("N", 75.0)),
        P=float(sensor_data.get("P", 45.0)),
        K=float(sensor_data.get("K", 40.0)),
        temperature=float(sensor_data.get("temperature", 24.5)),
        humidity=float(sensor_data.get("humidity", 78.0)),
        ph=float(sensor_data.get("ph", 6.4)),
        rainfall=float(sensor_data.get("rainfall", 185.0)),
        ec=float(sensor_data.get("ec", 0.8)),
        season=sensor_data.get("season", "kharif"),
        water_availability=sensor_data.get("water_availability", "canal_irrigated"),
        state=sensor_data.get("state", (state.get("location") or {}).get("state", "Punjab")),
    )

    agent = CropRecommendationAgent()
    output = await agent.recommend(features=features, top_k=3, language=language)

    return {
        "active_crop": output.winning_crop,
        "shap_values": output.shap_attributions,
        "crop_data": output.model_dump(),
        "citations": output.rag_citations,
        "agent_results": [{
            "agent": "crop_agent",
            "winning_crop": output.winning_crop,
            "confidence": output.overall_confidence,
            "top_3": [(r.crop_name, r.probability) for r in output.top_recommendations],
            "advisory": output.advisory_text,
            "is_feasible": output.top_recommendations[0].feasibility.is_feasible,
        }],
    }
