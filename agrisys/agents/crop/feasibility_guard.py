"""Agronomic Feasibility and Seasonality Guardrail."""

from __future__ import annotations
from typing import Dict, Any
from agrisys.agents.crop.models import (
    CropInputFeatures,
    CropFeasibilityStatus,
    SeasonEnum,
    WaterSourceEnum,
)

# Domain Knowledge Rules based on ICAR Agronomy Handbooks
CROP_AGRONOMIC_PROFILES: dict[str, dict[str, Any]] = {
    "rice": {
        "seasons": [SeasonEnum.KHARIF, SeasonEnum.ANNUAL],
        "min_water_mm": 1000,
        "requires_irrigation": True,
        "ph_range": (5.0, 7.5),
    },
    "maize": {
        "seasons": [SeasonEnum.KHARIF, SeasonEnum.RABI, SeasonEnum.ZAID],
        "min_water_mm": 500,
        "requires_irrigation": False,
        "ph_range": (5.5, 7.5),
    },
    "chickpea": {
        "seasons": [SeasonEnum.RABI],
        "min_water_mm": 350,
        "requires_irrigation": False,
        "ph_range": (5.8, 8.5),
    },
    "kidneybeans": {
        "seasons": [SeasonEnum.KHARIF, SeasonEnum.RABI],
        "min_water_mm": 400,
        "requires_irrigation": False,
        "ph_range": (5.5, 6.5),
    },
    "pigeonpeas": {
        "seasons": [SeasonEnum.KHARIF],
        "min_water_mm": 600,
        "requires_irrigation": False,
        "ph_range": (5.0, 8.0),
    },
    "mothbeans": {
        "seasons": [SeasonEnum.KHARIF],
        "min_water_mm": 250,
        "requires_irrigation": False,
        "ph_range": (4.5, 8.5),
    },
    "mungbean": {
        "seasons": [SeasonEnum.KHARIF, SeasonEnum.ZAID],
        "min_water_mm": 300,
        "requires_irrigation": False,
        "ph_range": (6.0, 7.5),
    },
    "blackgram": {
        "seasons": [SeasonEnum.KHARIF, SeasonEnum.RABI],
        "min_water_mm": 400,
        "requires_irrigation": False,
        "ph_range": (6.0, 7.5),
    },
    "lentil": {
        "seasons": [SeasonEnum.RABI],
        "min_water_mm": 300,
        "requires_irrigation": False,
        "ph_range": (5.8, 7.8),
    },
    "pomegranate": {
        "seasons": [SeasonEnum.ANNUAL],
        "min_water_mm": 500,
        "requires_irrigation": True,
        "ph_range": (5.5, 7.5),
    },
    "banana": {
        "seasons": [SeasonEnum.ANNUAL],
        "min_water_mm": 1200,
        "requires_irrigation": True,
        "ph_range": (5.5, 7.0),
    },
    "mango": {
        "seasons": [SeasonEnum.ANNUAL],
        "min_water_mm": 600,
        "requires_irrigation": False,
        "ph_range": (5.0, 7.5),
    },
    "grapes": {
        "seasons": [SeasonEnum.ANNUAL],
        "min_water_mm": 600,
        "requires_irrigation": True,
        "ph_range": (5.5, 7.0),
    },
    "watermelon": {
        "seasons": [SeasonEnum.ZAID, SeasonEnum.KHARIF],
        "min_water_mm": 400,
        "requires_irrigation": True,
        "ph_range": (6.0, 7.0),
    },
    "muskmelon": {
        "seasons": [SeasonEnum.ZAID],
        "min_water_mm": 300,
        "requires_irrigation": True,
        "ph_range": (6.0, 7.0),
    },
    "apple": {
        "seasons": [SeasonEnum.ANNUAL],
        "min_water_mm": 800,
        "requires_irrigation": True,
        "ph_range": (5.5, 6.8),
    },
    "orange": {
        "seasons": [SeasonEnum.ANNUAL],
        "min_water_mm": 800,
        "requires_irrigation": True,
        "ph_range": (6.0, 7.5),
    },
    "papaya": {
        "seasons": [SeasonEnum.ANNUAL],
        "min_water_mm": 1000,
        "requires_irrigation": True,
        "ph_range": (6.0, 7.0),
    },
    "coconut": {
        "seasons": [SeasonEnum.ANNUAL],
        "min_water_mm": 1300,
        "requires_irrigation": True,
        "ph_range": (5.2, 8.0),
    },
    "cotton": {
        "seasons": [SeasonEnum.KHARIF],
        "min_water_mm": 600,
        "requires_irrigation": False,
        "ph_range": (5.8, 8.0),
    },
    "jute": {
        "seasons": [SeasonEnum.KHARIF],
        "min_water_mm": 1200,
        "requires_irrigation": True,
        "ph_range": (6.0, 7.4),
    },
    "coffee": {
        "seasons": [SeasonEnum.ANNUAL],
        "min_water_mm": 1200,
        "requires_irrigation": True,
        "ph_range": (5.0, 7.0),
    },
}


class CropFeasibilityGuard:
    """Validates ML model predictions against agronomic constraints (Season, Water, pH)."""

    def evaluate(
        self, crop_name: str, model_probability: float, features: CropInputFeatures
    ) -> CropFeasibilityStatus:
        crop_clean = crop_name.lower().strip()
        prof = CROP_AGRONOMIC_PROFILES.get(crop_clean)

        if not prof:
            # Unknown profile, pass through default
            return CropFeasibilityStatus(
                is_feasible=True,
                suitability_score=model_probability,
                seasonal_match=True,
                water_match=True,
                ph_match=True,
                flags=[],
                reasoning="Agronomic profile not restricted.",
            )

        flags: list[str] = []
        score = model_probability

        # 1. Season Check
        season_match = (
            features.season in prof["seasons"]
            or SeasonEnum.ANNUAL in prof["seasons"]
            or features.season == SeasonEnum.ANNUAL
        )
        if not season_match:
            flags.append(f"Off-season alert: {crop_name} is typically sown in {[s.value for s in prof['seasons']]}.")
            score *= 0.60  # 40% penalty for out-of-season sowing

        # 2. Water Availability Check
        water_match = True
        if prof["requires_irrigation"] and features.water_availability == WaterSourceEnum.RAINFED:
            if features.rainfall < prof["min_water_mm"]:
                water_match = False
                flags.append(
                    f"Water deficit warning: {crop_name} requires >={prof['min_water_mm']}mm or irrigation. Rainfed conditions pose drought risk."
                )
                score *= 0.50  # 50% penalty for severe water deficit

        # 3. pH Range Check
        ph_low, ph_high = prof["ph_range"]
        ph_match = ph_low <= features.ph <= ph_high
        if not ph_match:
            flags.append(
                f"Soil pH alert: Soil pH {features.ph:.1f} is outside ideal range ({ph_low}-{ph_high}) for {crop_name}."
            )
            score *= 0.80  # 20% penalty for sub-optimal pH

        is_feasible = score >= 0.20 and (season_match or water_match)
        reasoning = "; ".join(flags) if flags else "Fully feasible and optimal for given agro-climatic conditions."

        return CropFeasibilityStatus(
            is_feasible=is_feasible,
            suitability_score=round(score, 4),
            seasonal_match=season_match,
            water_match=water_match,
            ph_match=ph_match,
            flags=flags,
            reasoning=reasoning,
        )
