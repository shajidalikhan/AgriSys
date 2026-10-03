"""Pydantic data models and schemas for Market Price Intelligence Agent."""

from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class MandiRecord(BaseModel):
    """Specific APMC mandi price and arrival record."""
    mandi_name: str = Field(..., description="Name of APMC Mandi")
    district: str = Field(..., description="District name")
    state: str = Field(..., description="State name")
    commodity: str = Field(..., description="Commodity / crop name")
    arrival_date: str = Field(..., description="Arrival record date (ISO string)")
    min_price: float = Field(..., ge=0.0, description="Minimum reported price (₹/quintal)")
    max_price: float = Field(..., ge=0.0, description="Maximum reported price (₹/quintal)")
    modal_price: float = Field(..., ge=0.0, description="Modal transaction price (₹/quintal)")
    latitude: float = Field(..., description="Geographic latitude of mandi")
    longitude: float = Field(..., description="Geographic longitude of mandi")
    distance_km: float = Field(default=0.0, ge=0.0, description="Geodesic distance from farmer location (km)")
    estimated_transport_cost: float = Field(
        default=0.0, ge=0.0, description="Estimated freight cost per quintal (₹/quintal)"
    )
    net_realization_price: float = Field(
        default=0.0, ge=0.0, description="Net price realized after logistics (₹/quintal)"
    )


class PriceForecastPoint(BaseModel):
    """Single point in a 7-day price trajectory forecast."""
    day_offset: int = Field(..., ge=1, le=7, description="Forecast horizon day index (1 to 7)")
    date: str = Field(..., description="Forecast calendar date (YYYY-MM-DD)")
    projected_modal_price: float = Field(..., ge=0.0, description="Projected modal price (₹/quintal)")
    lower_bound: float = Field(..., ge=0.0, description="Lower 80% confidence interval (₹/quintal)")
    upper_bound: float = Field(..., ge=0.0, description="Upper 80% confidence interval (₹/quintal)")


class MSPComparison(BaseModel):
    """Comparison against official CACP Minimum Support Price benchmark."""
    commodity: str = Field(..., description="Commodity name")
    msp_price: float | None = Field(default=None, description="Official CACP MSP (₹/quintal) if applicable")
    current_market_price: float = Field(..., description="Prevailing market modal price (₹/quintal)")
    difference: float | None = Field(default=None, description="Current price minus MSP (₹/quintal)")
    diff_percentage: float | None = Field(default=None, description="Percentage deviation relative to MSP")
    status: Literal["ABOVE_MSP", "BELOW_MSP", "AT_MSP", "NO_MSP_ANNOUNCED"] = Field(
        ..., description="Market position relative to procurement floor"
    )
    guidance: str = Field(..., description="Strategic advisory guidance regarding MSP procurement")


class MarketAdvisoryReport(BaseModel):
    """Complete market intelligence advisory report."""
    commodity: str = Field(..., description="Target agricultural commodity")
    farmer_location: str = Field(..., description="Origin location (district/state or coordinates)")
    current_modal_price_kg: float = Field(..., description="Prevailing reference price in ₹/kg")
    current_modal_price_quintal: float = Field(..., description="Prevailing reference price in ₹/quintal")
    recommendation: Literal["SELL_NOW", "HOLD", "TRANSPORT_TO_MANDI"] = Field(
        ..., description="Decisive farmer advisory action"
    )
    trend_direction: Literal["RISING", "FALLING", "STABLE"] = Field(
        ..., description="7-day projected price velocity"
    )
    trend_percentage: float = Field(..., description="Projected percentage change over 7 days")
    msp_analysis: MSPComparison
    top_mandis: list[MandiRecord] = Field(default_factory=list, description="Top 5 mandis ranked by net price")
    forecast_7d: list[PriceForecastPoint] = Field(default_factory=list, description="7-day daily forecast")
    advisory_text: str = Field(..., description="Actionable farmer advisory with rationale")
    citations: list[str] = Field(default_factory=list, description="Authoritative data source citations")
