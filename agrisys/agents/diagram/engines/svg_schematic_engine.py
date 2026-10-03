"""Parametric 2D SVG Schematic Engine for physical agricultural illustrations."""

from __future__ import annotations
from typing import Any
from agrisys.agents.diagram.models import DiagramRequest, DiagramOutput, VisualType
from agrisys.agents.diagram.engines.base import BaseVisualEngine
from agrisys.agents.diagram.translator import BilingualLabelInjector


class SvgSchematicEngine(BaseVisualEngine):
    """Engine B: Procedurally generates crisp, lightweight, measured 2D SVG schematics."""

    SUPPORTED_TYPES = {
        VisualType.PLANTING_SPACING,
        VisualType.DRIP_IRRIGATION,
        VisualType.RAISED_BED_PROFILE,
        VisualType.CANOPY_PRUNING,
        VisualType.TRAP_DISTRIBUTION,
        VisualType.CUSTOM_2D_SVG,
    }

    def supports_type(self, visual_type: str) -> bool:
        try:
            vt = VisualType(visual_type)
            return vt in self.SUPPORTED_TYPES
        except ValueError:
            return False

    async def generate(self, request: DiagramRequest) -> DiagramOutput:
        v_type = request.visual_type or self._infer_visual_type(request.query)
        lang = request.language
        ctx = request.context_data

        if v_type == VisualType.DRIP_IRRIGATION:
            svg, caption, labels = self._build_drip_irrigation_svg(lang, ctx)
        elif v_type == VisualType.RAISED_BED_PROFILE:
            svg, caption, labels = self._build_raised_bed_svg(lang, ctx)
        elif v_type == VisualType.CANOPY_PRUNING:
            svg, caption, labels = self._build_canopy_pruning_svg(lang, ctx)
        elif v_type == VisualType.TRAP_DISTRIBUTION:
            svg, caption, labels = self._build_trap_distribution_svg(lang, ctx)
        else:
            # Default to planting spacing
            v_type = VisualType.PLANTING_SPACING
            svg, caption, labels = self._build_planting_spacing_svg(lang, ctx, request.crop_name)

        return DiagramOutput(
            visual_type=v_type,
            engine_used="svg_2d",
            raw_code=svg,
            caption=caption,
            bilingual_labels=labels,
            is_valid=True,
        )

    def _infer_visual_type(self, query: str) -> VisualType:
        q = query.lower()
        if any(w in q for w in ["drip", "irrigation", "pipe", "lateral", "filter"]):
            return VisualType.DRIP_IRRIGATION
        if any(w in q for w in ["bed", "mulch", "ridge", "furrow", "cross section"]):
            return VisualType.RAISED_BED_PROFILE
        if any(w in q for w in ["prun", "cut", "branch", "canopy", "sucker", "training"]):
            return VisualType.CANOPY_PRUNING
        if any(w in q for w in ["trap", "pheromone", "sticky", "ipm", "pest density"]):
            return VisualType.TRAP_DISTRIBUTION
        return VisualType.PLANTING_SPACING

    # -------------------------------------------------------------
    # 1. PLANTING SPACING SCHEMATIC
    # -------------------------------------------------------------
    def _build_planting_spacing_svg(
        self, lang: str, ctx: dict[str, Any], crop_name: str | None
    ) -> tuple[str, str, dict[str, str]]:
        r2r = ctx.get("row_to_row_cm", 60)
        p2p = ctx.get("plant_to_plant_cm", 45)
        crop = crop_name or ctx.get("crop", "Crop")

        r2r_lbl = BilingualLabelInjector.get_bilingual_label("row to row", lang) + f": {r2r} cm"
        p2p_lbl = BilingualLabelInjector.get_bilingual_label("plant to plant", lang) + f": {p2p} cm"

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 420" width="100%" height="100%">
  <defs>
    <linearGradient id="soilGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#8D6E63" />
      <stop offset="100%" stop-color="#5D4037" />
    </linearGradient>
    <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="#D32F2F" />
    </marker>
  </defs>

  <!-- Background Soil Bed -->
  <rect x="20" y="20" width="660" height="380" rx="12" fill="url(#soilGrad)" stroke="#3E2723" stroke-width="2"/>
  
  <!-- Furrow Tracks -->
  <line x1="40" y1="90" x2="660" y2="90" stroke="#4E342E" stroke-width="6" stroke-dasharray="10,6" />
  <line x1="40" y1="210" x2="660" y2="210" stroke="#4E342E" stroke-width="6" stroke-dasharray="10,6" />
  <line x1="40" y1="330" x2="660" y2="330" stroke="#4E342E" stroke-width="6" stroke-dasharray="10,6" />

  <!-- Plant Row 1 -->
  <g id="row1">
    <circle cx="120" cy="90" r="22" fill="#4CAF50" stroke="#2E7D32" stroke-width="3"/>
    <circle cx="280" cy="90" r="22" fill="#4CAF50" stroke="#2E7D32" stroke-width="3"/>
    <circle cx="440" cy="90" r="22" fill="#4CAF50" stroke="#2E7D32" stroke-width="3"/>
    <circle cx="600" cy="90" r="22" fill="#4CAF50" stroke="#2E7D32" stroke-width="3"/>
  </g>

  <!-- Plant Row 2 -->
  <g id="row2">
    <circle cx="120" cy="210" r="22" fill="#4CAF50" stroke="#2E7D32" stroke-width="3"/>
    <circle cx="280" cy="210" r="22" fill="#4CAF50" stroke="#2E7D32" stroke-width="3"/>
    <circle cx="440" cy="210" r="22" fill="#4CAF50" stroke="#2E7D32" stroke-width="3"/>
    <circle cx="600" cy="210" r="22" fill="#4CAF50" stroke="#2E7D32" stroke-width="3"/>
  </g>

  <!-- Plant Row 3 -->
  <g id="row3">
    <circle cx="120" cy="330" r="22" fill="#4CAF50" stroke="#2E7D32" stroke-width="3"/>
    <circle cx="280" cy="330" r="22" fill="#4CAF50" stroke="#2E7D32" stroke-width="3"/>
    <circle cx="440" cy="330" r="22" fill="#4CAF50" stroke="#2E7D32" stroke-width="3"/>
    <circle cx="600" cy="330" r="22" fill="#4CAF50" stroke="#2E7D32" stroke-width="3"/>
  </g>

  <!-- Plant to Plant Measurement Dimension -->
  <line x1="120" y1="45" x2="280" y2="45" stroke="#D32F2F" stroke-width="2.5" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
  <rect x="155" y="32" width="90" height="24" rx="4" fill="#FFFDE7" stroke="#F57F17"/>
  <text x="200" y="48" font-size="12" font-weight="bold" fill="#B71C1C" text-anchor="middle">{p2p_lbl}</text>

  <!-- Row to Row Measurement Dimension -->
  <line x1="60" y1="90" x2="60" y2="210" stroke="#D32F2F" stroke-width="2.5" marker-start="url(#arrow)" marker-end="url(#arrow)"/>
  <rect x="15" y="138" width="105" height="24" rx="4" fill="#FFFDE7" stroke="#F57F17"/>
  <text x="67" y="154" font-size="11" font-weight="bold" fill="#B71C1C" text-anchor="middle">{r2r_lbl}</text>

  <!-- Title Badge -->
  <rect x="420" y="360" width="240" height="30" rx="6" fill="#1B5E20" opacity="0.9"/>
  <text x="540" y="380" font-size="13" font-weight="bold" fill="#FFFFFF" text-anchor="middle">{crop.capitalize()} Spacing Layout</text>
