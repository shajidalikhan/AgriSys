"""Comprehensive unit and integration tests for Stage 6: Weather & Irrigation Advisory Agent."""

import pytest
from fastapi.testclient import TestClient

from agrisys.agents.weather.models import (
    DailyWeatherForecast,
    EToCalculationResult,
    WeatherAlert,
    WeatherReport,
)
from agrisys.agents.weather.eto_calculator import (
    FAO56PenmanMonteithCalculator,
    FAO56_CROP_KC,
)
from agrisys.agents.weather.alerts import WeatherAlertEngine
from agrisys.agents.weather.client import WeatherClient
from agrisys.agents.weather.agent import WeatherAgent
from agrisys.agents.weather.node import weather_agent_node
from agrisys.orchestrator.graph import create_agrisys_graph
from agrisys.api.main import app


# ------------------------------------------------------------------
# 1. FAO-56 Penman-Monteith Calculation Tests
# ------------------------------------------------------------------

def test_fao56_eto_penman_monteith_calculation():
    calc = FAO56PenmanMonteithCalculator()
    # Typical Northern Indian subtropical summer day
    et0 = calc.calculate_et0(
        temp_max=36.0,
        temp_min=24.0,
        relative_humidity=55.0,
        wind_speed_ms=2.5,
        solar_radiation_mj=20.0,
        elevation_m=120.0,
    )
    # Reference ET0 for warm summer conditions typically ranges between 4.0 and 7.5 mm/day
    assert 4.0 <= et0 <= 8.0


def test_crop_water_requirement_and_irrigation():
    res = FAO56PenmanMonteithCalculator.calculate_irrigation_requirement(
        crop="Wheat",
        stage="Mid",
        temp_max=28.0,
        temp_min=14.0,
        relative_humidity=60.0,
        wind_speed_ms=2.0,
        precipitation_mm=0.0,
        solar_radiation_mj=18.0,
    )

    assert res.crop == "Wheat"
    assert res.crop_kc == 1.15  # Wheat mid-season Kc
    assert res.etc_mm_day == pytest.approx(res.et0_mm_day * 1.15, rel=1e-2)
    assert res.effective_rainfall_mm == 0.0
    assert res.net_irrigation_requirement_mm == res.etc_mm_day
    assert res.recommended_drip_runtime_hours == pytest.approx(res.net_irrigation_requirement_mm / 4.0, rel=1e-2)


def test_effective_rainfall_deduction():
    # Significant rainfall (30 mm) should reduce net irrigation requirement
    res = FAO56PenmanMonteithCalculator.calculate_irrigation_requirement(
        crop="Tomato",
        stage="Mid",
        temp_max=30.0,
        temp_min=20.0,
        relative_humidity=75.0,
        wind_speed_ms=2.0,
        precipitation_mm=30.0,
        solar_radiation_mj=16.0,
    )
    assert res.effective_rainfall_mm > 15.0
    # Net requirement should be zeroed out or greatly diminished
    assert res.net_irrigation_requirement_mm <= res.etc_mm_day


# ------------------------------------------------------------------
# 2. Extreme Weather Agricultural Hazard Alert Tests
# ------------------------------------------------------------------

def test_weather_alerts_frost_detection():
    dummy_forecasts = [
        DailyWeatherForecast(
            date="2026-01-10",
            temp_max=16.0,
            temp_min=2.5,  # Dip below 4.0°C
            temp_mean=9.2,
            relative_humidity=70.0,
            wind_speed_ms=1.2,
            precipitation_mm=0.0,
        )
    ]
    alerts = WeatherAlertEngine.detect_alerts(dummy_forecasts)
    assert len(alerts) >= 1
    assert alerts[0].alert_type == "FROST"
    assert alerts[0].severity in ["WARNING", "ADVISORY"]
    assert "Frost" in alerts[0].headline


def test_weather_alerts_heatwave_detection():
    dummy_forecasts = [
        DailyWeatherForecast(
            date="2026-05-20",
            temp_max=44.5,  # Extreme heat > 40°C
            temp_min=29.0,
            temp_mean=36.7,
            relative_humidity=30.0,
            wind_speed_ms=3.0,
            precipitation_mm=0.0,
        )
    ]
    alerts = WeatherAlertEngine.detect_alerts(dummy_forecasts)
    assert len(alerts) >= 1
    assert alerts[0].alert_type == "HEATWAVE"
    assert "Heatwave" in alerts[0].headline


