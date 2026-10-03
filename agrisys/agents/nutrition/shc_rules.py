"""ICAR Soil Health Card (SHC) agronomic benchmarks and fertilizer calculation rules."""

from __future__ import annotations
from typing import Any, Dict, List, Tuple
from agrisys.agents.nutrition.models import (
    SoilSensorReading,
    FertilizerDoseRecommendation,
)

# Standard ICAR Package of Practices Base Nutrient Recommendations (N-P-K in kg/ha)
# Format: crop_key -> (N, P2O5, K2O)
ICAR_CROP_POP_RECOMMENDATIONS: dict[str, tuple[float, float, float]] = {
    "rice": (120.0, 60.0, 40.0),
    "paddy": (120.0, 60.0, 40.0),
    "wheat": (120.0, 60.0, 40.0),
    "maize": (120.0, 60.0, 50.0),
    "tomato": (100.0, 60.0, 60.0),
    "potato": (150.0, 100.0, 120.0),
    "cotton": (120.0, 60.0, 60.0),
    "sugarcane": (250.0, 100.0, 120.0),
    "banana": (200.0, 60.0, 300.0),
    "chilli": (120.0, 60.0, 60.0),
    "onion": (100.0, 50.0, 50.0),
    "pulses": (20.0, 40.0, 20.0),
    "default": (100.0, 50.0, 50.0),
}


