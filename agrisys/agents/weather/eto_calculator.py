"""FAO-56 Penman-Monteith Reference Evapotranspiration (ET0) & Crop Water Requirement Calculator."""

from __future__ import annotations
import math
from typing import Dict, Tuple
from agrisys.agents.weather.models import EToCalculationResult

# FAO-56 Crop Coefficients (Kc) for Major Indian Agricultural Crops
# Format: crop_key -> {"Initial": kc_ini, "Mid": kc_mid, "Late": kc_late}
FAO56_CROP_KC: dict[str, dict[str, float]] = {
    "wheat": {"Initial": 0.40, "Mid": 1.15, "Late": 0.40},
    "rice": {"Initial": 1.05, "Mid": 1.20, "Late": 0.90},
    "paddy": {"Initial": 1.05, "Mid": 1.20, "Late": 0.90},
    "maize": {"Initial": 0.40, "Mid": 1.15, "Late": 0.60},
    "tomato": {"Initial": 0.60, "Mid": 1.15, "Late": 0.80},
    "potato": {"Initial": 0.50, "Mid": 1.15, "Late": 0.75},
    "cotton": {"Initial": 0.45, "Mid": 1.20, "Late": 0.65},
    "sugarcane": {"Initial": 0.40, "Mid": 1.25, "Late": 0.75},
    "mustard": {"Initial": 0.35, "Mid": 1.05, "Late": 0.35},
    "soyabean": {"Initial": 0.40, "Mid": 1.15, "Late": 0.50},
    "banana": {"Initial": 1.00, "Mid": 1.20, "Late": 1.10},
    "onion": {"Initial": 0.70, "Mid": 1.05, "Late": 0.75},
    "chilli": {"Initial": 0.60, "Mid": 1.05, "Late": 0.80},
    "gram": {"Initial": 0.40, "Mid": 1.00, "Late": 0.35},
    "pulses": {"Initial": 0.40, "Mid": 1.05, "Late": 0.40},
    "default": {"Initial": 0.50, "Mid": 1.10, "Late": 0.60},
}


class FAO56PenmanMonteithCalculator:
    """Calculates daily reference evapotranspiration (ET0) compliant with FAO-56 guidelines."""

    @staticmethod
    def calculate_et0(
        temp_max: float,
        temp_min: float,
        relative_humidity: float,
        wind_speed_ms: float = 2.0,
        solar_radiation_mj: float = 18.0,
        elevation_m: float = 120.0,
    ) -> float:
        """
        Calculates reference evapotranspiration ET0 in mm/day using standard FAO-56 Penman-Monteith equation:
        ET0 = [0.408 * Δ * (Rn - G) + γ * (900 / (T + 273)) * u2 * (es - ea)] / [Δ + γ * (1 + 0.34 * u2)]
        """
        temp_mean = (temp_max + temp_min) / 2.0

        # Atmospheric pressure (P in kPa) from elevation
        P = 101.3 * math.pow((293.0 - 0.0065 * elevation_m) / 293.0, 5.26)

        # Psychrometric constant (γ in kPa/°C)
        gamma = 0.000665 * P

        # Saturation vapour pressure (es in kPa)
        es_tmax = 0.6108 * math.exp((17.27 * temp_max) / (temp_max + 237.3))
        es_tmin = 0.6108 * math.exp((17.27 * temp_min) / (temp_min + 237.3))
        es = (es_tmax + es_tmin) / 2.0

        # Actual vapour pressure (ea in kPa)
        ea = es * (max(10.0, min(relative_humidity, 100.0)) / 100.0)

        # Slope of saturation vapour pressure curve (Δ in kPa/°C)
        delta = (4098.0 * (0.6108 * math.exp((17.27 * temp_mean) / (temp_mean + 237.3)))) / math.pow(temp_mean + 237.3, 2)

        # Net radiation (Rn in MJ/m²/day) approximated from solar radiation
        # Net shortwave radiation (albedo α ≈ 0.23 for reference grass) minus net longwave
        Rn = max(1.0, 0.60 * solar_radiation_mj)
        G = 0.0  # Soil heat flux density is negligible for daily periods

        # Wind speed at 2m height (u2 in m/s)
        u2 = max(0.5, min(wind_speed_ms, 25.0))

        # FAO-56 Penman-Monteith numerator and denominator
        num_radiation = 0.408 * delta * (Rn - G)
        num_aerodynamic = gamma * (900.0 / (temp_mean + 273.0)) * u2 * (es - ea)
        denominator = delta + gamma * (1.0 + 0.34 * u2)

        et0 = (num_radiation + num_aerodynamic) / denominator
        return round(max(0.5, et0), 2)

    @classmethod
    def calculate_irrigation_requirement(
        cls,
        crop: str,
        stage: str = "Mid",
        temp_max: float = 32.0,
        temp_min: float = 20.0,
        relative_humidity: float = 65.0,
        wind_speed_ms: float = 2.0,
        precipitation_mm: float = 0.0,
        solar_radiation_mj: float = 18.0,
    ) -> EToCalculationResult:
        """
        Computes ET0, applies stage crop coefficient Kc, deducts effective rainfall,
        and determines net irrigation depth and drip runtime.
        """
        crop_clean = crop.lower().strip()
        kc_table = FAO56_CROP_KC.get(crop_clean, FAO56_CROP_KC["default"])
        stage_clean = stage.capitalize()
        if stage_clean not in kc_table:
            stage_clean = "Mid"
        kc = kc_table[stage_clean]

        et0 = cls.calculate_et0(
            temp_max=temp_max,
            temp_min=temp_min,
            relative_humidity=relative_humidity,
            wind_speed_ms=wind_speed_ms,
            solar_radiation_mj=solar_radiation_mj,
        )

        # Actual crop evapotranspiration (ETc in mm/day)
        etc = round(et0 * kc, 2)

        # USDA SCS Effective Rainfall estimation
        if precipitation_mm > 5.0:
            effective_rain = round(max(0.0, (precipitation_mm * 0.80) - 4.0), 2)
        else:
            effective_rain = 0.0

        # Net irrigation requirement (NIR in mm)
        nir = round(max(0.0, etc - effective_rain), 2)

        # Drip runtime estimation (assuming standard 4 mm/hr application rate)
        drip_hours = round(nir / 4.0, 1) if nir > 0.0 else 0.0

        return EToCalculationResult(
            et0_mm_day=et0,
            crop=crop,
            crop_growth_stage=stage_clean,
            crop_kc=kc,
            etc_mm_day=etc,
            effective_rainfall_mm=effective_rain,
            net_irrigation_requirement_mm=nir,
            recommended_drip_runtime_hours=drip_hours,
        )
