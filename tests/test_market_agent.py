"""Comprehensive unit and integration tests for Stage 5: Market Price Intelligence Agent."""

import pytest
from fastapi.testclient import TestClient

from agrisys.agents.market.models import (
    MandiRecord,
    PriceForecastPoint,
    MSPComparison,
    MarketAdvisoryReport,
)
from agrisys.agents.market.msp_database import compare_msp, CACP_MSP_DATABASE
from agrisys.agents.market.anomaly_filter import IQRAnomalyFilter
from agrisys.agents.market.haversine_ranker import (
    HaversineMandiRanker,
    haversine_distance,
    MANDI_DIRECTORY,
)
from agrisys.agents.market.forecaster import (
    StatisticalPriceForecaster,
    ProphetPriceForecaster,
)
from agrisys.agents.market.agent import MarketAgent
from agrisys.agents.market.node import market_agent_node
from agrisys.orchestrator.graph import create_agrisys_graph
from agrisys.api.main import app


# ------------------------------------------------------------------
# 1. IQR Anomaly Filter Tests
# ------------------------------------------------------------------

def test_iqr_anomaly_filter_removes_outliers():
    filter_engine = IQRAnomalyFilter(iqr_multiplier=1.5)
    # Normal prices ~ ₹2000/q with an extreme data entry typo (₹45,000/q)
    prices = [1900.0, 1950.0, 2050.0, 2000.0, 2100.0, 1980.0, 45000.0, 2020.0]
    filtered = filter_engine.filter_outliers(prices)

    assert 45000.0 not in filtered
    assert len(filtered) == 7
    assert all(1800.0 <= p <= 2200.0 for p in filtered)


def test_iqr_anomaly_filter_mask():
    filter_engine = IQRAnomalyFilter()
    prices = [2000.0, 2050.0, 1980.0, 2010.0, 50000.0]
    mask = filter_engine.detect_anomalies(prices)
    assert mask[-1] is True
    assert mask[0] is False


# ------------------------------------------------------------------
# 2. CACP MSP Comparison Tests
# ------------------------------------------------------------------

def test_cacp_msp_comparison_above_msp():
    # Wheat MSP is ₹2,275
    comp = compare_msp(commodity="Wheat", current_price_quintal=2550.0)
    assert comp.status == "ABOVE_MSP"
    assert comp.msp_price == 2275.0
    assert comp.diff_percentage > 0.0
    assert "ABOVE" in comp.guidance


def test_cacp_msp_comparison_below_msp():
    # Paddy MSP is ₹2,300
    comp = compare_msp(commodity="Paddy", current_price_quintal=2050.0)
    assert comp.status == "BELOW_MSP"
    assert comp.msp_price == 2300.0
    assert comp.diff_percentage < 0.0
    assert "distress" in comp.guidance.lower() or "procurement" in comp.guidance.lower()


def test_cacp_msp_comparison_no_msp_commodity():
    comp = compare_msp(commodity="Tomato", current_price_quintal=1800.0)
    assert comp.status == "NO_MSP_ANNOUNCED"
    assert comp.msp_price is None


# ------------------------------------------------------------------
# 3. Haversine Distance & Mandi Ranker Tests
# ------------------------------------------------------------------

def test_haversine_distance_known_coordinates():
    # Lucknow APMC (26.89, 80.93) to Kanpur APMC (26.41, 80.33)
    dist = haversine_distance(26.8900, 80.9300, 26.4100, 80.3300)
    # Expected distance is ~80 km
    assert 70.0 <= dist <= 95.0


def test_haversine_mandi_ranker_logistics_deduction():
    ranker = HaversineMandiRanker(freight_per_quintal_km=0.25)
    origin_lat, origin_lon = 26.8467, 80.9462  # Lucknow

    ranked = ranker.rank_mandis(
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        commodity="Tomato",
        top_k=5,
    )

    assert len(ranked) == 5
    # First ranked must have highest net realization price
    assert ranked[0].net_realization_price >= ranked[1].net_realization_price
    for mandi in ranked:
        assert mandi.distance_km >= 0.0
        assert mandi.estimated_transport_cost == pytest.approx(mandi.distance_km * 0.25, rel=1e-2)
        assert mandi.net_realization_price == pytest.approx(mandi.modal_price - mandi.estimated_transport_cost, rel=1e-2)


