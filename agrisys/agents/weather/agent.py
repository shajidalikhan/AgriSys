"""Master Weather & Precision Irrigation Advisory Agent coordinating forecasts, ETo, and hazard alerts."""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

from agrisys.agents.weather.models import (
    DailyWeatherForecast,
    EToCalculationResult,
    WeatherAlert,
    WeatherReport,
)
from agrisys.agents.weather.client import WeatherClient
from agrisys.agents.weather.eto_calculator import FAO56PenmanMonteithCalculator
from agrisys.agents.weather.alerts import WeatherAlertEngine
from agrisys.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class WeatherAgent:
    """Coordinates meteorological ingestion, FAO-56 ETo modeling, hazard alerts, and irrigation advisories."""

    def __init__(
        self,
        client: WeatherClient | None = None,
        llm_provider: BaseLLMProvider | None = None,
    ):
        self.client = client or WeatherClient()
        self.llm_provider = llm_provider
        self.alert_engine = WeatherAlertEngine()

    async def get_advisory(
        self,
        crop: str = "Wheat",
        crop_stage: str = "Mid",
        latitude: float = 26.8467,  # Default: Lucknow
        longitude: float = 80.9462,
        location_name: str = "Lucknow, Uttar Pradesh",
        language: str = "en",
    ) -> WeatherReport:
        """
        Executes end-to-end weather forecasting and irrigation recommendation.
        """
        # 1. Fetch 7-day meteorological forecast via 4-tier fallback
        forecasts, source = await self.client.fetch_forecast_7d(
            lat=latitude,
            lon=longitude,
            district=location_name,
        )

        today_forecast = forecasts[0] if forecasts else None
        current_temp = today_forecast.temp_mean if today_forecast else 25.0
        current_cond = today_forecast.condition_summary if today_forecast else "Clear"

        # 2. Compute FAO-56 Penman-Monteith ETo & Crop Water Demand
        eto_result = FAO56PenmanMonteithCalculator.calculate_irrigation_requirement(
            crop=crop,
            stage=crop_stage,
            temp_max=today_forecast.temp_max if today_forecast else 32.0,
            temp_min=today_forecast.temp_min if today_forecast else 20.0,
            relative_humidity=today_forecast.relative_humidity if today_forecast else 65.0,
            wind_speed_ms=today_forecast.wind_speed_ms if today_forecast else 2.0,
            precipitation_mm=today_forecast.precipitation_mm if today_forecast else 0.0,
            solar_radiation_mj=today_forecast.solar_radiation_mj if today_forecast else 18.0,
        )

        # 3. Detect agricultural weather alerts across 7 days
        alerts = self.alert_engine.detect_alerts(forecasts)

        # 4. Formulate Irrigation Decision
        # Check upcoming 3 days precipitation
        upcoming_3d_rain = sum(f.precipitation_mm for f in forecasts[:3])
        if upcoming_3d_rain >= 15.0:
            irrigation_advice = (
                f"POSTPONE IRRIGATION: Expected rainfall of {upcoming_3d_rain:.1f} mm over the next 48-72 hours "
                f"will satisfy root-zone soil moisture. Check field drainage."
            )
        elif eto_result.net_irrigation_requirement_mm > 0.0:
            irrigation_advice = (
                f"IRRIGATION RECOMMENDED: Apply {eto_result.net_irrigation_requirement_mm:.1f} mm depth "
                f"({eto_result.recommended_drip_runtime_hours:.1f} hours drip runtime) within 36 hours. "
                f"Reference ET₀ is {eto_result.et0_mm_day:.1f} mm/day."
            )
        else:
            irrigation_advice = (
                "ADEQUATE MOISTURE: Recent or ongoing precipitation is sufficient. No supplemental irrigation needed today."
            )

        # 5. Format Synthesized Farmer Advisory Text
        advisory_text = self._format_advisory(
            crop=crop,
            location_name=location_name,
            current_temp=current_temp,
            current_cond=current_cond,
            eto_result=eto_result,
            alerts=alerts,
            irrigation_advice=irrigation_advice,
            upcoming_rain=upcoming_3d_rain,
            language=language,
        )

        citations = [
            f"Meteorological Feed: {source}",
            "FAO-56 Irrigation and Drainage Paper: Crop Evapotranspiration Guidelines",
            "India Meteorological Department (IMD) Agromet Advisory Services (AAS)",
        ]

        return WeatherReport(
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            data_source=source,  # type: ignore
            current_temp=current_temp,
            current_condition=current_cond,
            forecast_7d=forecasts,
            eto_analysis=eto_result,
            active_alerts=alerts,
            irrigation_advice=irrigation_advice,
            advisory_text=advisory_text,
            citations=citations,
        )

    def _format_advisory(
        self,
        crop: str,
        location_name: str,
        current_temp: float,
        current_cond: float | str,
        eto_result: EToCalculationResult,
        alerts: list[WeatherAlert],
        irrigation_advice: str,
        upcoming_rain: float,
        language: str,
    ) -> str:
        """Constructs bilingual advisory text in English or Hindi."""
        primary_alert = alerts[0] if alerts else None
        has_critical_alert = primary_alert and primary_alert.alert_type != "NONE"

        if language == "hi":
            alert_str = f"⚠️ मौसम चेतावनी: {primary_alert.headline}\nसुझाव: {primary_alert.protective_action}\n" if has_critical_alert else "मौसम अनुकूल है।"
            return (
                f"स्थान: {location_name} | फसल: {crop} ({eto_result.crop_growth_stage} अवस्था)\n"
                f"वर्तमान तापमान: {current_temp:.1f}°C ({current_cond})\n"
                f"वाष्पोत्सर्जन (ET₀): {eto_result.et0_mm_day:.1f} मिमी/दिन | फसल जल मांग (ETc): {eto_result.etc_mm_day:.1f} मिमी/दिन\n"
                f"अगले 3 दिनों में संभावित वर्षा: {upcoming_rain:.1f} मिमी\n\n"
                f"सिंचाई सलाह: {irrigation_advice}\n\n"
                f"{alert_str}"
            )
        else:
            alert_str = f"⚠️ HAZARD WARNING: {primary_alert.headline}\nAction Required: {primary_alert.protective_action}\n" if has_critical_alert else "Normal weather conditions prevail."
            return (
                f"Region: {location_name} | Crop: {crop} ({eto_result.crop_growth_stage} Stage)\n"
                f"Current Ambient Temperature: {current_temp:.1f}°C ({current_cond})\n"
                f"Reference ET₀: {eto_result.et0_mm_day:.1f} mm/day | Crop Demand (ETc): {eto_result.etc_mm_day:.1f} mm/day\n"
                f"Anticipated 72h Precipitation: {upcoming_rain:.1f} mm\n\n"
                f"Precision Irrigation Advisory: {irrigation_advice}\n\n"
                f"{alert_str}"
            )
