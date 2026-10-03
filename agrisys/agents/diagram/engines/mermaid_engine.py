"""Mermaid.js workflow and timeline engine."""

from __future__ import annotations
from typing import Any
from agrisys.agents.diagram.models import DiagramRequest, DiagramOutput, VisualType
from agrisys.agents.diagram.engines.base import BaseVisualEngine
from agrisys.agents.diagram.translator import BilingualLabelInjector
from agrisys.providers.base import BaseLLMProvider


class MermaidEngine(BaseVisualEngine):
    """Engine A: Generates valid, structured Mermaid.js diagrams for workflows and calendars."""

    SUPPORTED_TYPES = {
        VisualType.FLOWCHART,
        VisualType.GANTT,
        VisualType.TIMELINE,
        VisualType.MINDMAP,
        VisualType.PIE,
    }

    def __init__(self, llm_provider: BaseLLMProvider | None = None):
        self.llm_provider = llm_provider

    def supports_type(self, visual_type: str) -> bool:
        try:
            vt = VisualType(visual_type)
            return vt in self.SUPPORTED_TYPES
        except ValueError:
            return False

    async def generate(self, request: DiagramRequest) -> DiagramOutput:
        v_type = request.visual_type or self._infer_mermaid_type(request.query)
        lang = request.language
        ctx = request.context_data
        crop = request.crop_name or ctx.get("crop", "Crop")

        # Check if LLM provider can generate customized Mermaid code
        if self.llm_provider:
            try:
                code, caption = await self._generate_with_llm(request, v_type, crop, lang)
                return DiagramOutput(
                    visual_type=v_type,
                    engine_used="mermaid",
                    raw_code=code,
                    caption=caption,
                    bilingual_labels={},
                    is_valid=True,
                )
            except Exception:
                pass  # Fall back to procedural template

        # Procedural fallback templates
        if v_type == VisualType.GANTT:
            code, caption = self._build_gantt_calendar(crop, lang, ctx)
        elif v_type == VisualType.TIMELINE:
            code, caption = self._build_timeline(crop, lang, ctx)
        elif v_type == VisualType.PIE:
            code, caption = self._build_pie_chart(crop, lang, ctx)
        else:
            v_type = VisualType.FLOWCHART
            code, caption = self._build_flowchart(crop, lang, ctx)

        return DiagramOutput(
            visual_type=v_type,
            engine_used="mermaid",
            raw_code=code,
            caption=caption,
            bilingual_labels={},
            is_valid=True,
        )

    def _infer_mermaid_type(self, query: str) -> VisualType:
        q = query.lower()
        if any(w in q for w in ["calendar", "gantt", "schedule", "sow date", "harvest date"]):
            return VisualType.GANTT
        if any(w in q for w in ["timeline", "stage", "phase", "growth"]):
            return VisualType.TIMELINE
        if any(w in q for w in ["pie", "ratio", "proportion", "dose split", "fertilizer mix"]):
            return VisualType.PIE
        if any(w in q for w in ["mindmap", "concept", "options"]):
            return VisualType.MINDMAP
        return VisualType.FLOWCHART

    def _build_gantt_calendar(self, crop: str, lang: str, ctx: dict[str, Any]) -> tuple[str, str]:
        sow_lbl = BilingualLabelInjector.get_bilingual_label("sowing", lang)
        veg_lbl = BilingualLabelInjector.get_bilingual_label("vegetative", lang)
        flow_lbl = BilingualLabelInjector.get_bilingual_label("flowering", lang)
        harv_lbl = BilingualLabelInjector.get_bilingual_label("harvesting", lang)

        code = f"""gantt
    title {crop.capitalize()} Sowing & Management Calendar
    dateFormat  YYYY-MM-DD
    axisFormat  %b
    section Field Prep
    Land Preparation & Basal Dose :active, a1, 2026-06-01, 15d
    section Crop Growth
    {sow_lbl}                     :crit, a2, 2026-06-15, 10d
    {veg_lbl} & 1st Weeding        :a3, after a2, 35d
    {flow_lbl} & Top Dressing      :a4, after a3, 25d
    section Maturity
    {harv_lbl}                    :crit, a5, after a4, 20d"""
        caption = f"Seasonal agronomic Gantt calendar for {crop} from land preparation to harvest."
        return code, caption

    def _build_timeline(self, crop: str, lang: str, ctx: dict[str, Any]) -> tuple[str, str]:
        code = f"""timeline
    title {crop.capitalize()} Phenological Stages & Interventions
    Day 0-15 : Basal Fertilizer Application : Nursery Sowing
    Day 16-45 : Vegetative Growth : First Split Urea : Inter-cultivation
    Day 46-75 : Flowering & Pod Formation : Second Split Potassium : Pest Scouting
    Day 76-105 : Physiological Maturity : Pre-harvest Interval : Final Irrigation Termination"""
        caption = f"Phenological growth stages and critical nutrient intervention timeline for {crop}."
        return code, caption

    def _build_pie_chart(self, crop: str, lang: str, ctx: dict[str, Any]) -> tuple[str, str]:
        n = ctx.get("N", 100)
        p = ctx.get("P", 50)
        k = ctx.get("K", 50)
        code = f"""pie title {crop.capitalize()} Recommended NPK Fertilizer Ratio (kg/ha)
    "Nitrogen (N)" : {n}
    "Phosphorus (P)" : {p}
    "Potassium (K)" : {k}"""
        caption = f"Recommended NPK nutrient dosage distribution for {crop}."
        return code, caption

    def _build_flowchart(self, crop: str, lang: str, ctx: dict[str, Any]) -> tuple[str, str]:
        code = f"""flowchart TD
    A["Farmer Field Setup: {crop.capitalize()}"] --> B["Soil Health Test (NPK & pH)"]
    B --> C{{"pH between 6.0 and 7.5?"}}
    C -->|Yes| D["Apply Recommended Basal Dose"]
    C -->|No, Acidic| E["Apply Agricultural Lime (2-4 t/ha)"]
    C -->|No, Alkaline| F["Apply Gypsum & Organic Farmyard Manure"]
    D --> G["Sowing / Transplanting with Measured Spacing"]
    E --> D
    F --> D
    G --> H["Install Drip Irrigation & Mulch Sheet"]
    H --> I["Regular Scouting & Integrated Pest Management"]
    style D fill:#C8E6C9,stroke:#2E7D32
    style I fill:#BBDEFB,stroke:#1565C0"""
        caption = f"Decision workflow for {crop} agronomic establishment and soil amendment."
        return code, caption

    async def _generate_with_llm(
        self, request: DiagramRequest, v_type: VisualType, crop: str, lang: str
    ) -> tuple[str, str]:
        prompt = (
            f"Generate a valid Mermaid.js diagram definition for an agricultural advisory.\n"
            f"Diagram Type: {v_type.value}\n"
            f"Crop: {crop}\n"
            f"Farmer Request: {request.query}\n"
            f"Requirements:\n"
            f"- Return ONLY the Mermaid code block without backticks or markdown preamble.\n"
            f"- Do not use unescaped parentheses inside node text.\n"
            f"- Ground instructions in Indian agronomic standards (ICAR)."
        )
        response = await self.llm_provider.complete([{"role": "user", "content": prompt}])
        clean_code = response.strip()
        if clean_code.startswith("```mermaid"):
            clean_code = clean_code[len("```mermaid"):].strip()
        if clean_code.startswith("```"):
            clean_code = clean_code[3:].strip()
        if clean_code.endswith("```"):
            clean_code = clean_code[:-3].strip()
        caption = f"Mermaid diagram illustrating {crop} {v_type.value} workflow."
        return clean_code, caption
