"""Master Nutrition Deficiency Agent coordinating cross-modal inference and precision dosing."""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
import torch

from agrisys.agents.nutrition.models import (
    SoilSensorReading,
    DeficiencyPrediction,
    FertilizerDoseRecommendation,
    NutritionReport,
)
from agrisys.agents.nutrition.fusion_model import (
    CrossModalNutritionFusionNet,
    SensorNormalizer,
    DEFICIENCY_CLASSES,
    DEFICIENCY_SYMPTOMS,
)
from agrisys.agents.nutrition.shc_rules import SoilHealthCardEvaluator
from agrisys.agents.disease.preprocessor import ImagePreprocessor
from agrisys.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class NutritionAgent:
    """
    Coordinates cross-modal leaf image and soil sensor processing,
    predicts deficiencies, calculates ICAR SHC fertilizer doses, and outputs
    actionable agronomic advisories.
    """

    def __init__(
        self,
        fusion_net: CrossModalNutritionFusionNet | None = None,
        llm_provider: BaseLLMProvider | None = None,
    ):
        self.fusion_net = fusion_net or CrossModalNutritionFusionNet()
        self.fusion_net.eval()
        self.llm_provider = llm_provider
        self.preprocessor = ImagePreprocessor()

    def diagnose(
        self,
        image_bytes: bytes | None = None,
        sensor_data: dict[str, Any] | SoilSensorReading | None = None,
        crop: str = "Tomato",
        language: str = "en",
    ) -> NutritionReport:
        """
        Executes end-to-end nutrition diagnosis and fertilizer calculation.
        """
        # 1. Determine modality & parse sensor data
        sensor_obj: SoilSensorReading | None = None
        sensor_tensor: torch.Tensor | None = None
        sensor_evals: dict[str, str] = {}

        if sensor_data is not None:
            if isinstance(sensor_data, dict):
                sensor_obj = SoilSensorReading(**sensor_data)
            elif isinstance(sensor_data, SoilSensorReading):
                sensor_obj = sensor_data

            if sensor_obj:
                sensor_tensor = SensorNormalizer.normalize(sensor_obj.to_feature_vector())
                sensor_evals = SoilHealthCardEvaluator.evaluate_nutrient_levels(sensor_obj)

        # 2. Process image bytes if available
        image_tensor: torch.Tensor | None = None
        if image_bytes:
            prep_result = self.preprocessor.preprocess(image_bytes)
            if prep_result.is_valid and prep_result.tensor is not None:
                image_tensor = prep_result.tensor

        # 3. Classify execution modality
        if image_tensor is not None and sensor_tensor is not None:
            modality = "multimodal"
        elif sensor_tensor is not None:
            modality = "sensor_only"
        elif image_tensor is not None:
            modality = "vision_only"
        else:
            raise ValueError("Nutrition diagnosis requires at least soil sensor readings or leaf image bytes.")

        # 4. Cross-Modal Fusion Model Prediction
        label, conf, (n_pred, p_pred, k_pred) = self.fusion_net.predict(
            image_tensor=image_tensor,
            sensor_tensor=sensor_tensor,
        )

        # Rule-assisted refinement if sensor indicates strong deficit but vision was ambiguous
        if sensor_obj and modality == "sensor_only":
            if sensor_obj.nitrogen < 200.0:
                label = "Nitrogen (N) Deficiency"
                conf = max(conf, 0.88)
            elif sensor_obj.phosphorus < 8.0:
                label = "Phosphorus (P) Deficiency"
                conf = max(conf, 0.85)
            elif sensor_obj.potassium < 90.0:
                label = "Potassium (K) Deficiency"
                conf = max(conf, 0.86)

        affected_element, symptom_desc = DEFICIENCY_SYMPTOMS.get(
            label, ("Unknown", "Observe foliar development for specific deficiency patterns.")
        )

        # Severity determination
        if label == "Healthy / Optimal":
            severity = "Normal"
        elif conf >= 0.80:
            severity = "Severe"
        elif conf >= 0.60:
            severity = "Moderate"
        else:
            severity = "Mild"

        prediction = DeficiencyPrediction(
            deficiency_class=label,
            confidence=round(conf, 3),
            severity=severity,
            affected_nutrient=affected_element,
            visual_symptoms=symptom_desc,
        )

        # 5. ICAR Soil Health Card Fertilizer Calculation
        fertilizer_rec = SoilHealthCardEvaluator.calculate_fertilizer_dose(
            crop=crop,
            sensor=sensor_obj,
            predicted_doses=(n_pred, p_pred, k_pred) if modality == "multimodal" else None,
        )

        # 6. Compose Actionable Advisory Text
        if language == "hi":
            advisory = (
                f"फसल: {crop} | पोषण स्थिति: {label} (विश्वास: {conf:.1%})\n"
                f"लक्षण: {symptom_desc}\n\n"
                f"अनुशंसित उर्वरक मात्रा:\n"
                f"• यूरिया (Urea 46% N): {fertilizer_rec.urea_kg_acre} किग्रा/एकड़ ({fertilizer_rec.urea_kg_ha} किग्रा/हेक्टेयर)\n"
                f"• डीएपी (DAP 18:46): {fertilizer_rec.dap_kg_acre} किग्रा/एकड़ ({fertilizer_rec.dap_kg_ha} किग्रा/हेक्टेयर)\n"
                f"• एमओपी (MOP 60% K2O): {fertilizer_rec.mop_kg_acre} किग्रा/एकड़ ({fertilizer_rec.mop_kg_ha} किग्रा/हेक्टेयर)\n\n"
                f"छिड़काव निर्देश: बेसल बुवाई के समय डीएपी और पोटाश की पूरी मात्रा दें। यूरिया को 2 से 3 बराबर किस्तों में बांटकर सिंचाई के बाद दें।"
            )
        else:
            advisory = (
                f"Crop: {crop} | Nutritional Diagnosis: {label} (Confidence: {conf:.1%})\n"
                f"Symptom Characteristics: {symptom_desc}\n\n"
                f"Recommended Precision Fertilizer Dosage:\n"
                f"• Urea (46% N): {fertilizer_rec.urea_kg_acre} kg/acre ({fertilizer_rec.urea_kg_ha} kg/ha)\n"
                f"• DAP (18% N, 46% P₂O₅): {fertilizer_rec.dap_kg_acre} kg/acre ({fertilizer_rec.dap_kg_ha} kg/ha)\n"
                f"• MOP (60% K₂O): {fertilizer_rec.mop_kg_acre} kg/acre ({fertilizer_rec.mop_kg_ha} kg/ha)\n\n"
                f"Application Guidelines: Apply 100% DAP and MOP with 50% Urea at basal sowing. Top-dress remaining Urea in two split doses during vegetative and flowering stages under adequate soil moisture."
            )

        citations = [
            "ICAR Soil Health Card (SHC) Benchmark Norms",
            f"ICAR Package of Practices for {crop} — Integrated Nutrient Management (INM)",
            "FAO Fertilizer and Plant Nutrition Guide Bulletin 16",
        ]

        return NutritionReport(
            crop=crop,
            input_modality=modality,
            sensor_evaluation=sensor_evals,
            prediction=prediction,
            fertilizer_recommendation=fertilizer_rec,
            advisory=advisory,
            citations=citations,
        )
