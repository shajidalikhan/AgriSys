"""Crop Recommendation Agent Coordinator."""

from __future__ import annotations
import logging
from typing import Any, List
from agrisys.agents.crop.models import (
    CropInputFeatures,
    CropRecommendation,
    CropRecommendationOutput,
    CropFeasibilityStatus,
)
from agrisys.agents.crop.registry import CROP_MODEL_REGISTRY, get_crop_tool
from agrisys.agents.crop.ensemble import CropEnsembleVoter
from agrisys.agents.crop.feasibility_guard import CropFeasibilityGuard
from agrisys.xai.shap_explainer import CropSHAPExplainer
from agrisys.providers.base import BaseLLMProvider
from agrisys.rag.retrieval.pipeline import RetrievalPipeline

logger = logging.getLogger(__name__)


class CropRecommendationAgent:
    """Coordinates ensemble inference, feasibility filtering, SHAP attribution, and RAG enrichment."""

    def __init__(
        self,
        llm_provider: BaseLLMProvider | None = None,
        rag_pipeline: RetrievalPipeline | None = None,
    ):
        self.llm_provider = llm_provider
        self.rag_pipeline = rag_pipeline
        self.voter = CropEnsembleVoter()
        self.feasibility_guard = CropFeasibilityGuard()
        self.shap_explainer = None
        self._init_shap()

    def _init_shap(self) -> None:
        try:
            xgb_tool = get_crop_tool("xgb_crop_classifier")
            if hasattr(xgb_tool, "model"):
                self.shap_explainer = CropSHAPExplainer(
                    xgb_tool.model, getattr(xgb_tool, "label_mapping", {})
                )
        except Exception as e:
            logger.warning(f"SHAP explainer initialization deferred: {e}")

    async def recommend(
        self, features: CropInputFeatures, top_k: int = 3, language: str = "en"
    ) -> CropRecommendationOutput:
        # 1. Ensemble Predictions from Registry Tools
        tool_predictions = {}
        for name, tool in CROP_MODEL_REGISTRY.items():
            try:
                preds = await tool.predict(features)
                tool_predictions[name] = preds
            except Exception as e:
                logger.warning(f"Crop model tool '{name}' failed during inference: {e}")

        ensemble_ranked = self.voter.vote(tool_predictions)
        if not ensemble_ranked:
            raise RuntimeError("No crop model tools returned predictions.")

        # 2. Feasibility Evaluation
        recommendations: List[CropRecommendation] = []
        for crop_name, prob in ensemble_ranked[:top_k]:
            feasibility: CropFeasibilityStatus = self.feasibility_guard.evaluate(
                crop_name, prob, features
            )

            # RAG enrichment for package of practices
            pop_summary = ""
            citations = []
            if self.rag_pipeline:
                try:
                    rag_res = await self.rag_pipeline.retrieve(
                        query=f"{crop_name} package of practices sowing fertilizer variety",
                        top_k=2,
                        filter_criteria={"crop": crop_name, "domain": "crop_recommendation"},
                    )
                    if rag_res.chunks:
                        pop_summary = "\n".join(c.content for c in rag_res.chunks[:2])
                        citations = [c.source for c in rag_res.chunks]
                except Exception as err:
                    logger.debug(f"RAG lookup for {crop_name} skipped: {err}")

            recommendations.append(
                CropRecommendation(
                    crop_name=crop_name,
                    probability=prob,
                    feasibility=feasibility,
                    package_of_practices_summary=pop_summary,
                    key_drivers=[],
                    limiting_factors=[],
                )
            )

        winning_crop = recommendations[0].crop_name
        winner_prob = recommendations[0].probability

        # 3. SHAP Feature Explanations
        shap_data = {}
        if self.shap_explainer:
            try:
                # Find index of winning crop in label mapping
                idx = 0
                if hasattr(self.shap_explainer, "class_mapping"):
                    for k, v in self.shap_explainer.class_mapping.items():
                        if v.lower() == winning_crop.lower():
                            idx = k
                            break

                shap_data = self.shap_explainer.explain(
                    features=features.to_feature_array(),
                    target_crop_index=idx,
                    language=language,
                )
                recommendations[0].key_drivers = shap_data.get("positive_drivers", [])
                recommendations[0].limiting_factors = shap_data.get("limiting_factors", [])
            except Exception as err:
                logger.warning(f"Error computing SHAP for {winning_crop}: {err}")

        # 4. Generate Advisory Text
        drivers_str = ", ".join(recommendations[0].key_drivers) or "optimal soil nutrients and temperature"
        advisory = (
            f"Based on your soil and climate data, **{winning_crop.capitalize()}** is the most recommended crop "
            f"with {winner_prob * 100:.1f}% suitability. Key favorable factors include {drivers_str}."
        )
        if not recommendations[0].feasibility.is_feasible or recommendations[0].feasibility.flags:
            advisory += f" Note: {recommendations[0].feasibility.reasoning}"

        return CropRecommendationOutput(
            top_recommendations=recommendations,
            winning_crop=winning_crop,
            overall_confidence=winner_prob,
            input_features=features,
            shap_attributions=shap_data,
            rag_citations=citations if 'citations' in locals() else [],
            advisory_text=advisory,
        )