def test_weather_alerts_heavy_rainfall_detection():
    dummy_forecasts = [
        DailyWeatherForecast(
            date="2026-07-15",
            temp_max=31.0,
            temp_min=24.0,
            temp_mean=27.5,
            relative_humidity=90.0,
            wind_speed_ms=4.0,
            precipitation_mm=55.0,  # Heavy downpour > 35mm
        )
    ]
    alerts = WeatherAlertEngine.detect_alerts(dummy_forecasts)
    assert any(a.alert_type == "HEAVY_RAINFALL" for a in alerts)


# ------------------------------------------------------------------
# 3. Weather Client & Fallback Chain Tests
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_weather_client_fetch_forecast():
    client = WeatherClient()
    forecasts, source = await client.fetch_forecast_7d(lat=26.85, lon=80.95, district="Lucknow")

    assert len(forecasts) >= 7
    assert source in ["OPEN_METEO", "REDIS_CACHE", "LOCAL_OFFLINE", "IMD_API"]
    assert forecasts[0].temp_max > forecasts[0].temp_min
    assert forecasts[0].relative_humidity >= 0.0


# ------------------------------------------------------------------
# 4. End-to-End Weather Agent Tests
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_weather_agent_get_advisory_english():
    agent = WeatherAgent()
    report = await agent.get_advisory(
        crop="Wheat",
        crop_stage="Mid",
        latitude=26.85,
        longitude=80.95,
        location_name="Lucknow, Uttar Pradesh",
        language="en",
    )

    assert isinstance(report, WeatherReport)
    assert report.eto_analysis.crop == "Wheat"
    assert report.eto_analysis.et0_mm_day > 0.0
    assert len(report.forecast_7d) >= 7
    assert len(report.citations) >= 2
    assert "irrigation" in report.irrigation_advice.lower() or "moisture" in report.irrigation_advice.lower()


@pytest.mark.asyncio
async def test_weather_agent_get_advisory_hindi():
    agent = WeatherAgent()
    report = await agent.get_advisory(
        crop="Tomato",
        crop_stage="Mid",
        latitude=26.85,
        longitude=80.95,
        location_name="Lucknow, Uttar Pradesh",
        language="hi",
    )

    assert "स्थान: Lucknow" in report.advisory_text
    assert "वाष्पोत्सर्जन" in report.advisory_text
    assert "सिंचाई सलाह" in report.advisory_text


# ------------------------------------------------------------------
# 5. LangGraph State Node & Workflow Tests
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_weather_agent_node_execution():
    state = {
        "query": "What is the 7-day weather forecast for wheat in Lucknow and how much irrigation is needed?",
        "active_crop": "Wheat",
        "location": {"latitude": 26.8467, "longitude": 80.9462, "state": "Uttar Pradesh"},
        "language": "en",
    }
    output = await weather_agent_node(state)
    assert "weather_data" in output
    assert len(output["agent_results"]) == 1
    assert output["agent_results"][0]["agent"] == "weather_agent"
    assert output["agent_results"][0]["et0_mm_day"] > 0.0


@pytest.mark.asyncio
async def test_langgraph_stategraph_weather_workflow():
    graph = create_agrisys_graph()
    initial_state = {
        "query": "Will it rain in Lucknow this week and should I irrigate my wheat crop?",
        "image_bytes": None,
        "image_path": None,
        "sensor_data": None,
        "voice_audio_path": None,
        "language": "en",
        "location": {"latitude": 26.8467, "longitude": 80.9462, "state": "Uttar Pradesh"},
        "session_id": "test_weather_session",
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
        "weather_data": None,
        "merged_response": "",
        "confidence_score": 0.0,
        "hallucination_score": 1.0,
        "escalate": False,
        "tts_audio_path": None,
    }

    final_state = await graph.ainvoke(initial_state)
    assert "weather" in final_state["intents"]
    assert final_state["weather_data"] is not None
    assert any(res["agent"] == "weather_agent" for res in final_state["agent_results"])
    assert len(final_state["merged_response"]) > 20


# ------------------------------------------------------------------
# 6. FastAPI Endpoint Test
# ------------------------------------------------------------------

def test_api_weather_forecast_endpoint():
    client = TestClient(app)
    payload = {
        "crop": "Wheat",
        "crop_stage": "Mid",
        "latitude": 26.8467,
        "longitude": 80.9462,
        "location_name": "Lucknow, Uttar Pradesh",
        "language": "en",
    }
    response = client.post("/api/weather/forecast", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["location_name"] == "Lucknow, Uttar Pradesh"
    assert "eto_analysis" in data
    assert data["eto_analysis"]["et0_mm_day"] > 0.0
    assert len(data["forecast_7d"]) >= 7