</svg>'''

        caption = f"Planting layout for {crop} showing row-to-row ({r2r} cm) and plant-to-plant ({p2p} cm) spacing."
        labels = {"row_to_row": r2r_lbl, "plant_to_plant": p2p_lbl}
        return svg, caption, labels

    # -------------------------------------------------------------
    # 2. DRIP IRRIGATION SCHEMATIC
    # -------------------------------------------------------------
    def _build_drip_irrigation_svg(
        self, lang: str, ctx: dict[str, Any]
    ) -> tuple[str, str, dict[str, str]]:
        src_lbl = BilingualLabelInjector.get_bilingual_label("water source", lang)
        pump_lbl = BilingualLabelInjector.get_bilingual_label("pump", lang)
        filt_lbl = BilingualLabelInjector.get_bilingual_label("sand filter", lang)
        main_lbl = BilingualLabelInjector.get_bilingual_label("main pipe", lang)
        lat_lbl = BilingualLabelInjector.get_bilingual_label("drip lateral", lang)
        drip_lbl = BilingualLabelInjector.get_bilingual_label("dripper", lang)

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 740 430" width="100%" height="100%">
  <defs>
    <linearGradient id="waterGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#0288D1"/>
      <stop offset="100%" stop-color="#01579B"/>
    </linearGradient>
  </defs>

  <!-- Background Field -->
  <rect x="10" y="10" width="720" height="410" rx="10" fill="#E8F5E9" stroke="#81C784" stroke-width="2"/>

  <!-- Water Source & Pump House -->
  <rect x="30" y="40" width="90" height="90" rx="8" fill="url(#waterGrad)" />
  <text x="75" y="85" font-size="11" font-weight="bold" fill="#FFFFFF" text-anchor="middle">{src_lbl}</text>

  <rect x="150" y="55" width="70" height="60" rx="6" fill="#455A64" />
  <text x="185" y="90" font-size="11" font-weight="bold" fill="#FFFFFF" text-anchor="middle">{pump_lbl}</text>
  <line x1="120" y1="85" x2="150" y2="85" stroke="#0277BD" stroke-width="8"/>

  <!-- Filter & Venturi Unit -->
  <circle cx="270" cy="85" r="28" fill="#F57C00" stroke="#E65100" stroke-width="3"/>
  <text x="270" y="88" font-size="10" font-weight="bold" fill="#FFFFFF" text-anchor="middle">{filt_lbl}</text>
  <line x1="220" y1="85" x2="242" y2="85" stroke="#0277BD" stroke-width="8"/>

  <!-- Main Pipeline (50mm) -->
  <line x1="298" y1="85" x2="680" y2="85" stroke="#01579B" stroke-width="12"/>
  <rect x="380" y="60" width="160" height="20" rx="3" fill="#E1F5FE" stroke="#0288D1"/>
  <text x="460" y="74" font-size="10" font-weight="bold" fill="#01579B" text-anchor="middle">{main_lbl}</text>

  <!-- Sub-Main (Vertical distributor) -->
  <line x1="680" y1="85" x2="680" y2="380" stroke="#0288D1" stroke-width="10"/>

  <!-- Lateral 1 -->
  <line x1="680" y1="160" x2="120" y2="160" stroke="#37474F" stroke-width="5"/>
  <circle cx="560" cy="160" r="4" fill="#0288D1"/>
  <circle cx="440" cy="160" r="4" fill="#0288D1"/>
  <circle cx="320" cy="160" r="4" fill="#0288D1"/>
  <circle cx="200" cy="160" r="4" fill="#0288D1"/>

  <!-- Lateral 2 -->
  <line x1="680" y1="250" x2="120" y2="250" stroke="#37474F" stroke-width="5"/>
  <circle cx="560" cy="250" r="4" fill="#0288D1"/>
  <circle cx="440" cy="250" r="4" fill="#0288D1"/>
  <circle cx="320" cy="250" r="4" fill="#0288D1"/>
  <circle cx="200" cy="250" r="4" fill="#0288D1"/>

  <!-- Lateral 3 -->
  <line x1="680" y1="340" x2="120" y2="340" stroke="#37474F" stroke-width="5"/>
  <circle cx="560" cy="340" r="4" fill="#0288D1"/>
  <circle cx="440" cy="340" r="4" fill="#0288D1"/>
  <circle cx="320" cy="340" r="4" fill="#0288D1"/>
  <circle cx="200" cy="340" r="4" fill="#0288D1"/>

  <!-- Labels & Callouts -->
  <rect x="230" y="175" width="140" height="22" rx="4" fill="#ECEFF1" stroke="#455A64"/>
  <text x="300" y="190" font-size="10" font-weight="bold" fill="#263238" text-anchor="middle">{lat_lbl}</text>

  <rect x="460" y="265" width="130" height="22" rx="4" fill="#E0F7FA" stroke="#00838F"/>
  <text x="525" y="280" font-size="10" font-weight="bold" fill="#006064" text-anchor="middle">{drip_lbl}</text>
</svg>'''

        caption = "Technical layout of a pressurized drip irrigation network from source to inline emitters."
        labels = {"source": src_lbl, "pump": pump_lbl, "filter": filt_lbl, "main": main_lbl, "lateral": lat_lbl}
        return svg, caption, labels

    # -------------------------------------------------------------
    # 3. RAISED BED & MULCH PROFILE SCHEMATIC
    # -------------------------------------------------------------
    def _build_raised_bed_svg(
        self, lang: str, ctx: dict[str, Any]
    ) -> tuple[str, str, dict[str, str]]:
        bed_w = ctx.get("bed_top_width_cm", 90)
        bed_h = ctx.get("bed_height_cm", 15)
        furrow_w = ctx.get("furrow_width_cm", 30)

        mulch_lbl = BilingualLabelInjector.get_bilingual_label("mulch film", lang)
        bed_lbl = BilingualLabelInjector.get_bilingual_label("soil bed", lang)
        tape_lbl = BilingualLabelInjector.get_bilingual_label("drip tape", lang)
        seed_lbl = BilingualLabelInjector.get_bilingual_label("seed pocket", lang)

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 380" width="100%" height="100%">
  <!-- Sky / Background -->
  <rect x="10" y="10" width="700" height="360" rx="10" fill="#F1F8E9" stroke="#C5E1A5" stroke-width="2"/>

  <!-- Native Soil Sub-base -->
  <rect x="30" y="270" width="660" height="80" fill="#4E342E" />

  <!-- Raised Bed Trapezoid Cross-Section -->
  <!-- Base 120cm, Top 90cm, Furrows on sides -->
  <polygon points="120,270 190,160 530,160 600,270" fill="#795548" stroke="#3E2723" stroke-width="3"/>
  <text x="360" y="225" font-size="14" font-weight="bold" fill="#FFFFFF" text-anchor="middle">{bed_lbl}</text>

  <!-- Silver-Black Mulch Film Sheet -->
  <path d="M 180 160 L 540 160" stroke="#37474F" stroke-width="7" stroke-linecap="round"/>
  <path d="M 180 160 L 540 160" stroke="#ECEFF1" stroke-width="2.5" stroke-dasharray="8,4"/>

  <!-- Drip Tape (Under mulch) -->
  <circle cx="360" cy="180" r="10" fill="#0288D1" stroke="#01579B" stroke-width="2"/>
  <text x="360" y="184" font-size="8" font-weight="bold" fill="#FFFFFF" text-anchor="middle">DRIP</text>

  <!-- Seed / Plant Holes -->
  <circle cx="260" cy="155" r="8" fill="#4CAF50" stroke="#1B5E20" stroke-width="2"/>
  <circle cx="460" cy="155" r="8" fill="#4CAF50" stroke="#1B5E20" stroke-width="2"/>

  <!-- Sprout Leaves -->
  <path d="M 260 155 Q 245 130 255 120 Q 270 135 260 155" fill="#66BB6A"/>
  <path d="M 460 155 Q 445 130 455 120 Q 470 135 460 155" fill="#66BB6A"/>

  <!-- Dimension Lines -->
  <!-- Top Width -->
  <line x1="190" y1="130" x2="530" y2="130" stroke="#D32F2F" stroke-width="2"/>
  <rect x="315" y="118" width="90" height="22" rx="4" fill="#FFFDE7" stroke="#F57F17"/>
  <text x="360" y="133" font-size="11" font-weight="bold" fill="#B71C1C" text-anchor="middle">{bed_w} cm Top</text>

  <!-- Height -->
  <line x1="620" y1="160" x2="620" y2="270" stroke="#D32F2F" stroke-width="2"/>
  <rect x="630" y="200" width="70" height="22" rx="4" fill="#FFFDE7" stroke="#F57F17"/>
  <text x="665" y="215" font-size="11" font-weight="bold" fill="#B71C1C" text-anchor="middle">{bed_h} cm</text>

  <!-- Callouts -->
  <text x="550" y="145" font-size="10" font-weight="bold" fill="#263238">{mulch_lbl}</text>
  <text x="360" y="250" font-size="10" font-weight="bold" fill="#E1F5FE" text-anchor="middle">{tape_lbl}</text>
