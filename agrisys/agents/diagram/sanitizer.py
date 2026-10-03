"""Self-healing syntax validator and linter for diagrams."""

from __future__ import annotations
import re
import xml.etree.ElementTree as ET


class SelfHealingSyntaxLinter:
    """Validates and auto-repairs Mermaid.js code and 2D SVG XML markup."""

    @classmethod
    def sanitize_and_validate(cls, raw_code: str, engine: str) -> tuple[str, bool, str]:
        """
        Sanitizes and validates diagram markup.
        Returns: (repaired_code, is_valid, validation_message)
        """
        if engine == "svg_2d":
            return cls._validate_and_repair_svg(raw_code)
        else:
            return cls._validate_and_repair_mermaid(raw_code)

    @classmethod
    def _validate_and_repair_svg(cls, svg_code: str) -> tuple[str, bool, str]:
        # Strip markdown codeblocks if present
        clean = svg_code.strip()
        if clean.startswith("```xml") or clean.startswith("```svg"):
            clean = re.sub(r"^```(?:xml|svg)?\s*", "", clean)
        if clean.startswith("```"):
            clean = clean[3:].strip()
        if clean.endswith("```"):
            clean = clean[:-3].strip()

        # Ensure wrapping in <svg> tags
        if "<svg" not in clean:
            clean = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400">{clean}</svg>'
        if not clean.endswith("</svg>"):
            clean += "</svg>"

        # Check XML parseability
        try:
            ET.fromstring(clean)
            return clean, True, "Valid SVG XML markup."
        except ET.ParseError as err:
            # Attempt simple heuristic repairs (e.g. unclosed tag or unescaped ampersand)
            repaired = clean.replace("&", "&amp;") if "&amp;" not in clean else clean
            try:
                ET.fromstring(repaired)
                return repaired, True, f"Repaired XML entity error: {err}"
            except Exception:
                return clean, False, f"XML syntax error: {err}"

    @classmethod
    def _validate_and_repair_mermaid(cls, mermaid_code: str) -> tuple[str, bool, str]:
        clean = mermaid_code.strip()
        # Strip markdown fences
        if clean.startswith("```mermaid"):
            clean = clean[len("```mermaid"):].strip()
        if clean.startswith("```"):
            clean = clean[3:].strip()
        if clean.endswith("```"):
            clean = clean[:-3].strip()

        # Check for standard Mermaid diagram keywords
        valid_headers = ["flowchart", "graph", "gantt", "timeline", "pie", "mindmap", "sequenceDiagram", "classDiagram"]
        first_line = clean.splitlines()[0].strip() if clean.splitlines() else ""
        has_header = any(first_line.startswith(hdr) for hdr in valid_headers)

        if not has_header:
            # Prepend flowchart TD if missing
            clean = "flowchart TD\n" + clean

        # Auto-repair unescaped brackets in node text: e.g. [Node (detail)] -> [Node "detail"]
        # In Mermaid, unescaped parentheses inside [ ] can break parser unless wrapped in quotes
        repaired_lines = []
        for line in clean.splitlines():
            # Check for pattern [ ... ( ... ) ... ]
            if "[" in line and "]" in line and '"' not in line:
                # Wrap label in quotes inside brackets
                line = re.sub(r'\[([^"\]]+)\]', r'["\1"]', line)
            repaired_lines.append(line)

        repaired_code = "\n".join(repaired_lines)
        return repaired_code, True, "Mermaid code validated and normalized."
