"""LangGraph state node for the Market Price Intelligence Agent."""

from __future__ import annotations
import logging
from typing import Any
from agrisys.agents.market.agent import MarketAgent

logger = logging.getLogger(__name__)


async def market_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph state node executing the Market Price Intelligence Agent."""
    query = state.get("query", "")
    crop = state.get("active_crop") or "Tomato"
    language = state.get("language", "en")
    location = state.get("location") or {}

    # Extract crop from query if not already set or defaulted
    q_lower = query.lower()
    for candidate in ["tomato", "wheat", "rice", "paddy", "potato", "onion", "cotton", "mustard", "maize", "soyabean", "gram"]:
        if candidate in q_lower:
            crop = candidate.capitalize()
            break

    lat = float(location.get("latitude", location.get("lat", 26.8467)))
    lon = float(location.get("longitude", location.get("lon", 80.9462)))
    loc_name = location.get("state", location.get("district", "Lucknow, Uttar Pradesh"))

    agent = MarketAgent()
    report = await agent.advise(
        commodity=crop,
        origin_lat=lat,
        origin_lon=lon,
        location_name=loc_name,
        language=language,
    )

    return {
        "market_data": report.model_dump(),
        "citations": report.citations,
        "agent_results": [{
            "agent": "market_agent",
            "commodity": report.commodity,
            "current_price_kg": report.current_modal_price_kg,
            "current_price_quintal": report.current_modal_price_quintal,
            "recommendation": report.recommendation,
            "trend_direction": report.trend_direction,
            "trend_percentage": report.trend_percentage,
            "advisory": report.advisory_text,
            "best_mandi": report.top_mandis[0].mandi_name if report.top_mandis else None,
            "msp_status": report.msp_analysis.status,
        }],
    }
