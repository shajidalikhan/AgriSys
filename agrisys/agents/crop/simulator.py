"""What-If Sensitivity Simulation Service for Crop Decision Support."""

from __future__ import annotations
import logging
from typing import Any
from agrisys.agents.crop.models import (
    CropInputFeatures,
    WhatIfSimulationRequest,
    WhatIfSimulationResult,
)
from agrisys.agents.crop.ensemble import CropEnsembleVoter
from agrisys.agents.crop.registry import CROP_MODEL_REGISTRY

logger = logging.getLogger(__name__)


class CropSimulationService:
    """SRP: Runs perturbation analysis comparing base scenario against what-if simulated conditions."""

    def __init__(self, voter: CropEnsembleVoter | None = None):
        self.voter = voter or CropEnsembleVoter()

    async def simulate(self, request: WhatIfSimulationRequest) -> WhatIfSimulationResult:
        base = request.base_features

        # 1. Base Prediction
        base_preds = await self._predict_ensemble(base)
        orig_winner, orig_prob = base_preds[0] if base_preds else ("unknown", 0.0)

        # 2. Perturbed Prediction
        perturbed_dict = base.model_dump()
        for k, delta in request.delta_features.items():
            if k in perturbed_dict and isinstance(perturbed_dict[k], (int, float)):
                perturbed_dict[k] = max(0.0, perturbed_dict[k] + delta)

        sim_features = CropInputFeatures(**perturbed_dict)
        sim_preds = await self._predict_ensemble(sim_features)
        sim_winner, sim_prob = sim_preds[0] if sim_preds else ("unknown", 0.0)

        # 3. Calculate shifts for top candidates
        base_map = {c: p for c, p in base_preds}
        sim_map = {c: p for c, p in sim_preds}
        all_crops = set(list(base_map.keys())[:5] + list(sim_map.keys())[:5])

        prob_shifts = {}
        for c in all_crops:
            prob_shifts[c] = round(sim_map.get(c, 0.0) - base_map.get(c, 0.0), 4)

        changed = orig_winner != sim_winner

        if changed:
            verdict = (
                f"Agronomic Shift: Changing inputs by {request.delta_features} changes the optimal crop from "
                f"{orig_winner.capitalize()} ({orig_prob * 100:.1f}%) to {sim_winner.capitalize()} ({sim_prob * 100:.1f}%)."
            )
        else:
            diff = sim_prob - orig_prob
            trend = "strengthens" if diff >= 0 else "weakens"
            verdict = (
                f"Stable Recommendation: {orig_winner.capitalize()} remains optimal, but confidence {trend} by "
                f"{abs(diff) * 100:.1f}% (from {orig_prob * 100:.1f}% to {sim_prob * 100:.1f}%)."
            )

        return WhatIfSimulationResult(
            original_winner=orig_winner,
            original_probability=orig_prob,
            simulated_winner=sim_winner,
            simulated_probability=sim_prob,
            probability_shifts=prob_shifts,
            recommendation_changed=changed,
            agronomic_verdict=verdict,
        )

    async def _predict_ensemble(self, features: CropInputFeatures) -> list[tuple[str, float]]:
        tool_results = {}
        for name, tool in CROP_MODEL_REGISTRY.items():
            try:
                preds = await tool.predict(features)
                tool_results[name] = preds
            except Exception as e:
                logger.warning(f"Tool {name} failed in simulation: {e}")

        return self.voter.vote(tool_results)
