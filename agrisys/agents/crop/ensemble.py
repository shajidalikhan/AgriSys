"""Weighted Multi-Model Crop Ensemble Voter."""

from __future__ import annotations
import logging
from collections import defaultdict
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class CropEnsembleVoter:
    """Combines predictions from multiple crop recommendation tools via weighted probability voting."""

    DEFAULT_WEIGHTS = {
        "xgb_crop_classifier": 0.60,
        "rf_crop_classifier": 0.40,
    }

    def __init__(self, weights: Dict[str, float] | None = None):
        self.weights = weights or self.DEFAULT_WEIGHTS

    def vote(
        self, tool_predictions: Dict[str, List[Tuple[str, float]]]
    ) -> List[Tuple[str, float]]:
        """
        Calculates normalized weighted probability across active model predictions.
        tool_predictions: {tool_name: [(crop, prob), ...]}
        """
        if not tool_predictions:
            return []

        if len(tool_predictions) == 1:
            # Single model output
            return next(iter(tool_predictions.values()))

        # Normalize weights for active models
        active_tools = list(tool_predictions.keys())
        total_weight = sum(self.weights.get(t, 1.0) for t in active_tools)
        norm_weights = {t: self.weights.get(t, 1.0) / total_weight for t in active_tools}

        crop_scores = defaultdict(float)
        for tool_name, preds in tool_predictions.items():
            w = norm_weights.get(tool_name, 0.0)
            for crop, prob in preds:
                crop_scores[crop] += w * prob

        # Normalize probabilities so sum = 1.0
        total_score = sum(crop_scores.values()) or 1.0
        final_ranked = [
            (crop, round(score / total_score, 4))
            for crop, score in crop_scores.items()
        ]
        final_ranked.sort(key=lambda x: x[1], reverse=True)
        return final_ranked
