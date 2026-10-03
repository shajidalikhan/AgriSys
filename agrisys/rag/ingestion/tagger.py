"""Metadata Tagger for RAG Ingestion Pipeline.

Fulfills §10.1: Tags chunks with source, crop, state, domain, language,
and date_indexed metadata.
"""

from typing import Dict, List, Optional
import re
from datetime import datetime, timezone
from agrisys.rag.ingestion.models import ChunkMetadata

CROPS = [
    "wheat", "rice", "paddy", "tomato", "potato", "onion", "cotton",
    "maize", "sugarcane", "soybean", "mustard", "chilli", "groundnut",
    "gram", "apple", "mango", "banana", "citrus", "tea", "coffee",
    # Hindi crops
    "टमाटर", "गेहूं", "चावल", "धान", "आलू", "प्याज", "कपास", "मक्का", "गन्ना", "सरसों", "मिर्च"
]

STATES = [
    "UP", "Uttar Pradesh", "Maharashtra", "Punjab", "Haryana",
    "Madhya Pradesh", "MP", "Rajasthan", "Gujarat", "Bihar",
    "West Bengal", "Karnataka", "Andhra Pradesh", "AP", "Tamil Nadu",
    "Telangana", "Odisha", "Assam", "Kerala", "Himachal Pradesh"
]

STATE_NORM_MAP = {
    "uttar pradesh": "UP",
    "up": "UP",
    "madhya pradesh": "MP",
    "mp": "MP",
    "andhra pradesh": "AP",
    "ap": "AP",
}

DOMAIN_KEYWORDS = {
    "disease": [
        "blight", "rust", "fungus", "wilt", "mildew", "rot", "canker", "virus", "pest", "pathogen",
        "infestation", "symptom", "fungicide", "pesticide",
        "रोग", "झुलसा", "कवक", "कीट", "फफूंद", "कीटनाशक", "कवकनाशी", "लक्षण", "संक्रमण"
    ],
    "nutrition": [
        "nitrogen", "phosphorus", "potassium", "npk", "fertilizer", "deficiency", "chlorosis",
        "zinc", "urea", "manure", "micronutrient", "soil health", "ph",
        "उर्वरक", "खाद", "नाइट्रोजन", "फास्फोरस", "पोटाश", "पोषक", "कमी", "यूरिया"
    ],
    "market": [
        "mandi", "price", "msp", "market", "quintal", "rate", "agmarknet", "enam", "wholesale", "retail", "arrival",
        "मंडी", "भाव", "दाम", "मूल्य", "क्विंटल", "बाजार"
    ],
    "weather": [
        "rainfall", "temperature", "humidity", "monsoon", "irrigation", "forecast", "evapotranspiration", "eto", "drought", "frost",
        "मौसम", "वर्षा", "बारिश", "तापमान", "सिंचाई", "मानसून", "सूखा"
    ],
}


class MetadataTagger:
    """Extracts and tags standard agricultural metadata for knowledge chunks."""

    @classmethod
    def tag(
        cls,
        text: str,
        base_metadata: Optional[Dict[str, str]] = None,
        chunk_index: int = 0,
        doc_id: Optional[str] = None,
    ) -> ChunkMetadata:
        """Analyze text and combine with base metadata to produce ChunkMetadata."""
        meta = base_metadata or {}
        text_lower = text.lower()

        # 1. Source determination
        source = meta.get("source", "icar").lower()
        valid_sources = {"icar", "fao", "kcc", "agmarknet", "cgiar", "custom"}
        if source not in valid_sources:
            source = "icar"

        # 2. Crop detection
        crop = meta.get("crop")
        if not crop:
            for c in CROPS:
                if re.search(rf"\b{c}\b", text_lower):
                    crop = c
                    break

        # 3. State detection
        state = meta.get("state")
        if not state:
            for s in STATES:
                if re.search(rf"\b{re.escape(s.lower())}\b", text_lower):
                    state = STATE_NORM_MAP.get(s.lower(), s)
                    break

        # 4. Domain classification
        domain = meta.get("domain")
        if not domain:
            scores = {d: 0 for d in DOMAIN_KEYWORDS}
            for d, keywords in DOMAIN_KEYWORDS.items():
                for kw in keywords:
                    if kw in text_lower:
                        scores[d] += 1
            best_domain, best_score = max(scores.items(), key=lambda item: item[1])
            domain = best_domain if best_score > 0 else "general"

        # 5. Language detection (checks for Devanagari Unicode range \u0900-\u097F)
        devanagari_chars = len(re.findall(r"[\u0900-\u097F]", text))
        total_chars = len(text)
        language = "hi" if total_chars > 0 and (devanagari_chars / total_chars) > 0.15 else "en"

        return ChunkMetadata(
            source=source,
            crop=crop,
            state=state,
            domain=domain,
            language=language,
            date_indexed=datetime.now(timezone.utc).isoformat(),
            doc_id=doc_id,
            chunk_index=chunk_index,
        )
