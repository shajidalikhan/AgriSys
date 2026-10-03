"""Crop Recommendation Explainability via SHAP TreeExplainer."""

from __future__ import annotations
import logging
from typing import Any, Dict, List
import numpy as np
import shap

logger = logging.getLogger(__name__)

FEATURE_NAMES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]

BILINGUAL_FEATURE_LABELS = {
    "N": "नाइट्रोजन (Nitrogen)",
    "P": "फास्फोरस (Phosphorus)",
    "K": "पोटेशियम (Potassium)",
    "temperature": "तापमान (Temperature)",
    "humidity": "आर्द्रता (Humidity)",
    "ph": "मृदा पीएच (Soil pH)",
    "rainfall": "वार्षिक वर्षा (Annual Rainfall)",
}


class CropSHAPExplainer:
    """Computes SHAP feature attribution for crop recommendation models (TreeExplainer)."""

    def __init__(self, xgb_model: Any, class_mapping: Dict[int, str] | None = None):
        self.xgb_model = xgb_model
        self.class_mapping = class_mapping or {}
        self.explainer = None
        self._init_explainer()

    def _init_explainer(self) -> None:
        try:
            self.explainer = shap.TreeExplainer(self.xgb_model)
            logger.info("Initialized SHAP TreeExplainer for crop XGBoost model.")
        except Exception as e:
            logger.warning(f"Could not initialize native TreeExplainer, using algorithmic fallback: {e}")
            self.explainer = None

    def explain(
        self,
        features: list[float],
        target_crop_index: int = 0,
        language: str = "hi",
    ) -> dict[str, Any]:
        """
        Explain the prediction for a specific crop class index.
        Returns:
            {
                "feature_contributions": [{"feature": "N", "label": "...", "shap_value": 0.45}, ...],
                "positive_drivers": ["..."],
                "limiting_factors": ["..."],
                "base_value": float
            }
        """
        feat_array = np.array([features], dtype=np.float32)

        if self.explainer:
            try:
                shap_values = self.explainer.shap_values(feat_array)
                # For multi-class, shap_values can be a list of arrays [classes, samples, features]
                # or a 3D array [samples, features, classes]
                if isinstance(shap_values, list):
                    values_for_class = shap_values[target_crop_index][0]
                elif len(shap_values.shape) == 3:
                    values_for_class = shap_values[0, :, target_crop_index]
                else:
                    values_for_class = shap_values[0]

                base_val = float(
                    self.explainer.expected_value[target_crop_index]
                    if isinstance(self.explainer.expected_value, (list, np.ndarray))
                    else self.explainer.expected_value
                )
            except Exception as e:
                logger.warning(f"SHAP compute error, using fallback: {e}")
                values_for_class, base_val = self._algorithmic_fallback(features)
        else:
            values_for_class, base_val = self._algorithmic_fallback(features)

        contributions: List[Dict[str, Any]] = []
        positives: List[str] = []
        limiters: List[str] = []

        for name, val in zip(FEATURE_NAMES, values_for_class):
            v_float = round(float(val), 4)
            lbl = (
                BILINGUAL_FEATURE_LABELS.get(name, name)
                if language != "en"
                else name
            )
            contributions.append({
                "feature": name,
                "label": lbl,
                "shap_value": v_float,
            })
            if v_float > 0.05:
                positives.append(f"{lbl} (+{v_float:.2f})")
            elif v_float < -0.05:
                limiters.append(f"{lbl} ({v_float:.2f})")

        # Sort contributions by absolute impact
        contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)

        return {
            "feature_contributions": contributions,
            "positive_drivers": positives[:3],
            "limiting_factors": limiters[:3],
            "base_value": round(base_val, 4),
        }

    def _algorithmic_fallback(self, features: list[float]) -> tuple[list[float], float]:
        """Calculates normalized relative feature deviations when native SHAP is unavailable."""
        # Baseline reference: N=50, P=50, K=50, temp=25, hum=70, ph=6.5, rain=100
        baselines = [50.0, 50.0, 50.0, 25.0, 70.0, 6.5, 100.0]
        stds = [30.0, 25.0, 30.0, 6.0, 15.0, 0.8, 80.0]
        vals = []
        for feat, base, std in zip(features, baselines, stds):
            z = (feat - base) / (std or 1.0)
            vals.append(float(np.clip(z * 0.15, -0.8, 0.8)))
        return vals, 0.10
