"""Multi-Agent Response Merger and Synthesizer."""

from __future__ import annotations
import logging
from typing import Any, List

logger = logging.getLogger(__name__)


class ResponseMerger:
    """SRP: Synthesizes multi-agent outputs, citations, and confidence scores into a cohesive advisory."""

    def merge(
        self,
        query: str,
        agent_results: list[dict[str, Any]],
        rag_chunks: list[dict[str, Any]] | None = None,
        citations: list[str] | None = None,
        language: str = "en",
    ) -> dict[str, Any]:
        if not agent_results:
            return {
                "merged_response": "No specialist agents were able to process your request. Please contact your nearest Kisan Call Centre (KCC).",
                "confidence_score": 0.0,
                "escalate": True,
            }

        sections: List[str] = []
        confidences: List[float] = []

        # 1. Disease Section
        for res in agent_results:
            if res.get("agent") == "disease_agent":
                crop = res.get("crop", "Crop")
                disease = res.get("disease", "Unknown")
                conf = float(res.get("confidence", 0.0))
                confidences.append(conf)
                sev = res.get("severity_index", 0)

                sec = (
                    f"### 🌿 Disease Diagnostic Findings\n"
                    f"- **Crop Identified:** {crop.capitalize()}\n"
                    f"- **Diagnosis:** {disease} (Confidence: {conf * 100:.1f}%)\n"
                    f"- **Severity Index:** Level {sev}/5\n"
                )
                if res.get("treatment_protocol"):
                    sec += f"- **Recommended Treatment:** {res['treatment_protocol']}\n"
                sections.append(sec)

        # 2. Crop Recommendation Section
        for res in agent_results:
            if res.get("agent") == "crop_agent":
                winner = res.get("winning_crop", "Crop")
                conf = float(res.get("confidence", 0.0))
                confidences.append(conf)

                sec = (
                    f"### 🌾 Crop Recommendation Advisory\n"
                    f"- **Recommended Crop:** {winner.capitalize()} (Suitability: {conf * 100:.1f}%)\n"
                )
                if res.get("top_3"):
                    top_str = ", ".join(f"{c.capitalize()} ({p*100:.1f}%)" for c, p in res["top_3"])
                    sec += f"- **Top Evaluated Options:** {top_str}\n"
                if res.get("advisory"):
                    sec += f"- **Agronomic Advice:** {res['advisory']}\n"
                sections.append(sec)

        # 3. Diagram Section
        for res in agent_results:
            if res.get("agent") == "diagram_agent":
                v_type = res.get("visual_type", "diagram")
                cap = res.get("caption", "")
                sec = (
                    f"### 📐 Illustrated Schematic ({v_type.capitalize()})\n"
                    f"{cap}\n"
                )
                sections.append(sec)

        # 4. Web Search Section
        for res in agent_results:
            if res.get("agent") == "web_search_agent":
                summary = res.get("summary", "")
                sec = (
                    f"### 🌐 Live Web Search & Government Updates\n"
                    f"{summary}\n"
                )
                sections.append(sec)
                confidences.append(0.88)

        # 5. Weather Advisory Section
        for res in agent_results:
            if res.get("agent") == "weather_agent":
                sec = (
                    f"### 🌦️ Weather & Irrigation Advisory\n"
                    f"- **Location:** {res.get('location')}\n"
                    f"- **Conditions:** {res.get('condition')} ({res.get('current_temp')}°C)\n"
                    f"- **Irrigation Advice:** {res.get('irrigation_advice')}\n"
                )
                if res.get("active_alert"):
                    sec += f"- **Alert:** {res['active_alert']}\n"
                sections.append(sec)
                confidences.append(0.90)

        # 6. Market Section
        for res in agent_results:
            if res.get("agent") == "market_agent":
                sec = (
                    f"### 📈 Mandi Market Intelligence\n"
                    f"- **Crop:** {res.get('crop')}\n"
                    f"- **Current Rate:** ₹{res.get('modal_price')}/quintal\n"
                    f"- **Price Outlook:** {res.get('trend_summary', 'Stable')}\n"
                )
                sections.append(sec)
                confidences.append(0.85)

        # 7. Nutrition Section
        for res in agent_results:
            if res.get("agent") == "nutrition_agent":
                sec = (
                    f"### 🧪 Soil & Nutrient Management\n"
                    f"- **Deficiency Identified:** {res.get('deficiency', 'None')}\n"
                    f"- **Dosage Recommendation:** {res.get('fertilizer_plan', 'Balanced NPK')}\n"
                )
                sections.append(sec)
                confidences.append(float(res.get("confidence", 0.85)))

        # 4. Citations & References
        all_citations = list(dict.fromkeys(citations or []))
        if all_citations:
            sections.append("### 📚 Grounded References\n" + "\n".join(f"- {c}" for c in all_citations))

        # Overall Confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.85
        escalate = avg_confidence < 0.70

        if escalate:
            sections.append(
                "\n> ⚠️ **Notice:** Diagnostic confidence is below the 70% certainty threshold. "
                "This query has been flagged for human verification by a Kisan Call Centre (KCC) agronomist."
            )

        merged_text = "\n\n".join(sections)

        return {
            "merged_response": merged_text,
            "confidence_score": round(avg_confidence, 3),
            "escalate": escalate,
        }
