"""Indic Text Normalization & Script Language Detection."""

from __future__ import annotations
import re
import unicodedata
from typing import Dict, Optional

# Devnagari digits to Western digits mapping
DEVNAGARI_DIGITS = {
    "०": "0", "१": "1", "२": "2", "३": "3", "४": "4",
    "५": "5", "६": "6", "७": "7", "८": "8", "९": "9",
}

# Unicode Script Ranges for Major Indian Languages
SCRIPT_RANGES = [
    (re.compile(r"[\u0900-\u097F]"), "hi"),  # Devanagari (Hindi, Marathi)
    (re.compile(r"[\u0A00-\u0A7F]"), "pa"),  # Gurmukhi (Punjabi)
    (re.compile(r"[\u0980-\u09FF]"), "bn"),  # Bengali
    (re.compile(r"[\u0B80-\u0BFF]"), "ta"),  # Tamil
    (re.compile(r"[\u0C00-\u0C7F]"), "te"),  # Telugu
    (re.compile(r"[\u0A80-\u0AFF]"), "gu"),  # Gujarati
    (re.compile(r"[\u0C80-\u0CFF]"), "kn"),  # Kannada
    (re.compile(r"[\u0D00-\u0D7F]"), "ml"),  # Malayalam
    (re.compile(r"[a-zA-Z]"), "en"),         # Latin / English
]


# Common Indian agricultural abbreviation expansions
INDIC_AGRI_TERMS = {
    "किग्रा": "किलोग्राम",
    "कि.ग्रा.": "किलोग्राम",
    "हैक्टेयर": "हेक्टेयर",
    "हेक्टर": "हेक्टेयर",
    "हैक्टर": "हेक्टेयर",
}


class IndicTextNormalizer:
    """Normalizes Devnagari and Indic vernacular text outputs from ASR engines."""

    @staticmethod
    def normalize(text: str, language: str | None = None) -> str:
        if not text:
            return ""

        # 1. Unicode NFC Canonical Composition
        cleaned = unicodedata.normalize("NFC", text)

        # 2. Remove Zero-Width Non-Joiner (ZWNJ), Zero-Width Joiner (ZWJ), and BOM
        cleaned = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", cleaned)

        # 3. Convert Devnagari numerals to Western digits for numerical processing
        for dev_digit, west_digit in DEVNAGARI_DIGITS.items():
            cleaned = cleaned.replace(dev_digit, west_digit)

        # 4. Standardize punctuation & spacing around Indian danda (।)
        cleaned = cleaned.replace("।", ". ")

        # 5. Expand common agricultural abbreviations
        for abbr, full_term in INDIC_AGRI_TERMS.items():
            cleaned = cleaned.replace(abbr, full_term)

        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned


# Marathi distinctive markers (characters ळ, ॅ and frequent tokens)
MARATHI_DISTINCTIVE_REGEX = re.compile(r"[\u0933\u0945]|\b(आहे|आहेत|च्या|वर|पडले|झाले|आणि)\b")


class IndicLanguageDetector:
    """Heuristic script and keyword detector identifying language code from text or transcription snippet."""

    @staticmethod
    def detect_language(text: str, default: str = "en") -> str:
        if not text or not text.strip():
            return default

        # 1. Check for distinct Marathi markers within Devanagari text
        if re.search(r"[\u0900-\u097F]", text):
            if MARATHI_DISTINCTIVE_REGEX.search(text):
                return "mr"
            return "hi"

        # 2. Count character occurrences matching other scripts
        counts: dict[str, int] = {}
        for regex, lang_code in SCRIPT_RANGES:
            if lang_code == "hi":
                continue
            matches = len(regex.findall(text))
            counts[lang_code] = counts.get(lang_code, 0) + matches

        best_lang = max(counts, key=counts.get) if counts else default
        if counts.get(best_lang, 0) == 0:
            return default

        return best_lang

    @classmethod
    def detect_script(cls, text: str) -> str:
        """Alias for detect_language."""
        return cls.detect_language(text)