class SoilHealthCardEvaluator:
    """Evaluates soil fertility against ICAR Soil Health Card benchmarks and calculates commercial doses."""

    @staticmethod
    def evaluate_nutrient_levels(sensor: SoilSensorReading) -> dict[str, str]:
        """Categorizes soil metrics according to ICAR benchmark thresholds."""
        evals: dict[str, str] = {}

        # Nitrogen (kg/ha)
        if sensor.nitrogen < 280.0:
            evals["N"] = f"Low ({sensor.nitrogen:.1f} kg/ha, target ≥ 280)"
        elif sensor.nitrogen <= 560.0:
            evals["N"] = f"Medium ({sensor.nitrogen:.1f} kg/ha, optimal range 280-560)"
        else:
            evals["N"] = f"High ({sensor.nitrogen:.1f} kg/ha, target ≤ 560)"

        # Phosphorus (kg/ha)
        if sensor.phosphorus < 10.0:
            evals["P"] = f"Low ({sensor.phosphorus:.1f} kg/ha, target ≥ 10)"
        elif sensor.phosphorus <= 25.0:
            evals["P"] = f"Medium ({sensor.phosphorus:.1f} kg/ha, optimal range 10-25)"
        else:
            evals["P"] = f"High ({sensor.phosphorus:.1f} kg/ha, target ≤ 25)"

        # Potassium (kg/ha)
        if sensor.potassium < 108.0:
            evals["K"] = f"Low ({sensor.potassium:.1f} kg/ha, target ≥ 108)"
        elif sensor.potassium <= 280.0:
            evals["K"] = f"Medium ({sensor.potassium:.1f} kg/ha, optimal range 108-280)"
        else:
            evals["K"] = f"High ({sensor.potassium:.1f} kg/ha, target ≤ 280)"

        # pH
        if sensor.ph < 6.5:
            evals["pH"] = f"Acidic ({sensor.ph:.1f}) — Lime application recommended"
        elif sensor.ph <= 7.8:
            evals["pH"] = f"Neutral / Optimal ({sensor.ph:.1f})"
        else:
            evals["pH"] = f"Alkaline ({sensor.ph:.1f}) — Gypsum treatment recommended"

        # Electrical Conductivity (dS/m)
        if sensor.electrical_conductivity < 1.0:
            evals["EC"] = f"Normal Non-Saline ({sensor.electrical_conductivity:.2f} dS/m)"
        elif sensor.electrical_conductivity <= 2.0:
            evals["EC"] = f"Critical / Moderately Saline ({sensor.electrical_conductivity:.2f} dS/m)"
        else:
            evals["EC"] = f"Highly Saline ({sensor.electrical_conductivity:.2f} dS/m) — Leaching required"

        # Moisture
        if sensor.soil_moisture < 25.0:
            evals["Moisture"] = f"Deficit ({sensor.soil_moisture:.1f}%) — Immediate irrigation needed"
        elif sensor.soil_moisture <= 60.0:
            evals["Moisture"] = f"Adequate ({sensor.soil_moisture:.1f}%)"
        else:
            evals["Moisture"] = f"Excess / Saturated ({sensor.soil_moisture:.1f}%) — Ensure drainage"

        return evals

    @classmethod
    def calculate_fertilizer_dose(
        cls,
        crop: str,
        sensor: SoilSensorReading | None = None,
        predicted_doses: tuple[float, float, float] | None = None,
    ) -> FertilizerDoseRecommendation:
        """
        Calculates exact commercial fertilizer quantities (Urea, DAP, MOP) based on
        crop Package of Practices adjusted for soil test values.
        """
        crop_key = crop.lower().strip()
        base_n, base_p, base_k = ICAR_CROP_POP_RECOMMENDATIONS.get(
            crop_key, ICAR_CROP_POP_RECOMMENDATIONS["default"]
        )

        # 1. Determine elemental target doses (kg/ha)
        if predicted_doses is not None:
            # Model-predicted doses, clamped within realistic agronomic bounds
            target_n = max(0.0, min(float(predicted_doses[0]), base_n * 1.5))
            target_p = max(0.0, min(float(predicted_doses[1]), base_p * 1.5))
            target_k = max(0.0, min(float(predicted_doses[2]), base_k * 1.5))
        elif sensor is not None:
            # Soil-test crop response (STCR) adjustment factors:
            # Low: +25% dose; Medium: 100% standard dose; High: -25% dose
            adj_n = 1.25 if sensor.nitrogen < 280 else (0.75 if sensor.nitrogen > 560 else 1.0)
            adj_p = 1.25 if sensor.phosphorus < 10 else (0.75 if sensor.phosphorus > 25 else 1.0)
            adj_k = 1.25 if sensor.potassium < 108 else (0.75 if sensor.potassium > 280 else 1.0)

            target_n = round(base_n * adj_n, 1)
            target_p = round(base_p * adj_p, 1)
            target_k = round(base_k * adj_k, 1)
        else:
            target_n, target_p, target_k = base_n, base_p, base_k

        # 2. Commercial formulation conversion:
        # DAP (18% N, 46% P2O5) supplies P2O5 and partial N
        if target_p > 0.0:
            dap_kg_ha = round(target_p / 0.46, 1)
            n_from_dap = dap_kg_ha * 0.18
        else:
            dap_kg_ha = 0.0
            n_from_dap = 0.0

        # Remaining N supplied by Urea (46% N)
        remaining_n = max(0.0, target_n - n_from_dap)
        urea_kg_ha = round(remaining_n / 0.46, 1)

        # MOP (Muriate of Potash, 60% K2O)
        mop_kg_ha = round(target_k / 0.60, 1) if target_k > 0.0 else 0.0

        # Acre conversions (1 hectare = 2.47105 acres)
        HA_TO_ACRE = 2.47105
        urea_kg_acre = round(urea_kg_ha / HA_TO_ACRE, 1)
        dap_kg_acre = round(dap_kg_ha / HA_TO_ACRE, 1)
        mop_kg_acre = round(mop_kg_ha / HA_TO_ACRE, 1)

        # 3. Application Schedule (split doses to prevent leaching and volatilization)
        schedule = [
            {
                "stage": "Basal (At Sowing / Transplanting)",
                "details": f"Apply 100% DAP ({dap_kg_ha} kg/ha / {dap_kg_acre} kg/acre), 100% MOP ({mop_kg_ha} kg/ha / {mop_kg_acre} kg/acre), and 50% Urea ({round(urea_kg_ha*0.5, 1)} kg/ha / {round(urea_kg_acre*0.5, 1)} kg/acre).",
            },
            {
                "stage": "Vegetative Stage (25-30 Days After Sowing)",
                "details": f"Top dress 25% Urea ({round(urea_kg_ha*0.25, 1)} kg/ha / {round(urea_kg_acre*0.25, 1)} kg/acre) under optimal soil moisture.",
            },
            {
                "stage": "Flowering / Panicle / Fruit Set (45-55 DAS)",
                "details": f"Top dress remaining 25% Urea ({round(urea_kg_ha*0.25, 1)} kg/ha / {round(urea_kg_acre*0.25, 1)} kg/acre).",
            },
        ]

        # 4. Organic and Biofertilizer alternatives
        organic = [
            "Well-decomposed Farmyard Manure (FYM): 10 tonnes/ha (4 tonnes/acre) during land preparation.",
            "Vermicompost: 2.5 tonnes/ha to enhance soil microbial biomass and cation exchange capacity.",
            "Azotobacter / Azospirillum biofertilizers (for N) and PSB (Phosphorus Solubilizing Bacteria) seed/soil treatment.",
        ]

        return FertilizerDoseRecommendation(
            n_dose_kg_ha=target_n,
            p_dose_kg_ha=target_p,
            k_dose_kg_ha=target_k,
            urea_kg_ha=urea_kg_ha,
            dap_kg_ha=dap_kg_ha,
            mop_kg_ha=mop_kg_ha,
            urea_kg_acre=urea_kg_acre,
            dap_kg_acre=dap_kg_acre,
            mop_kg_acre=mop_kg_acre,
            application_schedule=schedule,
            organic_alternatives=organic,
        )
