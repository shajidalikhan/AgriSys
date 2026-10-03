"""Dedicated Crop Identification Tool & Discrepancy Resolver.

Fulfills Step 2 of the Sequential Crop-First Pipeline:
- Detects crop from leaf image using the best available crop model endpoint
- Resolves consensus/conflicts with farmer text hints (Improvement 2)
"""

from typing import List, Optional
import re
from agrisys.agents.disease.models import CropDetectionResult
from agrisys.agents.disease.registry import get_disease_tool, BaseDiseaseModelTool

KNOWN_CROPS = [
    "tomato", "potato", "corn", "wheat", "rice", "apple", "grape",
    "peach", "strawberry", "cotton", "soybean", "mustard", "chilli",
    "onion", "sugarcane", "banana", "mango", "citrus",
    # Hindi
    "टमाटर", "आलू", "गेहूं", "चावल", "धान", "कपास", "मक्का", "सरसों"
]

CROP_ALIAS_MAP = {
    "टमाटर": "tomato",
    "आलू": "potato",
    "गेहूं": "wheat",
    "चावल": "rice",
    "धान": "rice",
    "कपास": "cotton",
    "मक्का": "corn",
    "सरसों": "mustard",
    "paddy": "rice",
    "maize": "corn",
}


class CropDetector:
    """Detects crop type from leaf photo and correlates with farmer text query."""

    def __init__(self, tool: Optional[BaseDiseaseModelTool] = None) -> None:
        self.tool = tool or get_disease_tool("crop_detector")

    def extract_crop_hint(self, text: Optional[str]) -> Optional[str]:
        """Extract explicit crop mention from user message if present."""
        if not text:
            return None
        text_lower = text.lower()
        for crop in KNOWN_CROPS:
            if re.search(rf"\b{crop}\b", text_lower):
                return CROP_ALIAS_MAP.get(crop, crop)
        return None

    async def detect_crop(
        self,
        image_bytes: bytes,
        user_query: Optional[str] = None,
    ) -> CropDetectionResult:
        """Run crop detection and harmonize with farmer query."""
        pred = await self.tool.predict(image_bytes)
        vision_crop = pred.crop.lower()
        vision_conf = pred.confidence

        text_hint = self.extract_crop_hint(user_query)

        # Consensus Resolution (Improvement 2)
        if text_hint:
            if text_hint == vision_crop:
                return CropDetectionResult(
                    crop=vision_crop,
                    confidence=min(1.0, vision_conf + 0.05),
                    source="consensus",
                    top_candidates=[{"crop": vision_crop, "score": vision_conf}],
                )
            else:
                # Discrepancy detected
                note = f"User mentioned '{text_hint}', but image vision analysis detected '{vision_crop}' ({int(vision_conf*100)}% confidence)."
                # If vision confidence is high (> 0.80), trust vision with note; otherwise adopt user hint
                chosen_crop = vision_crop if vision_conf >= 0.80 else text_hint
                return CropDetectionResult(
                    crop=chosen_crop,
                    confidence=vision_conf if chosen_crop == vision_crop else 0.75,
                    source="vision" if chosen_crop == vision_crop else "text_hint",
                    top_candidates=[{"crop": vision_crop, "score": vision_conf}, {"crop": text_hint, "score": 0.75}],
                    discrepancy_note=note,
                )

        return CropDetectionResult(
            crop=vision_crop if vision_crop != "general" else "tomato",
            confidence=vision_conf,
            source="vision",
            top_candidates=[{"crop": vision_crop, "score": vision_conf}],
        )
