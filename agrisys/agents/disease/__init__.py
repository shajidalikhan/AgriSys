"""Disease Diagnostic Agent Subpackage."""

from agrisys.agents.disease.models import (
    GatekeeperResult,
    CropDetectionResult,
    DiseasePrediction,
    DiseaseDiagnosticReport,
)
from agrisys.agents.disease.preprocessor import ImagePreprocessor
from agrisys.agents.disease.client import SecureModelEndpointClient, parse_plantvillage_label
from agrisys.agents.disease.registry import (
    BaseDiseaseModelTool,
    EndpointDiseaseModelTool,
    MODEL_REGISTRY,
    get_disease_tool,
    register_disease_tool,
)
from agrisys.agents.disease.crop_detector import CropDetector
from agrisys.agents.disease.ensemble import WeightedEnsembleVoter
from agrisys.agents.disease.model_router import CropModelRouter
from agrisys.agents.disease.chain import AgriChainDiagnosticEngine
from agrisys.agents.disease.node import DiseaseAgent, get_disease_agent, disease_agent_node

__all__ = [
    "GatekeeperResult",
    "CropDetectionResult",
    "DiseasePrediction",
    "DiseaseDiagnosticReport",
    "ImagePreprocessor",
    "SecureModelEndpointClient",
    "parse_plantvillage_label",
    "BaseDiseaseModelTool",
    "EndpointDiseaseModelTool",
    "MODEL_REGISTRY",
    "get_disease_tool",
    "register_disease_tool",
    "CropDetector",
    "WeightedEnsembleVoter",
    "CropModelRouter",
    "AgriChainDiagnosticEngine",
    "DiseaseAgent",
    "get_disease_agent",
    "disease_agent_node",
]
