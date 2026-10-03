"""Disease Model Registry and Tool Abstraction (§4.1).

Fulfills Open/Closed Principle (OCP):
- Models are exposed as modular Agent Tools implementing BaseDiseaseModelTool.
- New models can be added by adding an entry to MODEL_REGISTRY or calling register_disease_tool.
- No changes required to agent or orchestrator code.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from agrisys.agents.disease.models import DiseasePrediction
from agrisys.agents.disease.client import SecureModelEndpointClient, parse_plantvillage_label


class BaseDiseaseModelTool(ABC):
    """Abstract interface for disease model tools."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def crops_supported(self) -> List[str]: ...

    @property
    @abstractmethod
    def role(self) -> str:
        """'crop_detection', 'crop_specific_disease', or 'general_disease'."""
        ...

    @property
    @abstractmethod
    def weight(self) -> float: ...

    @abstractmethod
    async def predict(self, image_bytes: bytes) -> DiseasePrediction:
        """Execute inference against the model endpoint."""
        ...


class EndpointDiseaseModelTool(BaseDiseaseModelTool):
    """Concrete model tool delegating inference to an HTTP/REST endpoint."""

    def __init__(
        self,
        name: str,
        endpoint_url: str,
        crops_supported: Optional[List[str]] = None,
        role: str = "general_disease",
        weight: float = 1.0,
        client: Optional[SecureModelEndpointClient] = None,
    ) -> None:
        self._name = name
        self.endpoint_url = endpoint_url
        self._crops_supported = [c.lower() for c in (crops_supported or ["all"])]
        self._role = role
        self._weight = weight
        self.client = client or SecureModelEndpointClient()

    @property
    def name(self) -> str:
        return self._name

    @property
    def crops_supported(self) -> List[str]:
        return self._crops_supported

    @property
    def role(self) -> str:
        return self._role

    @property
    def weight(self) -> float:
        return self._weight

    async def predict(self, image_bytes: bytes) -> DiseasePrediction:
        raw_predictions = await self.client.predict_image(self.endpoint_url, image_bytes)
        if not raw_predictions:
            return DiseasePrediction(
                crop="unknown",
                disease="unidentified",
                confidence=0.0,
                model_name=self.name,
                execution_mode="endpoint",
            )

        top_pred = raw_predictions[0]
        label = top_pred.get("label", "unknown___healthy")
        score = float(top_pred.get("score", 0.5))
        crop, disease = parse_plantvillage_label(label)

        # Estimate default severity based on disease and score
        severity = 0 if "healthy" in disease else max(1, min(5, int(score * 4) + 1))
        sev_labels = ["Healthy", "Trace", "Mild", "Moderate", "Severe", "Critical"]

        return DiseasePrediction(
            crop=crop,
            disease=disease,
            confidence=round(score, 3),
            severity=severity,
            severity_label=sev_labels[severity],
            top_k=raw_predictions[:3],
            model_name=self.name,
            execution_mode="endpoint",
        )


# === Central Model Registry (§4.1) ===
# Edit this dictionary to add, enable, or retarget disease models without touching agent code.
MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "crop_detector": {
        "endpoint_url": "https://api-inference.huggingface.co/models/linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification",
        "crops": ["all"],
        "role": "crop_detection",
        "weight": 1.0,
        "enabled": True,
    },
    "tomato_specialist": {
        "endpoint_url": "https://api-inference.huggingface.co/models/linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification",
        "crops": ["tomato", "potato", "apple", "grape", "peach"],
        "role": "crop_specific_disease",
        "weight": 0.45,
        "enabled": True,
    },
    "cereal_grain_specialist": {
        "endpoint_url": "https://api-inference.huggingface.co/models/wambugu71/crop_leaf_diseases_vit",
        "crops": ["wheat", "rice", "corn", "potato"],
        "role": "crop_specific_disease",
        "weight": 0.35,
        "enabled": True,
    },
    "general_disease_detector": {
        "endpoint_url": "https://api-inference.huggingface.co/models/ozair23/plant-disease-detection",
        "crops": ["all"],
        "role": "general_disease",
        "weight": 0.20,
        "enabled": True,
    },
}

_TOOL_INSTANCES: Dict[str, BaseDiseaseModelTool] = {}


def get_disease_tool(tool_name: str) -> BaseDiseaseModelTool:
    """Retrieve or instantiate a disease model tool from MODEL_REGISTRY."""
    if tool_name in _TOOL_INSTANCES:
        return _TOOL_INSTANCES[tool_name]

    if tool_name not in MODEL_REGISTRY:
        raise KeyError(f"Tool '{tool_name}' not found in MODEL_REGISTRY. Available: {list(MODEL_REGISTRY.keys())}")

    cfg = MODEL_REGISTRY[tool_name]
    tool = EndpointDiseaseModelTool(
        name=tool_name,
        endpoint_url=cfg["endpoint_url"],
        crops_supported=cfg.get("crops", ["all"]),
        role=cfg.get("role", "general_disease"),
        weight=cfg.get("weight", 1.0),
    )
    _TOOL_INSTANCES[tool_name] = tool
    return tool


def register_disease_tool(tool_name: str, tool: BaseDiseaseModelTool) -> None:
    """Dynamically register a new disease model tool instance (OCP)."""
    _TOOL_INSTANCES[tool_name] = tool
