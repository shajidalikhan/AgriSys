"""Comprehensive unit and integration tests for Stage 4: Nutrition Deficiency Agent."""

import pytest
import torch
from fastapi.testclient import TestClient
from pydantic import ValidationError

from agrisys.agents.nutrition.models import (
    SoilSensorReading,
    DeficiencyPrediction,
    FertilizerDoseRecommendation,
    NutritionReport,
)
from agrisys.agents.nutrition.shc_rules import SoilHealthCardEvaluator, ICAR_CROP_POP_RECOMMENDATIONS
from agrisys.agents.nutrition.fusion_model import (
    CrossModalNutritionFusionNet,
    SensorNormalizer,
    DEFICIENCY_CLASSES,
    DEFICIENCY_SYMPTOMS,
)
from agrisys.agents.nutrition.agent import NutritionAgent
from agrisys.agents.nutrition.node import nutrition_agent_node
from agrisys.orchestrator.graph import create_agrisys_graph
from agrisys.api.main import app


# ------------------------------------------------------------------
# 1. Pydantic Model Validation Tests
# ------------------------------------------------------------------

def test_soil_sensor_validation_valid():
    sensor = SoilSensorReading(
        nitrogen=220.0,
        phosphorus=14.5,
        potassium=160.0,
        ph=6.8,
        electrical_conductivity=0.75,
        soil_moisture=42.0,
    )
    vec = sensor.to_feature_vector()
    assert len(vec) == 6
    assert vec[0] == 220.0
    assert vec[3] == 6.8


def test_soil_sensor_validation_invalid_ph():
    with pytest.raises(ValidationError):
        SoilSensorReading(
            nitrogen=200.0,
            phosphorus=15.0,
            potassium=150.0,
            ph=2.0,  # Below 3.5 minimum limit
            electrical_conductivity=0.5,
            soil_moisture=50.0,
        )


# ------------------------------------------------------------------
# 2. ICAR Soil Health Card Benchmark & Dose Tests
# ------------------------------------------------------------------

def test_icar_shc_evaluator_levels():
    sensor = SoilSensorReading(
        nitrogen=180.0,  # Low (< 280)
        phosphorus=30.0,  # High (> 25)
        potassium=150.0,  # Medium (108 - 280)
        ph=6.2,  # Acidic (< 6.5)
        electrical_conductivity=0.6,
        soil_moisture=20.0,  # Deficit (< 25)
    )
    evals = SoilHealthCardEvaluator.evaluate_nutrient_levels(sensor)
    assert "Low" in evals["N"]
    assert "High" in evals["P"]
    assert "Medium" in evals["K"]
    assert "Acidic" in evals["pH"]
    assert "Deficit" in evals["Moisture"]


def test_icar_fertilizer_dose_calculation():
    sensor = SoilSensorReading(
        nitrogen=150.0,  # Low -> +25% N dose
        phosphorus=15.0,  # Medium -> 100% P dose
        potassium=200.0,  # Medium -> 100% K dose
        ph=6.8,
        electrical_conductivity=0.5,
        soil_moisture=45.0,
    )
    rec = SoilHealthCardEvaluator.calculate_fertilizer_dose(crop="Tomato", sensor=sensor)
    assert rec.n_dose_kg_ha > 0.0
    assert rec.p_dose_kg_ha > 0.0
    assert rec.k_dose_kg_ha > 0.0
    assert rec.dap_kg_ha > 0.0
    assert rec.urea_kg_ha >= 0.0
    assert rec.mop_kg_ha > 0.0
    assert rec.urea_kg_acre == pytest.approx(rec.urea_kg_ha / 2.47105, rel=1e-2)
    assert len(rec.application_schedule) == 3


# ------------------------------------------------------------------
# 3. PyTorch Cross-Modal Fusion Network Tests
# ------------------------------------------------------------------

def test_cross_modal_fusion_network_multimodal():
    model = CrossModalNutritionFusionNet(num_classes=12)
    model.eval()

    # Create dummy 448x448 image tensor and 6-dim sensor tensor
    dummy_img = torch.randn(1, 3, 224, 224)
    dummy_sensor = torch.tensor([[0.3, 0.4, 0.5, 0.6, 0.2, 0.5]])

    logits, doses = model(dummy_img, dummy_sensor)
    assert logits.shape == (1, 12)
    assert doses.shape == (1, 3)

    label, conf, (n_d, p_d, k_d) = model.predict(dummy_img, dummy_sensor)
    assert label in DEFICIENCY_CLASSES
    assert 0.0 <= conf <= 1.0
    assert n_d >= 0.0 and p_d >= 0.0 and k_d >= 0.0


def test_cross_modal_fusion_network_sensor_only_fallback():
    model = CrossModalNutritionFusionNet(num_classes=12)
    model.eval()
    dummy_sensor = torch.tensor([[0.1, 0.2, 0.3, 0.5, 0.1, 0.4]])

    label, conf, doses = model.predict(image_tensor=None, sensor_tensor=dummy_sensor)
    assert label in DEFICIENCY_CLASSES
    assert 0.0 <= conf <= 1.0
    assert len(doses) == 3


