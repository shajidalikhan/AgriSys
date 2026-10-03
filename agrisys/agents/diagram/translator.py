"""Bilingual Label Injector for agricultural diagrams."""

from __future__ import annotations

# Dictionary mapping common English agronomic visual terms to Hindi + English pairs
AGRONOMIC_BILINGUAL_MAP = {
    # Irrigation & Hydraulics
    "water source": "जल स्रोत (Water Source)",
    "water tank": "पानी की टंकी (Water Tank)",
    "pump": "मोटर पंप (Pump)",
    "filter": "फिल्टर (Filter)",
    "sand filter": "सैंड फिल्टर (Sand Filter)",
    "disc filter": "डिस्क फिल्टर (Disc Filter)",
    "venturi": "वेंचुरी उर्वरक इंजेक्टर (Venturi)",
    "main pipe": "मुख्य पाइप (Main Line) 50mm",
    "main line": "मुख्य पाइप (Main Line) 50mm",
    "sub main": "उप-मुख्य पाइप (Sub-Main) 32mm",
    "sub-main": "उप-मुख्य पाइप (Sub-Main) 32mm",
    "drip lateral": "ड्रिप लेटरल (Lateral Pipe) 16mm",
    "laterals": "ड्रिप लेटरल्स (Laterals) 16mm",
    "dripper": "ड्रिपर / एमीटर (Dripper) 2-4 LPH",
    "emitter": "ड्रिपर / एमीटर (Emitter) 2-4 LPH",
    "flush valve": "फ्लश वाल्व (Flush Valve)",
    "root zone": "जड़ क्षेत्र (Root Zone)",
    
    # Planting Spacing & Geometry
    "row to row": "कतार से कतार (Row-to-Row)",
    "plant to plant": "पौधे से पौधा (Plant-to-Plant)",
    "ridge": "मेड़ (Ridge)",
    "furrow": "नाली (Furrow)",
    "bed width": "बेड की चौड़ाई (Bed Width)",
    "furrow depth": "नाली की गहराई (Furrow Depth)",
    "tractor track": "ट्रैक्टर मार्ग (Tractor Path)",
    "paired row": "युग्मित कतार (Paired Row)",

    # Raised Bed & Mulch
    "mulch film": "मल्चिंग फिल्म (Mulch Film) 25 micron",
    "silver black mulch": "सिल्वर-ब्लैक मल्च (Silver-Black Mulch)",
    "seed pocket": "बीज रोपण बिंदु (Seed Pocket)",
    "soil bed": "उठी हुई क्यारी (Raised Bed)",
    "drip tape": "ड्रिप टेप (Drip Tape)",

    # Pruning & Canopy
    "main stem": "मुख्य तना (Main Stem)",
    "leader branch": "अग्रणी शाखा (Leader Branch)",
    "scaffold branch": "प्राथमिक शाखा (Scaffold Branch)",
    "fruiting branch": "फल देने वाली शाखा (Fruiting Wood)",
    "water sprout": "अवांछित प्ररोह / जल शाखा (Water Sprout)",
    "sucker": "सकर / निचली शाखा (Sucker)",
    "pruning cut": "४५° कोण पर कटाई (45° Angle Cut)",
    "diseased branch": "रोगग्रस्त शाखा (Diseased Branch)",

    # Traps & IPM
    "pheromone trap": "फेरोमोन ट्रैप (Pheromone Trap)",
    "sticky trap": "पीला चिपचिपा ट्रैप (Yellow Sticky Trap)",
    "trap height": "कैनोपी से ऊंचाई (Height above Canopy) 30cm",
    "wind direction": "हवा की दिशा (Wind Direction)",

    # Phenology / Gantt
    "land prep": "भूमि की तैयारी (Land Preparation)",
    "sowing": "बुवाई (Sowing / Transplanting)",
    "vegetative": "वानस्पतिक वृद्धि (Vegetative Stage)",
    "flowering": "फूल आने की अवस्था (Flowering Stage)",
    "fruiting": "फल विकास (Fruit Development)",
    "harvesting": "फसल कटाई (Harvesting)",
}


class BilingualLabelInjector:
    """Injects localized Hindi/English terms into diagram captions and text nodes."""

    @staticmethod
    def get_bilingual_label(term: str, language: str = "hi") -> str:
        """Return translated bilingual term if known, else original term."""
        if language == "en":
            return term
        clean = term.strip().lower()
        return AGRONOMIC_BILINGUAL_MAP.get(clean, term)

    @staticmethod
    def enrich_diagram_labels(text: str, language: str = "hi") -> tuple[str, dict[str, str]]:
        """Finds known terms in text/code and produces a replacement dictionary."""
        replacements = {}
        if language == "en":
            return text, replacements

        for en_term, bi_term in AGRONOMIC_BILINGUAL_MAP.items():
            if en_term in text.lower():
                replacements[en_term] = bi_term

        return text, replacements
