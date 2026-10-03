"""Local XGBoost Crop Recommendation Tool."""

from __future__ import annotations
import os
import json
import logging
import numpy as np
import xgboost as xgb
from agrisys.agents.crop.models import CropInputFeatures
from agrisys.agents.crop.registry import BaseCropModelTool, register_crop_tool

logger = logging.getLogger(__name__)


class LocalXGBoostCropModelTool(BaseCropModelTool):
    """SRP: Only computes XGBoost multi-class probabilities for crop prediction."""

    def __init__(
        self,
        model_path: str = "models/crop_xgb_model.json",
        label_mapping_path: str = "models/crop_label_mapping.json",
    ):
        self._tool_name = "xgb_crop_classifier"
        self.model_path = model_path
        self.label_mapping_path = label_mapping_path
        self.model: xgb.XGBClassifier | None = None
        self.label_mapping: dict[int, str] = {}
        self._load_model()

    @property
    def tool_name(self) -> str:
        return self._tool_name

    def _load_model(self) -> None:
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"XGBoost model file not found at: {self.model_path}")

        if not os.path.exists(self.label_mapping_path):
            raise FileNotFoundError(f"Label mapping file not found at: {self.label_mapping_path}")

        with open(self.label_mapping_path, "r", encoding="utf-8") as f:
            raw_map = json.load(f)
            self.label_mapping = {int(k): v for k, v in raw_map.items()}

        self.model = xgb.XGBClassifier()
        self.model.load_model(self.model_path)
        logger.info(f"Loaded XGBoost model from {self.model_path} with {len(self.label_mapping)} classes.")

    async def predict(self, features: CropInputFeatures) -> list[tuple[str, float]]:
        """Compute ranked (crop, probability) list."""
        feat_array = np.array([features.to_feature_array()], dtype=np.float32)
        proba = self.model.predict_proba(feat_array)[0]

        ranked: list[tuple[str, float]] = []
        for class_idx, prob in enumerate(proba):
            crop_name = self.label_mapping.get(class_idx, f"crop_{class_idx}")
            ranked.append((crop_name, float(prob)))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked


# Auto-register default instance
try:
    default_xgb_tool = LocalXGBoostCropModelTool()
    register_crop_tool("xgb_crop_classifier", default_xgb_tool)
except Exception as e:
    logger.warning(f"Could not initialize default LocalXGBoostCropModelTool: {e}")
