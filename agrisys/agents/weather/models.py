"""Pydantic data models and schemas for Weather & Irrigation Advisory Agent."""

from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class DailyWeatherForecast(BaseModel):
    """Meteorological forecast for a single calendar day."""
    date: str = Field(..., description="Calendar date (YYYY-MM-DD)")
    temp_max: float = Field(..., description="Maximum temperature (°C)")
    temp_min: float = Field(..., description="Minimum temperature (°C)")
    temp_mean: float = Field(..., description="Mean temperature (°C)")
    relative_humidity: float = Field(..., ge=0.0, le=100.0, description="Mean relative humidity (%)")
    wind_speed_ms: float = Field(..., ge=0.0, description="Wind speed at 2m height (m/s)")
    precipitation_mm: float = Field(..., ge=0.0, description="Expected precipitation (mm)")
    precipitation_probability: float = Field(default=0.0, ge=0.0, le=100.0, description="Chance of rain (%)")
    solar_radiation_mj: float = Field(default=18.0, ge=0.0, description="Solar radiation (MJ/m²/day)")
    condition_summary: str = Field(default="Clear", description="Sky condition summary")


class EToCalculationResult(BaseModel):
    """FAO-56 Penman-Monteith Evapotranspiration and crop water requirements."""
    et0_mm_day: float = Field(..., ge=0.0, description="Reference crop evapotranspiration ET0 (mm/day)")
    crop: str = Field(..., description="Target crop name")
    crop_growth_stage: str = Field(..., description="Crop growth stage (Initial, Mid, Late)")
    crop_kc: float = Field(..., ge=0.0, description="Crop coefficient Kc for the growth stage")
    etc_mm_day: float = Field(..., ge=0.0, description="Actual crop evapotranspiration ETc (mm/day)")
    effective_rainfall_mm: float = Field(..., ge=0.0, description="Expected effective rainfall (mm)")
    net_irrigation_requirement_mm: float = Field(
        ..., ge=0.0, description="Net irrigation depth required (mm)"
    )
    recommended_drip_runtime_hours: float = Field(
        ..., ge=0.0, description="Estimated drip irrigation run time (hours)"
    )


class WeatherAlert(BaseModel):
    """Agricultural meteorological hazard alert."""
    alert_type: Literal["FROST", "HEATWAVE", "HEAVY_RAINFALL", "HIGH_WIND", "NONE"] = Field(
        ..., description="Type of weather hazard"
    )
    severity: Literal["NORMAL", "WATCH", "ADVISORY", "WARNING"] = Field(
        ..., description="Alert severity level"
    )
    headline: str = Field(..., description="Brief headline of the alert")
    description: str = Field(..., description="Detailed explanation of meteorological trigger")
    protective_action: str = Field(..., description="Agronomic countermeasures to prevent crop damage")


class WeatherReport(BaseModel):
    """Complete synthesized weather and irrigation advisory report."""
    location_name: str = Field(..., description="Target region / district name")
    latitude: float = Field(..., description="Geographic latitude")
    longitude: float = Field(..., description="Geographic longitude")
    data_source: Literal["IMD_API", "OPEN_METEO", "REDIS_CACHE", "LOCAL_OFFLINE"] = Field(
        ..., description="Meteorological tier that satisfied the request"
    )
    current_temp: float = Field(..., description="Current ambient temperature (°C)")
    current_condition: str = Field(..., description="Current weather condition")
    forecast_7d: list[DailyWeatherForecast] = Field(
        default_factory=list, description="7-day daily weather projections"
    )
    eto_analysis: EToCalculationResult
    active_alerts: list[WeatherAlert] = Field(
        default_factory=list, description="Active extreme weather hazard warnings"
    )
    irrigation_advice: str = Field(..., description="Specific irrigation schedule guidance")
    advisory_text: str = Field(..., description="Synthesized farmer advisory")
    citations: list[str] = Field(default_factory=list, description="Authoritative meteorological citations")
