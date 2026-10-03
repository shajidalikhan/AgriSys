"""Unit and integration tests for Crop Recommendation Agent, SHAP, and Simulator."""

import pytest
from agrisys.agents.crop.models import (
    CropInputFeatures,
    SeasonEnum,
    WaterSourceEnum,
    WhatIfSimulationRequest,
)
from agrisys.agents.crop.registry import (
    CROP_MODEL_REGISTRY,
    get_crop_tool,
    register_crop_tool,
)
from agrisys.agents.crop.xgb_tool import LocalXGBoostCropModelTool
from agrisys.agents.crop.rf_tool import LocalRandomForestCropModelTool
from agrisys.agents.crop.ensemble import CropEnsembleVoter
from agrisys.agents.crop.feasibility_guard import CropFeasibilityGuard
from agrisys.agents.crop.simulator import CropSimulationService
from agrisys.agents.crop.agent import CropRecommendationAgent
from agrisys.xai.shap_explainer import CropSHAPExplainer


@pytest.fixture
def sample_features() -> CropInputFeatures:
    """Standard alluvial soil features favoring rice or cotton."""
    return CropInputFeatures(
        N=90.0,
        P=42.0,
        K=43.0,
        temperature=25.0,
        humidity=82.0,
        ph=6.5,
        rainfall=200.0,
        season=SeasonEnum.KHARIF,
        water_availability=WaterSourceEnum.CANAL_IRRIGATED,
        state="Punjab",
    )


def test_crop_input_features_validation():
    """Test validation constraints on agronomic inputs."""
    feat = CropInputFeatures(
        N=50.0, P=50.0, K=50.0, temperature=24.0, humidity=80.0, ph=6.5, rainfall=100.0
    )
    arr = feat.to_feature_array()
    assert len(arr) == 7
    assert arr[0] == 50.0

    # Test out of range pH
    with pytest.raises(ValueError):
        CropInputFeatures(
            N=50.0, P=50.0, K=50.0, temperature=24.0, humidity=80.0, ph=14.0, rainfall=100.0
        )


@pytest.mark.asyncio
async def test_local_xgb_tool_prediction(sample_features):
    """Test local XGBoost crop model inference."""
    tool = LocalXGBoostCropModelTool()
    preds = await tool.predict(sample_features)
    assert len(preds) > 0
    winner_crop, winner_prob = preds[0]
    assert isinstance(winner_crop, str)
    assert 0.0 <= winner_prob <= 1.0
    # Probabilities should sum approximately to 1.0
    total_p = sum(p for _, p in preds)
    assert 0.95 <= total_p <= 1.05


@pytest.mark.asyncio
async def test_local_rf_tool_prediction(sample_features):
    """Test local Random Forest crop model inference."""
    tool = LocalRandomForestCropModelTool()
    preds = await tool.predict(sample_features)
    assert len(preds) > 0
    winner_crop, winner_prob = preds[0]
    assert isinstance(winner_crop, str)
    assert 0.0 <= winner_prob <= 1.0


def test_crop_ensemble_voter():
    """Test weighted probability ensemble voter."""
    voter = CropEnsembleVoter(weights={"xgb": 0.60, "rf": 0.40})
    tool_preds = {
        "xgb": [("rice", 0.70), ("maize", 0.30)],
        "rf": [("rice", 0.80), ("maize", 0.20)],
    }
    voted = voter.vote(tool_preds)
    assert voted[0][0] == "rice"
    expected_rice = 0.60 * 0.70 + 0.40 * 0.80  # 0.42 + 0.32 = 0.74
    assert pytest.approx(voted[0][1], 0.01) == expected_rice


def test_crop_feasibility_guard():
    """Test feasibility filtering for off-season and water-deficit conditions."""
    guard = CropFeasibilityGuard()

    # 1. Optimal rice in kharif with irrigation
    feat_good = CropInputFeatures(
        N=80.0, P=40.0, K=40.0, temperature=24.0, humidity=80.0, ph=6.5, rainfall=250.0,
        season=SeasonEnum.KHARIF, water_availability=WaterSourceEnum.CANAL_IRRIGATED
    )
    status_good = guard.evaluate("rice", 0.85, feat_good)
    assert status_good.is_feasible is True
    assert len(status_good.flags) == 0

    # 2. Rice under severe rainfed drought
    feat_deficit = CropInputFeatures(
        N=80.0, P=40.0, K=40.0, temperature=24.0, humidity=80.0, ph=6.5, rainfall=150.0,
        season=SeasonEnum.KHARIF, water_availability=WaterSourceEnum.RAINFED
    )
    status_deficit = guard.evaluate("rice", 0.85, feat_deficit)
    assert any("Water deficit" in f for f in status_deficit.flags)
    assert status_deficit.suitability_score < 0.85


def test_crop_shap_explainer(sample_features):
    """Test SHAP TreeExplainer feature attributions and bilingual labels."""
    tool = LocalXGBoostCropModelTool()
    explainer = CropSHAPExplainer(tool.model, tool.label_mapping)
    res = explainer.explain(sample_features.to_feature_array(), target_crop_index=0, language="hi")

    assert "feature_contributions" in res
    assert len(res["feature_contributions"]) == 7
    # Bilingual label presence
    first_contrib = res["feature_contributions"][0]
    assert "(" in first_contrib["label"] or "नाइट्रोजन" in first_contrib["label"] or "N" in first_contrib["label"]


@pytest.mark.asyncio
async def test_what_if_simulator(sample_features):
    """Test What-If sensitivity simulation when modifying rainfall and nitrogen."""
    simulator = CropSimulationService()
    req = WhatIfSimulationRequest(
        base_features=sample_features,
        delta_features={"rainfall": -150.0, "N": -50.0}
    )
    res = await simulator.simulate(req)
    assert isinstance(res.original_winner, str)
    assert isinstance(res.simulated_winner, str)
    assert isinstance(res.probability_shifts, dict)
    assert len(res.agronomic_verdict) > 10


@pytest.mark.asyncio
async def test_crop_recommendation_agent_end_to_end(sample_features):
    """Test end-to-end CropRecommendationAgent output report."""
    agent = CropRecommendationAgent()
    output = await agent.recommend(sample_features, top_k=3, language="hi")
    assert len(output.top_recommendations) == 3
    assert output.winning_crop == output.top_recommendations[0].crop_name
    assert output.overall_confidence > 0.0
    assert output.advisory_text != ""
