"""Hybrid Multi-Intent Router for AgriSys LangGraph Orchestrator."""

from __future__ import annotations
import logging
import re
from typing import Any, List
from agrisys.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)

INTENT_KEYWORDS = {
    "disease": [
        "disease", "pest", "spot", "blight", "fungus", "rot", "wilt", "yellowing",
        "insect", "caterpillar", "leaf curl", "rust", "mildew", "symptom", "infection"
    ],
    "crop_recommendation": [
        "recommend crop", "which crop", "what to plant", "suitable crop", "crop selection",
        "soil test", "kharif", "rabi", "zaid", "sow", "farming options", "crop suitability"
    ],
    "diagram_request": [
        "diagram", "flowchart", "layout", "spacing", "calendar", "timeline", "schematic",
        "cross section", "how to install", "pruning cut", "trap grid", "draw", "visual"
    ],
    "nutrition": [
        "fertilizer", "nutrient", "urea", "dap", "potash", "deficiency", "npk dose",
        "chlorosis", "zinc", "nitrogen deficiency"
    ],
    "weather": [
        "weather", "forecast", "rain", "rainfall", "temperature", "frost", "storm"
    ],
    "market": [
        "mandi price", "market price", "rate", "bhav", "selling price", "msp", "enam"
    ],
    "web_search": [
        "scheme", "subsidy", "subsidies", "pm kisan", "pm-kisan", "pmfby", "fasal bima",
        "yojana", "kisan credit card", "kcc", "news", "portal", "latest update",
        "current affairs", "guidelines", "official update", "search online", "web search",
        "notification", "announcement", "government scheme", "subsidy status"
    ],
}


class IntentRouter:
    """Classifies user input into single or compound agricultural intents."""

    def __init__(self, llm_provider: BaseLLMProvider | None = None):
        self.llm_provider = llm_provider

    async def route(self, query: str, has_image: bool = False, has_sensor: bool = False) -> list[str]:
        q = query.lower().strip()
        intents: list[str] = []

        # 1. Fast heuristic matching
        for intent, kws in INTENT_KEYWORDS.items():
            if any(re.search(rf"\b{re.escape(kw)}\b", q) for kw in kws):
                intents.append(intent)

        # Implicit multimodal cues
        if has_image and "disease" not in intents:
            intents.append("disease")

        if has_sensor and "crop_recommendation" not in intents and "nutrition" not in intents:
            intents.append("crop_recommendation")

        if intents:
            return list(dict.fromkeys(intents))  # deduplicate preserving order

        # 2. LLM classification for ambiguous natural language
        if self.llm_provider:
            try:
                llm_intents = await self._classify_with_llm(query)
                if llm_intents:
                    return llm_intents
            except Exception as e:
                logger.warning(f"LLM intent classification fallback: {e}")

        # Default fallback
        return ["general_agronomy"]

    async def _classify_with_llm(self, query: str) -> list[str]:
        prompt = (
            f"Classify the following farmer query into one or more categories from: "
            f"['disease', 'crop_recommendation', 'diagram_request', 'nutrition', 'weather', 'market', 'web_search', 'general_agronomy'].\n"
            f"Query: \"{query}\"\n"
            f"Return ONLY comma-separated categories, e.g. 'disease, diagram_request'."
        )
        resp = await self.llm_provider.complete([{"role": "user", "content": prompt}])
        cleaned = [c.strip().lower() for c in resp.split(",") if c.strip().lower() in INTENT_KEYWORDS or c.strip().lower() == "general_agronomy"]
        return cleaned or ["general_agronomy"]