# ------------------------------------------------------------------
# 4. 7-Day Mandi Price Forecasting Tests
# ------------------------------------------------------------------

def test_statistical_price_forecaster_7_days():
    forecaster = StatisticalPriceForecaster()
    points = forecaster.forecast(base_price=2200.0, horizon_days=7)

    assert len(points) == 7
    for i, pt in enumerate(points, start=1):
        assert pt.day_offset == i
        assert pt.projected_modal_price > 0.0
        assert pt.lower_bound <= pt.projected_modal_price <= pt.upper_bound


def test_prophet_adapter_fallback():
    forecaster = ProphetPriceForecaster()
    points = forecaster.forecast(base_price=2400.0, horizon_days=7)
    assert len(points) == 7
    assert points[0].projected_modal_price > 0.0


# ------------------------------------------------------------------
# 5. End-to-End Market Agent Tests
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_market_agent_advise_english():
    agent = MarketAgent()
    report = await agent.advise(commodity="Tomato", origin_lat=26.85, origin_lon=80.95, language="en")

    assert isinstance(report, MarketAdvisoryReport)
    assert report.commodity == "Tomato"
    assert report.current_modal_price_kg > 0.0
    assert report.recommendation in ["SELL_NOW", "HOLD", "TRANSPORT_TO_MANDI"]
    assert report.trend_direction in ["RISING", "FALLING", "STABLE"]
    assert len(report.top_mandis) == 5
    assert len(report.forecast_7d) == 7
    assert len(report.citations) >= 2


@pytest.mark.asyncio
async def test_market_agent_advise_hindi():
    agent = MarketAgent()
    report = await agent.advise(commodity="Wheat", origin_lat=26.85, origin_lon=80.95, language="hi")

    assert "फसल: Wheat" in report.advisory_text
    assert "क्विंटल" in report.advisory_text


# ------------------------------------------------------------------
# 6. LangGraph State Node & Workflow Tests
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_market_agent_node_execution():
    state = {
        "query": "What is the tomato mandi rate in Lucknow and should I sell or hold?",
        "active_crop": "Tomato",
        "location": {"latitude": 26.8467, "longitude": 80.9462, "state": "Uttar Pradesh"},
        "language": "en",
    }
    output = await market_agent_node(state)
    assert "market_data" in output
    assert len(output["agent_results"]) == 1
    assert output["agent_results"][0]["agent"] == "market_agent"
    assert output["agent_results"][0]["recommendation"] in ["SELL_NOW", "HOLD", "TRANSPORT_TO_MANDI"]


@pytest.mark.asyncio
async def test_langgraph_stategraph_market_workflow():
    graph = create_agrisys_graph()
    initial_state = {
        "query": "What is the mandi price and bhav for wheat today, should I sell?",
        "image_bytes": None,
        "image_path": None,
        "sensor_data": None,
        "voice_audio_path": None,
        "language": "en",
        "location": {"latitude": 26.8467, "longitude": 80.9462, "state": "Uttar Pradesh"},
        "session_id": "test_market_session",
        "turn_number": 1,
        "history": [],
        "intents": [],
        "active_agents": [],
        "active_crop": "Wheat",
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
        "market_data": None,
        "merged_response": "",
        "confidence_score": 0.0,
        "hallucination_score": 1.0,
        "escalate": False,
        "tts_audio_path": None,
    }

    final_state = await graph.ainvoke(initial_state)
    assert "market" in final_state["intents"]
    assert final_state["market_data"] is not None
    assert any(res["agent"] == "market_agent" for res in final_state["agent_results"])
    assert len(final_state["merged_response"]) > 20


# ------------------------------------------------------------------
# 7. FastAPI Endpoint Test
# ------------------------------------------------------------------

def test_api_market_advisory_endpoint():
    client = TestClient(app)
    payload = {
        "commodity": "Tomato",
        "latitude": 26.8467,
        "longitude": 80.9462,
        "location_name": "Lucknow, Uttar Pradesh",
        "language": "en",
    }
    response = client.post("/api/market/advisory", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["commodity"] == "Tomato"
    assert "recommendation" in data
    assert "msp_analysis" in data
    assert len(data["top_mandis"]) > 0
    assert len(data["forecast_7d"]) == 7