</svg>'''

        caption = f"Raised bed cross-section: {bed_w} cm top width, {bed_h} cm height with silver-black mulch and drip tape."
        labels = {"bed": bed_lbl, "mulch": mulch_lbl, "drip_tape": tape_lbl, "seed": seed_lbl}
        return svg, caption, labels

    # -------------------------------------------------------------
    # 4. CANOPY PRUNING SCHEMATIC
    # -------------------------------------------------------------
    def _build_canopy_pruning_svg(
        self, lang: str, ctx: dict[str, Any]
    ) -> tuple[str, str, dict[str, str]]:
        cut_lbl = BilingualLabelInjector.get_bilingual_label("pruning cut", lang)
        leader_lbl = BilingualLabelInjector.get_bilingual_label("leader branch", lang)
        sucker_lbl = BilingualLabelInjector.get_bilingual_label("sucker", lang)
        fruit_lbl = BilingualLabelInjector.get_bilingual_label("fruiting branch", lang)

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 400" width="100%" height="100%">
  <!-- Sky -->
  <rect x="10" y="10" width="680" height="380" rx="10" fill="#E8F5E9" stroke="#A5D6A7" stroke-width="2"/>
  <!-- Soil Base -->
  <rect x="20" y="340" width="660" height="40" fill="#5D4037" />

  <!-- Main Trunk / Leader -->
  <path d="M 340 340 L 340 180 Q 340 120 350 80" stroke="#795548" stroke-width="24" stroke-linecap="round"/>
  <text x="385" y="110" font-size="11" font-weight="bold" fill="#3E2723">{leader_lbl}</text>

  <!-- Left Scaffold Branch (Keep) -->
  <path d="M 340 250 Q 270 220 200 170" stroke="#795548" stroke-width="14" stroke-linecap="round"/>
  <circle cx="200" cy="170" r="14" fill="#43A047"/>
  <circle cx="170" cy="150" r="10" fill="#E53935"/>
  <text x="180" y="210" font-size="10" font-weight="bold" fill="#1B5E20">{fruit_lbl}</text>

  <!-- Right Scaffold Branch (Keep) -->
  <path d="M 340 230 Q 430 200 500 150" stroke="#795548" stroke-width="14" stroke-linecap="round"/>
  <circle cx="500" cy="150" r="14" fill="#43A047"/>
  <circle cx="530" cy="140" r="10" fill="#E53935"/>

  <!-- Water Shoot / Sucker (To Cut) -->
  <path d="M 340 290 Q 280 270 230 260" stroke="#8D6E63" stroke-width="9" stroke-linecap="round"/>
  <text x="210" y="300" font-size="10" font-weight="bold" fill="#D32F2F">{sucker_lbl}</text>

  <!-- Cut Marks (45 Degree Red Dashes) -->
  <line x1="280" y1="265" x2="300" y2="295" stroke="#D32F2F" stroke-width="5" stroke-dasharray="6,3"/>
  <rect x="235" y="240" width="130" height="20" rx="4" fill="#FFCDD2" stroke="#E53935"/>
  <text x="300" y="254" font-size="10" font-weight="bold" fill="#B71C1C" text-anchor="middle">{cut_lbl}</text>
</svg>'''

        caption = "Canopy training guide: Prune aggressive suckers and diseased wood at 45° angle while preserving fruiting scaffolds."
        labels = {"cut": cut_lbl, "leader": leader_lbl, "sucker": sucker_lbl, "fruiting": fruit_lbl}
        return svg, caption, labels

    # -------------------------------------------------------------
    # 5. PHEROMONE TRAP DISTRIBUTION SCHEMATIC
    # -------------------------------------------------------------
    def _build_trap_distribution_svg(
        self, lang: str, ctx: dict[str, Any]
    ) -> tuple[str, str, dict[str, str]]:
        trap_lbl = BilingualLabelInjector.get_bilingual_label("pheromone trap", lang)
        wind_lbl = BilingualLabelInjector.get_bilingual_label("wind direction", lang)
        h_lbl = BilingualLabelInjector.get_bilingual_label("trap height", lang)

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 400" width="100%" height="100%">
  <!-- Field Border (1 Acre) -->
  <rect x="20" y="20" width="660" height="360" rx="8" fill="#F1F8E9" stroke="#2E7D32" stroke-width="3"/>
  <text x="350" y="45" font-size="14" font-weight="bold" fill="#1B5E20" text-anchor="middle">1 Acre Field Boundary (1-एकड़ प्रक्षेत्र)</text>

  <!-- Wind Direction Indicator -->
  <line x1="60" y1="80" x2="160" y2="80" stroke="#0288D1" stroke-width="4" marker-end="url(#arrow)"/>
  <text x="110" y="70" font-size="10" font-weight="bold" fill="#01579B" text-anchor="middle">{wind_lbl} ➡</text>

  <!-- 6 Traps Evenly Distributed -->
  <!-- Trap 1 -->
  <g transform="translate(150, 120)">
    <rect x="-15" y="-20" width="30" height="40" rx="4" fill="#FBC02D" stroke="#F57F17" stroke-width="2"/>
    <circle cx="0" cy="0" r="6" fill="#D32F2F"/>
  </g>
  <!-- Trap 2 -->
  <g transform="translate(350, 120)">
    <rect x="-15" y="-20" width="30" height="40" rx="4" fill="#FBC02D" stroke="#F57F17" stroke-width="2"/>
    <circle cx="0" cy="0" r="6" fill="#D32F2F"/>
  </g>
  <!-- Trap 3 -->
  <g transform="translate(550, 120)">
    <rect x="-15" y="-20" width="30" height="40" rx="4" fill="#FBC02D" stroke="#F57F17" stroke-width="2"/>
    <circle cx="0" cy="0" r="6" fill="#D32F2F"/>
  </g>
  <!-- Trap 4 -->
  <g transform="translate(150, 260)">
    <rect x="-15" y="-20" width="30" height="40" rx="4" fill="#FBC02D" stroke="#F57F17" stroke-width="2"/>
    <circle cx="0" cy="0" r="6" fill="#D32F2F"/>
  </g>
  <!-- Trap 5 -->
  <g transform="translate(350, 260)">
    <rect x="-15" y="-20" width="30" height="40" rx="4" fill="#FBC02D" stroke="#F57F17" stroke-width="2"/>
    <circle cx="0" cy="0" r="6" fill="#D32F2F"/>
  </g>
  <!-- Trap 6 -->
  <g transform="translate(550, 260)">
    <rect x="-15" y="-20" width="30" height="40" rx="4" fill="#FBC02D" stroke="#F57F17" stroke-width="2"/>
    <circle cx="0" cy="0" r="6" fill="#D32F2F"/>
  </g>

  <!-- Legend -->
  <rect x="220" y="325" width="260" height="35" rx="6" fill="#FFFDE7" stroke="#FBC02D"/>
  <text x="350" y="342" font-size="11" font-weight="bold" fill="#E65100" text-anchor="middle">{trap_lbl}</text>
  <text x="350" y="354" font-size="9" fill="#5D4037" text-anchor="middle">{h_lbl}</text>
</svg>'''

        caption = "1-acre pheromone trap distribution grid with 6 monitoring traps positioned across windward zones."
        labels = {"trap": trap_lbl, "wind": wind_lbl, "height": h_lbl}
        return svg, caption, labels
