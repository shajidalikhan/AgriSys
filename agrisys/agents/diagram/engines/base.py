"""Base interface for visual diagramming engines."""

from __future__ import annotations
from abc import ABC, abstractmethod
from agrisys.agents.diagram.models import DiagramRequest, DiagramOutput


class BaseVisualEngine(ABC):
    """Abstract interface for all visual rendering engines in AgriSys (ISP & LSP)."""

    @abstractmethod
    async def generate(self, request: DiagramRequest) -> DiagramOutput:
        """Generate diagram code or SVG markup for the given request."""
        ...

    @abstractmethod
    def supports_type(self, visual_type: str) -> bool:
        """Return True if this engine handles the requested visual type."""
        ...
