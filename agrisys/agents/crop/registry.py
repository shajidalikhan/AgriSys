"""Open/Closed Model Registry for Crop Recommendation Tools."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict
from agrisys.agents.crop.models import CropInputFeatures


class BaseCropModelTool(ABC):
    """Abstract interface for all crop recommendation model tools (LSP & ISP)."""

    @abstractmethod
    async def predict(self, features: CropInputFeatures) -> list[tuple[str, float]]:
        """
        Takes validated agronomic features and outputs ranked list of (crop_name, probability).
        Probabilities sum to 1.0 and are sorted descending.
        """
        ...

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Identifier for the tool."""
        ...


# Global dynamic model registry
CROP_MODEL_REGISTRY: Dict[str, BaseCropModelTool] = {}


def register_crop_tool(name: str, tool: BaseCropModelTool) -> None:
    """Register a new crop model tool without modifying existing agent code (OCP)."""
    CROP_MODEL_REGISTRY[name] = tool


def get_crop_tool(name: str) -> BaseCropModelTool:
    """Retrieve registered crop model tool."""
    if name not in CROP_MODEL_REGISTRY:
        raise KeyError(f"Crop model tool '{name}' not found in CROP_MODEL_REGISTRY. Available: {list(CROP_MODEL_REGISTRY.keys())}")
    return CROP_MODEL_REGISTRY[name]