def test_cross_modal_fusion_network_vision_only_fallback():
    model = CrossModalNutritionFusionNet(num_classes=12)
    model.eval()
    dummy_img = torch.randn(1, 3, 224, 224)

    label, conf, doses = model.predict(image_tensor=dummy_img, sensor_tensor=None)
    assert label in DEFICIENCY_CLASSES
    assert 0.0 <= conf <= 1.0
    assert len(doses) == 3


# ------------------------------------------------------------------
# 4. End-to-End Nutrition Agent Tests
# ------------------------------------------------------------------

def test_nutrition_agent_sensor_diagnosis():
    agent = NutritionAgent()
    sensor_dict = {
        "nitrogen": 140.0,
        "phosphorus": 8.0,
        "potassium": 160.0,
        "ph": 6.5,
        "electrical_conductivity": 0.6,
        "soil_moisture": 35.0,
    }
    report = agent.diagnose(sensor_data=sensor_dict, crop="Tomato", language="en")
    assert isinstance(report, NutritionReport)
    assert report.input_modality == "sensor_only"
    assert report.prediction.confidence > 0.0
    assert report.fertilizer_recommendation.urea_kg_acre > 0.0
    assert "Tomato" in report.advisory
    assert len(report.citations) >= 2


def test_nutrition_agent_hindi_localization():
    agent = NutritionAgent()
    sensor_dict = {
        "nitrogen": 130.0,
        "phosphorus": 12.0,
        "potassium": 180.0,
        "ph": 6.8,
        "electrical_conductivity": 0.5,
        "soil_moisture": 40.0,
    }
    report = agent.diagnose(sensor_data=sensor_dict, crop="Wheat", language="hi")
    assert "फसल: Wheat" in report.advisory
    assert "यूरिया" in report.advisory


# ------------------------------------------------------------------
# 5. LangGraph Node Integration Tests
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_nutrition_agent_node_execution():
    state = {
        "query": "My wheat field has low nitrogen and yellowing, recommend fertilizer dose",
        "sensor_data": {"N": 160.0, "P": 18.0, "K": 170.0, "pH": 6.6, "EC": 0.55, "moisture": 38.0},
        "image_bytes": None,
        "active_crop": "Wheat",
        "language": "en",
    }
    output = await nutrition_agent_node(state)
    assert "nutrition_data" in output
    assert len(output["agent_results"]) == 1
    assert output["agent_results"][0]["agent"] == "nutrition_agent"
    assert output["agent_results"][0]["urea_kg_acre"] > 0.0


# ------------------------------------------------------------------
# 6. LangGraph StateGraph Orchestration Workflow Test
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_langgraph_stategraph_nutrition_workflow():
    graph = create_agrisys_graph()
    initial_state = {
        "query": "How much urea and dap fertilizer dose should I apply for nitrogen deficiency in tomato?",
        "image_bytes": None,
        "image_path": None,
        "sensor_data": {"N": 140.0, "P": 12.0, "K": 150.0, "pH": 6.7, "EC": 0.6, "moisture": 40.0},
        "voice_audio_path": None,
        "language": "en",
        "location": {"state": "Uttar Pradesh"},
        "session_id": "test_nutrition_session",
        "turn_number": 1,
        "history": [],
        "intents": [],
        "active_agents": [],
        "active_crop": "Tomato",
        "agent_results": [],
        "rag_chunks": [],
        "citations": [],
        "grad_cam_path": None,
        "shap_values": None,
        "diagram_code": None,
        "diagram_type": None,
        "svg_schematic": None,
        "diagnostic_report": None,
        "crop_data": None,
        "nutrition_data": None,
        "merged_response": "",
        "confidence_score": 0.0,
        "hallucination_score": 1.0,
        "escalate": False,
        "tts_audio_path": None,
    }

    final_state = await graph.ainvoke(initial_state)
    assert "nutrition" in final_state["intents"]
    assert final_state["nutrition_data"] is not None
    assert any(res["agent"] == "nutrition_agent" for res in final_state["agent_results"])
    assert len(final_state["merged_response"]) > 20


# ------------------------------------------------------------------
# 7. FastAPI Endpoint Test
# ------------------------------------------------------------------

def test_api_nutrition_diagnose_endpoint():
    client = TestClient(app)
    payload = {
        "crop": "Tomato",
        "sensor_data": {
            "nitrogen": 175.0,
            "phosphorus": 14.0,
            "potassium": 155.0,
            "ph": 6.7,
            "electrical_conductivity": 0.65,
            "soil_moisture": 42.0,
        },
        "language": "en",
    }
    response = client.post("/api/nutrition/diagnose", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["crop"] == "Tomato"
    assert "prediction" in data
    assert "fertilizer_recommendation" in data
    assert data["fertilizer_recommendation"]["urea_kg_ha"] > 0.0
