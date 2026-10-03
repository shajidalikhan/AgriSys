"""Crop Recommendation Agent package."""

from agrisys.agents.crop.models import (
    CropInputFeatures,
    CropRecommendation,
    CropRecommendationOutput,
    CropFeasibilityStatus,
    WhatIfSimulationRequest,
    WhatIfSimulationResult,
    SeasonEnum,
    WaterSourceEnum,
)
from agrisys.agents.crop.registry import (
    BaseCropModelTool,
    CROP_MODEL_REGISTRY,
    register_crop_tool,
    get_crop_tool,
)
from agrisys.agents.crop.xgb_tool import LocalXGBoostCropModelTool
from agrisys.agents.crop.rf_tool import LocalRandomForestCropModelTool
from agrisys.agents.crop.endpoint_tool import EndpointCropModelTool
from agrisys.agents.crop.ensemble import CropEnsembleVoter
from agrisys.agents.crop.feasibility_guard import CropFeasibilityGuard
from agrisys.agents.crop.simulator import CropSimulationService
from agrisys.agents.crop.agent import CropRecommendationAgent
from agrisys.agents.crop.node import crop_agent_node

__all__ = [
    "CropInputFeatures",
    "CropRecommendation",
    "CropRecommendationOutput",
    "CropFeasibilityStatus",
    "WhatIfSimulationRequest",
    "WhatIfSimulationResult",
    "SeasonEnum",
    "WaterSourceEnum",
    "BaseCropModelTool",
    "CROP_MODEL_REGISTRY",
    "register_crop_tool",
    "get_crop_tool",
    "LocalXGBoostCropModelTool",
    "LocalRandomForestCropModelTool",
    "EndpointCropModelTool",
    "CropEnsembleVoter",
    "CropFeasibilityGuard",
    "CropSimulationService",
    "CropRecommendationAgent",
    "crop_agent_node",
]
