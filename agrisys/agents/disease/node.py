"""LangGraph Disease Agent Node (§4.3).

Exposes `disease_agent_node(state) -> state` orchestrating:
Preprocessor -> Crop Detector -> Targeted/General Disease Router -> GradCAM -> RAG -> Diagnostic Report
"""

from typing import Any, Dict, Optional
import base64
from pathlib import Path
from agrisys.agents.disease.preprocessor import ImagePreprocessor
from agrisys.agents.disease.crop_detector import CropDetector
from agrisys.agents.disease.model_router import CropModelRouter
from agrisys.agents.disease.chain import AgriChainDiagnosticEngine
from agrisys.xai.gradcam import DiseaseGradCAM
from agrisys.rag.retrieval.pipeline import RetrievalPipeline


class DiseaseAgent:
    """Coordinator executing full disease diagnostic pipeline."""

    def __init__(
        self,
        retrieval_pipeline: Optional[RetrievalPipeline] = None,
        confidence_threshold: float = 0.70,
    ) -> None:
        self.preprocessor = ImagePreprocessor()
        self.crop_detector = CropDetector()
        self.model_router = CropModelRouter(confidence_threshold=confidence_threshold)
        self.gradcam = DiseaseGradCAM()
        self.chain = AgriChainDiagnosticEngine(retrieval_pipeline=retrieval_pipeline)

    async def diagnose(
        self,
        image_bytes: bytes,
        user_query: Optional[str] = None,
        language: str = "en",
    ) -> Dict[str, Any]:
        """Execute complete diagnostic workflow."""
        # 1. Gatekeeper & validation
        gatekeeper_res, pil_img = self.preprocessor.validate_and_gatekeep(image_bytes)
        if not gatekeeper_res.is_plant or pil_img is None:
            return {
                "status": "rejected",
                "gatekeeper": gatekeeper_res.model_dump(),
                "advisory": gatekeeper_res.message,
                "crop": "unknown",
                "disease": "none",
            }

        # 2. Enhancement
        enhanced_bytes, tensor, rgb_np = self.preprocessor.enhance(pil_img)

        # 3. Crop detection with consensus resolver
        crop_res = await self.crop_detector.detect_crop(enhanced_bytes, user_query=user_query)

        # 4. Disease routing and prediction
        disease_pred = await self.model_router.route_and_predict(crop_res.crop, enhanced_bytes)

        # 5. Visual explainability heatmap
        _, heatmap_path = self.gradcam.generate_heatmap_overlay(rgb_np, model_tensor=tensor)

        # 6. AgriChain CoT reasoning and RAG treatment lookup
        report = await self.chain.generate_diagnostic_report(
            crop_result=crop_res,
            disease_pred=disease_pred,
            gatekeeper_result=gatekeeper_res,
            heatmap_path=heatmap_path,
            language=language,
        )

        return {
            "status": "success",
            "report": report.model_dump(),
            "advisory": report.advisory,
            "crop": report.crop,
            "disease": report.disease,
            "confidence": report.confidence,
            "severity_score": report.severity_score,
            "severity_label": report.severity_label,
            "treatment_protocol": report.treatment_protocol,
            "verified_sources": report.verified_sources,
            "heatmap_path": report.heatmap_artifact_path,
        }


# Global agent instance
_DISEASE_AGENT_INSTANCE: Optional[DiseaseAgent] = None


def get_disease_agent(retrieval_pipeline: Optional[RetrievalPipeline] = None) -> DiseaseAgent:
    global _DISEASE_AGENT_INSTANCE
    if _DISEASE_AGENT_INSTANCE is None:
        _DISEASE_AGENT_INSTANCE = DiseaseAgent(retrieval_pipeline=retrieval_pipeline)
    return _DISEASE_AGENT_INSTANCE


async def disease_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node function for disease diagnosis.

    Reads 'image_bytes' or 'image_path' from state, diagnoses disease,
    and returns updated state dict.
    """
    image_bytes = state.get("image_bytes")
    image_path = state.get("image_path")
    query = state.get("query", "")
    language = state.get("language", "en")

    if not image_bytes and image_path:
        p = Path(image_path)
        if p.exists():
            image_bytes = p.read_bytes()

    if not image_bytes:
        return {
            "disease_result": {
                "status": "error",
                "advisory": "No leaf image provided for disease diagnosis.",
            }
        }

    agent = get_disease_agent()
    result = await agent.diagnose(image_bytes, user_query=query, language=language)

    return {
        "disease_result": result,
        "active_agent": "disease",
        "final_advisory": result.get("advisory", ""),
    }
