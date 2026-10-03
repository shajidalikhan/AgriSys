"""Unit tests for Disease Model Registry and Tool Abstraction (§4.1).

Tests tool discovery, PlantVillage label parsing, endpoint client, and OCP extension.
"""

import pytest
from agrisys.agents.disease.client import parse_plantvillage_label, SecureModelEndpointClient
from agrisys.agents.disease.registry import (
    MODEL_REGISTRY,
    get_disease_tool,
    register_disease_tool,
    BaseDiseaseModelTool,
    EndpointDiseaseModelTool,
)
from agrisys.agents.disease.models import DiseasePrediction


def test_plantvillage_label_parsing():
    """Verify parsing of various HuggingFace PlantVillage label formats."""
    crop1, dis1 = parse_plantvillage_label("Tomato___Early_blight")
    assert crop1 == "tomato"
    assert dis1 == "early_blight"

    crop2, dis2 = parse_plantvillage_label("Corn_(maize)___Common_rust_")
    assert crop2 == "corn"
    assert dis2 == "common_rust"

    crop3, dis3 = parse_plantvillage_label("Apple___healthy")
    assert crop3 == "apple"
    assert dis3 == "healthy"


def test_model_registry_entries():
    """Verify standard models are registered with roles and endpoints."""
    assert "crop_detector" in MODEL_REGISTRY
    assert "tomato_specialist" in MODEL_REGISTRY
    assert "cereal_grain_specialist" in MODEL_REGISTRY
    assert "general_disease_detector" in MODEL_REGISTRY

    tool = get_disease_tool("tomato_specialist")
    assert tool.name == "tomato_specialist"
    assert "tomato" in tool.crops_supported
    assert tool.role == "crop_specific_disease"


@pytest.mark.asyncio
async def test_endpoint_tool_prediction():
    """Verify EndpointDiseaseModelTool parses scores and outputs structured DiseasePrediction."""
    tool = get_disease_tool("tomato_specialist")
    pred = await tool.predict(b"mock_image_bytes")

    assert isinstance(pred, DiseasePrediction)
    assert pred.crop in ["tomato", "potato"]
    assert pred.confidence > 0.5
    assert pred.severity >= 0
    assert len(pred.top_k) > 0


class CustomMockDiseaseTool(BaseDiseaseModelTool):
    """Custom model tool to verify Open/Closed Principle extension."""
    @property
    def name(self):
        return "custom_mustard_specialist"

    @property
    def crops_supported(self):
        return ["mustard"]

    @property
    def role(self):
        return "crop_specific_disease"

    @property
    def weight(self):
        return 0.5

    async def predict(self, image_bytes: bytes):
        return DiseasePrediction(
            crop="mustard",
            disease="white_rust",
            confidence=0.96,
            severity=3,
            severity_label="Moderate",
            model_name=self.name,
        )


@pytest.mark.asyncio
async def test_open_closed_principle_extension():
    """Verify adding a new disease tool without modifying existing agent code."""
    custom_tool = CustomMockDiseaseTool()
    register_disease_tool("custom_mustard_specialist", custom_tool)

    retrieved = get_disease_tool("custom_mustard_specialist")
    assert retrieved.name == "custom_mustard_specialist"

    pred = await retrieved.predict(b"dummy")
    assert pred.crop == "mustard"
    assert pred.disease == "white_rust"
    assert pred.confidence == 0.96
