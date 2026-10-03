"""Crop Model Router with Circuit Breaker and Fallback (§4.3).

Fulfills:
- Routes identified crop to specialized disease model tools
- Falls back to general disease detector if crop is unsupported or endpoint fails
- Ensembles multiple specialist models via WeightedEnsembleVoter
"""

import asyncio
from typing import List, Optional
import logging
from agrisys.agents.disease.models import DiseasePrediction
from agrisys.agents.disease.registry import MODEL_REGISTRY, get_disease_tool, BaseDiseaseModelTool
from agrisys.agents.disease.ensemble import WeightedEnsembleVoter

logger = logging.getLogger(__name__)


class CropModelRouter:
    """Dispatches image inference to crop-specific or universal model tools."""

    def __init__(self, confidence_threshold: float = 0.70) -> None:
        self.confidence_threshold = confidence_threshold

    def get_candidate_tools(self, crop: str) -> List[BaseDiseaseModelTool]:
        """Find enabled specialist tools supporting crop, or fallback to general tools."""
        crop_clean = crop.lower().strip()
        specialist_tools: List[BaseDiseaseModelTool] = []
        general_tools: List[BaseDiseaseModelTool] = []

        for name, cfg in MODEL_REGISTRY.items():
            if not cfg.get("enabled", True):
                continue
            role = cfg.get("role", "")
            crops = [c.lower() for c in cfg.get("crops", [])]

            if role == "crop_specific_disease" and (crop_clean in crops or "all" in crops):
                specialist_tools.append(get_disease_tool(name))
            elif role == "general_disease":
                general_tools.append(get_disease_tool(name))

        if specialist_tools:
            return specialist_tools
        return general_tools if general_tools else [get_disease_tool("general_disease_detector")]

    async def route_and_predict(self, crop: str, image_bytes: bytes) -> DiseasePrediction:
        """Execute inference against candidate tools and aggregate via ensemble voter."""
        candidate_tools = self.get_candidate_tools(crop)
        predictions: List[DiseasePrediction] = []
        weights: List[float] = []

        # Execute candidate tools concurrently
        tasks = [tool.predict(image_bytes) for tool in candidate_tools]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for tool, res in zip(candidate_tools, results):
            if isinstance(res, DiseasePrediction):
                predictions.append(res)
                weights.append(tool.weight)
            else:
                logger.warning("Tool '%s' failed during prediction: %s", tool.name, res)

        # Circuit breaker fallback to general disease detector if all specialists failed
        if not predictions:
            logger.warning("All specialist tools failed for crop '%s', falling back to general detector", crop)
            general_tool = get_disease_tool("general_disease_detector")
            fallback_pred = await general_tool.predict(image_bytes)
            predictions.append(fallback_pred)
            weights.append(1.0)

        # Run weighted ensemble vote
        winner = WeightedEnsembleVoter.vote(predictions, weights, threshold=self.confidence_threshold)
        return winner
