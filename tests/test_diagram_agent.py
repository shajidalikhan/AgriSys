"""Unit and integration tests for the Diagram Agent and 2D Visual Engines."""

import pytest
from agrisys.agents.diagram.models import DiagramRequest, VisualType
from agrisys.agents.diagram.engines.svg_schematic_engine import SvgSchematicEngine
from agrisys.agents.diagram.engines.mermaid_engine import MermaidEngine
from agrisys.agents.diagram.sanitizer import SelfHealingSyntaxLinter
from agrisys.agents.diagram.translator import BilingualLabelInjector
from agrisys.agents.diagram.agent import DiagramAgent


@pytest.mark.asyncio
async def test_svg_schematic_engine_planting_spacing():
    """Verify 2D SVG planting layout generation with measured dimensions."""
    engine = SvgSchematicEngine()
    req = DiagramRequest(
        query="show plant to plant spacing layout for tomato",
        visual_type=VisualType.PLANTING_SPACING,
        crop_name="tomato",
        language="hi",
        context_data={"row_to_row_cm": 60, "plant_to_plant_cm": 45},
    )
    out = await engine.generate(req)
    assert out.engine_used == "svg_2d"
    assert "<svg" in out.raw_code
    assert "</svg>" in out.raw_code
    assert "60 cm" in out.raw_code
    assert "45 cm" in out.raw_code
    assert out.is_valid is True


@pytest.mark.asyncio
async def test_svg_schematic_engine_drip_irrigation():
    """Verify 2D SVG drip irrigation network schematic."""
    engine = SvgSchematicEngine()
    req = DiagramRequest(
        query="drip irrigation layout pipe",
        visual_type=VisualType.DRIP_IRRIGATION,
        language="hi",
    )
    out = await engine.generate(req)
    assert out.engine_used == "svg_2d"
    assert "Main Line" in out.raw_code or "मुख्य पाइप" in out.raw_code
    assert "circle cx=" in out.raw_code  # emitters and filters


@pytest.mark.asyncio
async def test_svg_schematic_engine_raised_bed():
    """Verify 2D SVG raised bed cross-section schematic."""
    engine = SvgSchematicEngine()
    req = DiagramRequest(
        query="raised bed cross section with mulch",
        visual_type=VisualType.RAISED_BED_PROFILE,
        language="en",
        context_data={"bed_top_width_cm": 90, "bed_height_cm": 15},
    )
    out = await engine.generate(req)
    assert "90 cm Top" in out.raw_code
    assert "15 cm" in out.raw_code
    assert "DRIP" in out.raw_code


@pytest.mark.asyncio
async def test_svg_schematic_engine_canopy_pruning():
    """Verify 2D SVG canopy pruning guide."""
    engine = SvgSchematicEngine()
    req = DiagramRequest(
        query="pruning guide for apple branches",
        visual_type=VisualType.CANOPY_PRUNING,
        language="hi",
    )
    out = await engine.generate(req)
    assert "stroke-dasharray" in out.raw_code  # cut lines
    assert "Leader Branch" in out.raw_code or "अग्रणी शाखा" in out.raw_code


@pytest.mark.asyncio
async def test_svg_schematic_engine_trap_distribution():
    """Verify 2D SVG trap placement grid."""
    engine = SvgSchematicEngine()
    req = DiagramRequest(
        query="pheromone trap installation grid",
        visual_type=VisualType.TRAP_DISTRIBUTION,
        language="hi",
    )
    out = await engine.generate(req)
    assert "1 Acre Field Boundary" in out.raw_code
    assert "Pheromone Trap" in out.raw_code or "फेरोमोन ट्रैप" in out.raw_code


@pytest.mark.asyncio
async def test_mermaid_engine_gantt_and_flowchart():
    """Verify Mermaid Gantt sowing calendar and decision flowchart."""
    engine = MermaidEngine()
    req_gantt = DiagramRequest(
        query="sowing calendar schedule",
        visual_type=VisualType.GANTT,
        crop_name="wheat",
        language="en",
    )
    out_gantt = await engine.generate(req_gantt)
    assert out_gantt.engine_used == "mermaid"
    assert "gantt" in out_gantt.raw_code
    assert "section" in out_gantt.raw_code

    req_flow = DiagramRequest(
        query="soil preparation workflow",
        visual_type=VisualType.FLOWCHART,
        crop_name="rice",
    )
    out_flow = await engine.generate(req_flow)
    assert "flowchart TD" in out_flow.raw_code


def test_self_healing_syntax_linter():
    """Verify self-healing auto-repair for broken SVG and Mermaid syntax."""
    # 1. Broken XML entity
    broken_svg = '<svg viewBox="0 0 100 100"><text>N & P & K</text></svg>'
    repaired_svg, is_valid, note = SelfHealingSyntaxLinter.sanitize_and_validate(broken_svg, "svg_2d")
    assert is_valid is True
    assert "&amp;" in repaired_svg

    # 2. Broken Mermaid unescaped brackets
    broken_mermaid = 'A[Node (Unescaped)] --> B[Result]'
    repaired_mermaid, is_m_valid, m_note = SelfHealingSyntaxLinter.sanitize_and_validate(broken_mermaid, "mermaid")
    assert is_m_valid is True
    assert '"Node (Unescaped)"' in repaired_mermaid


@pytest.mark.asyncio
async def test_diagram_agent_end_to_end():
    """Verify DiagramAgent coordinator routing and output generation."""
    agent = DiagramAgent()
    req = DiagramRequest(query="draw drip irrigation system", language="hi")
    out = await agent.generate_diagram(req)
    assert out.is_valid is True
    assert out.engine_used == "svg_2d"
    assert "<svg" in out.raw_code
