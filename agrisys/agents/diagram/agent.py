"""Diagram Generation Agent coordinator and LangGraph node."""

from __future__ import annotations
import logging
from typing import Any
from agrisys.agents.diagram.models import DiagramRequest, DiagramOutput, VisualType
from agrisys.agents.diagram.engines.base import BaseVisualEngine
from agrisys.agents.diagram.engines.mermaid_engine import MermaidEngine
from agrisys.agents.diagram.engines.svg_schematic_engine import SvgSchematicEngine
from agrisys.agents.diagram.sanitizer import SelfHealingSyntaxLinter
from agrisys.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class DiagramAgent:
    """Coordinates Engine A (Mermaid) and Engine B (2D SVG) to render agricultural schematics."""

    def __init__(self, llm_provider: BaseLLMProvider | None = None):
        self.llm_provider = llm_provider
        self.mermaid_engine = MermaidEngine(llm_provider=llm_provider)
        self.svg_engine = SvgSchematicEngine()

    async def generate_diagram(self, request: DiagramRequest) -> DiagramOutput:
        """Route to appropriate visual engine and apply self-healing validation."""
        v_type = request.visual_type

        # Auto-route to SVG or Mermaid if not explicit
        if v_type and self.svg_engine.supports_type(v_type.value):
            output = await self.svg_engine.generate(request)
        elif v_type and self.mermaid_engine.supports_type(v_type.value):
            output = await self.mermaid_engine.generate(request)
        else:
            # Query-based routing
            q = request.query.lower()
            if any(k in q for k in [
                "spacing", "plant to plant", "row to row", "drip", "irrigation",
                "pipe", "lateral", "bed", "cross section", "pruning", "sucker", "trap"
            ]):
                output = await self.svg_engine.generate(request)
            else:
                output = await self.mermaid_engine.generate(request)

        # Apply Self-Healing Syntax Validation
        repaired_code, is_valid, note = SelfHealingSyntaxLinter.sanitize_and_validate(
            output.raw_code, output.engine_used
        )
        output.raw_code = repaired_code
        output.is_valid = is_valid
        output.validation_notes = note

        return output
