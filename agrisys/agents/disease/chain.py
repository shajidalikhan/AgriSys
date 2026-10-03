"""AgriChain CoT Reasoning and RAG Treatment Retrieval (§4.3).

Executes the Chain-of-Thought diagnostic flow:
[Crop] -> [Disease Label] -> [Severity Grade 0-5] -> [RAG ICAR Retrieval] -> [Structured Advisory]
"""

from typing import Dict, List, Optional
from agrisys.agents.disease.models import DiseasePrediction, CropDetectionResult, GatekeeperResult, DiseaseDiagnosticReport
from agrisys.rag.retrieval.pipeline import RetrievalPipeline
from agrisys.providers.base import BaseLLMProvider


class AgriChainDiagnosticEngine:
    """Reasoning engine connecting diagnostic predictions with ICAR knowledge base."""

    def __init__(
        self,
        retrieval_pipeline: Optional[RetrievalPipeline] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
    ) -> None:
        self.retrieval_pipeline = retrieval_pipeline
        self.llm_provider = llm_provider

    async def generate_diagnostic_report(
        self,
        crop_result: CropDetectionResult,
        disease_pred: DiseasePrediction,
        gatekeeper_result: GatekeeperResult,
        heatmap_path: Optional[str] = None,
        language: str = "en",
    ) -> DiseaseDiagnosticReport:
        """Formulate complete diagnostic report grounded in RAG protocols."""
        crop = crop_result.crop
        disease = disease_pred.disease

        # 1. Retrieve verified treatments from RAG knowledge base
        rag_sources = []
        treatment_text = ""
        if self.retrieval_pipeline:
            query = f"treatment dosage fungicide management for {disease} in {crop}"
            filter_meta = {"crop": crop, "domain": "disease", "language": language}
            chunks = await self.retrieval_pipeline.retrieve(query, filter_metadata=filter_meta)
            rag_sources = [{"id": c.id, "text": c.text, "score": c.score, "metadata": c.metadata} for c in chunks]
            if chunks:
                treatment_text = chunks[0].text

        if not treatment_text:
            treatment_text = f"Apply recommended ICAR fungicides for {disease} and contact local Krishi Vigyan Kendra (KVK)."

        # 2. Synthesize structured advisory
        advisory_lines = [
            f"**Crop Identified**: {crop.capitalize()} (Confidence: {int(crop_result.confidence * 100)}%)",
            f"**Diagnosis**: {disease.replace('_', ' ').title()} (Confidence: {int(disease_pred.confidence * 100)}%)",
            f"**Severity Level**: Grade {disease_pred.severity}/5 ({disease_pred.severity_label})",
        ]

        if crop_result.discrepancy_note:
            advisory_lines.append(f"> ℹ️ *Note*: {crop_result.discrepancy_note}")

        advisory_lines.extend([
            "",
            "### Recommended ICAR Treatment Protocol:",
            treatment_text,
            "",
            "### Action Guidelines:",
        ])

        if disease_pred.severity <= 1:
            advisory_lines.append("- Early/Trace stage: Spray bio-fungicides or preventive protective contact sprays. Avoid overhead irrigation.")
        elif disease_pred.severity <= 3:
            advisory_lines.append("- Moderate infection: Apply curative systemic fungicide spray at the specified dosage. Ensure thorough coverage on lower leaf surfaces.")
        else:
            advisory_lines.append("- Severe infection: Rogue and safely burn severely collapsed leaves to prevent fungal spore dispersal across neighboring healthy rows.")

        full_advisory = "\n".join(advisory_lines)

        return DiseaseDiagnosticReport(
            crop=crop,
            disease=disease,
            confidence=disease_pred.confidence,
            severity_score=disease_pred.severity,
            severity_label=disease_pred.severity_label,
            advisory=full_advisory,
            treatment_protocol=treatment_text,
            verified_sources=rag_sources,
            heatmap_artifact_path=heatmap_path,
            gatekeeper=gatekeeper_result,
            crop_detection=crop_result,
        )
