"""LangGraph state node for the Weather & Irrigation Advisory Agent."""

from __future__ import annotations
import logging
from typing import Any
from agrisys.agents.weather.agent import WeatherAgent

logger = logging.getLogger(__name__)


async def weather_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph state node executing the Weather & Irrigation Advisory Agent."""
    query = state.get("query", "")
    crop = state.get("active_crop") or "Wheat"
    language = state.get("language", "en")
    location = state.get("location") or {}

    # Extract crop from query if active_crop was unset
    q_lower = query.lower()
    for candidate in ["wheat", "rice", "paddy", "tomato", "potato", "maize", "cotton", "sugarcane", "mustard", "onion"]:
        if candidate in q_lower:
            crop = candidate.capitalize()
            break

    lat = float(location.get("latitude", location.get("lat", 26.8467)))
    lon = float(location.get("longitude", location.get("lon", 80.9462)))
    loc_name = location.get("state", location.get("district", "Lucknow, Uttar Pradesh"))

    agent = WeatherAgent()
    report = await agent.get_advisory(
        crop=crop,
        latitude=lat,
        longitude=lon,
        location_name=loc_name,
        language=language,
    )

    primary_alert = report.active_alerts[0] if report.active_alerts else None

    return {
        "weather_data": report.model_dump(),
        "citations": report.citations,
        "agent_results": [{
            "agent": "weather_agent",
            "location": report.location_name,
            "crop": report.eto_analysis.crop,
            "current_temp": report.current_temp,
            "condition": report.current_condition,
            "et0_mm_day": report.eto_analysis.et0_mm_day,
            "net_irrigation_mm": report.eto_analysis.net_irrigation_requirement_mm,
            "irrigation_advice": report.irrigation_advice,
            "active_alert": primary_alert.headline if primary_alert else None,
            "advisory": report.advisory_text,
        }],
    }
