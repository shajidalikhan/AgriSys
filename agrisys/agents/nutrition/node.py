"""LangGraph state node for the Nutrition Deficiency Agent."""

from __future__ import annotations
import logging
from typing import Any
from agrisys.agents.nutrition.models import SoilSensorReading
from agrisys.agents.nutrition.agent import NutritionAgent

logger = logging.getLogger(__name__)


async def nutrition_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph state node executing the Nutrition Deficiency Agent."""
    query = state.get("query", "")
    sensor_raw = state.get("sensor_data")
    image_bytes = state.get("image_bytes")
    crop = state.get("active_crop") or "Tomato"
    language = state.get("language", "en")

    # If sensor data not provided in state, provide standard defaults or parse
    sensor_reading: SoilSensorReading | None = None
    if sensor_raw:
        sensor_reading = SoilSensorReading(
            nitrogen=float(sensor_raw.get("nitrogen", sensor_raw.get("N", 240.0))),
            phosphorus=float(sensor_raw.get("phosphorus", sensor_raw.get("P", 14.0))),
            potassium=float(sensor_raw.get("potassium", sensor_raw.get("K", 150.0))),
            ph=float(sensor_raw.get("ph", sensor_raw.get("pH", 6.8))),
            electrical_conductivity=float(sensor_raw.get("electrical_conductivity", sensor_raw.get("ec", sensor_raw.get("EC", 0.65)))),
            soil_moisture=float(sensor_raw.get("soil_moisture", sensor_raw.get("moisture", 45.0))),
        )
    elif not image_bytes:
        # If neither image nor sensor provided, use baseline regional reading
        sensor_reading = SoilSensorReading(
            nitrogen=210.0,
            phosphorus=12.0,
            potassium=130.0,
            ph=6.5,
            electrical_conductivity=0.6,
            soil_moisture=40.0,
        )

    # Detect crop mention in query if active_crop was unset
    q_lower = query.lower()
    for candidate in ["tomato", "rice", "paddy", "wheat", "maize", "cotton", "potato", "sugarcane", "banana", "chilli", "onion"]:
        if candidate in q_lower:
            crop = candidate.capitalize()
            break

    agent = NutritionAgent()
    report = agent.diagnose(
        image_bytes=image_bytes,
        sensor_data=sensor_reading,
        crop=crop,
        language=language,
    )

    return {
        "nutrition_data": report.model_dump(),
        "citations": report.citations,
        "agent_results": [{
            "agent": "nutrition_agent",
            "crop": report.crop,
            "modality": report.input_modality,
            "deficiency": report.prediction.deficiency_class,
            "confidence": report.prediction.confidence,
            "severity": report.prediction.severity,
            "advisory": report.advisory,
            "urea_kg_acre": report.fertilizer_recommendation.urea_kg_acre,
            "dap_kg_acre": report.fertilizer_recommendation.dap_kg_acre,
            "mop_kg_acre": report.fertilizer_recommendation.mop_kg_acre,
            "application_schedule": report.fertilizer_recommendation.application_schedule,
        }],
    }
