"""Pydantic schemas for the Crop Recommendation Agent."""

from __future__ import annotations
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class SeasonEnum(str, Enum):
    KHARIF = "kharif"
    RABI = "rabi"
    ZAID = "zaid"
    ANNUAL = "annual"


class WaterSourceEnum(str, Enum):
    CANAL_IRRIGATED = "canal_irrigated"
    BOREWELL_DRIP = "borewell_drip"
    RAINFED = "rainfed"


class CropInputFeatures(BaseModel):
    """Agronomic input features for crop prediction."""
    N: float = Field(..., ge=0.0, le=250.0, description="Nitrogen content in soil (kg/ha)")
    P: float = Field(..., ge=0.0, le=250.0, description="Phosphorus content in soil (kg/ha)")
    K: float = Field(..., ge=0.0, le=300.0, description="Potassium content in soil (kg/ha)")
    temperature: float = Field(..., ge=0.0, le=55.0, description="Mean temperature (°C)")
    humidity: float = Field(..., ge=5.0, le=100.0, description="Relative humidity (%)")
    ph: float = Field(..., ge=3.0, le=10.0, description="Soil pH value")
    rainfall: float = Field(..., ge=0.0, le=4000.0, description="Annual / seasonal rainfall (mm)")
    ec: float = Field(default=0.8, ge=0.0, le=10.0, description="Electrical conductivity (dS/m)")
    season: SeasonEnum = Field(default=SeasonEnum.KHARIF, description="Target cropping season")
    water_availability: WaterSourceEnum = Field(default=WaterSourceEnum.CANAL_IRRIGATED, description="Water source")
    state: str = Field(default="Punjab", description="State or agro-climatic zone")

    def to_feature_array(self) -> list[float]:
        """Return numeric features matching the core model training schema."""
        return [self.N, self.P, self.K, self.temperature, self.humidity, self.ph, self.rainfall]


class CropFeasibilityStatus(BaseModel):
    """Feasibility assessment of a recommended crop."""
    is_feasible: bool = True
    suitability_score: float = Field(..., ge=0.0, le=1.0)
    seasonal_match: bool = True
    water_match: bool = True
    ph_match: bool = True
    flags: list[str] = Field(default_factory=list)
    reasoning: str = ""


class CropRecommendation(BaseModel):
    """Single crop recommendation entry."""
    crop_name: str
    scientific_name: str = ""
    probability: float = Field(..., ge=0.0, le=1.0)
    feasibility: CropFeasibilityStatus
    package_of_practices_summary: str = ""
    basal_fertilizer: dict[str, str] = Field(default_factory=dict)
    key_drivers: list[str] = Field(default_factory=list)
    limiting_factors: list[str] = Field(default_factory=list)


class CropRecommendationOutput(BaseModel):
    """Complete output report of the Crop Recommendation Agent."""
    top_recommendations: list[CropRecommendation]
    winning_crop: str
    overall_confidence: float
    input_features: CropInputFeatures
    shap_attributions: dict[str, Any] = Field(default_factory=dict)
    rag_citations: list[str] = Field(default_factory=list)
    advisory_text: str = ""


class WhatIfSimulationRequest(BaseModel):
    """Request for running sensitivity analysis on perturbed parameters."""
    base_features: CropInputFeatures
    delta_features: dict[str, float] = Field(
        ...,
        description="Key-value delta perturbations, e.g. {'N': +20.0, 'rainfall': -150.0}"
    )


class WhatIfSimulationResult(BaseModel):
    """Comparative outcome of the What-If simulation."""
    original_winner: str
    original_probability: float
    simulated_winner: str
    simulated_probability: float
    probability_shifts: dict[str, float]
    shap_shifts: dict[str, float] = Field(default_factory=dict)
    recommendation_changed: bool
    agronomic_verdict: str
