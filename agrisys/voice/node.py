"""LangGraph state nodes for Voice Processing & Speech Synthesis."""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Any
from agrisys.voice.pipeline import VoicePipeline

logger = logging.getLogger(__name__)


async def voice_processor_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph entry node executing before Intent Router.
    If voice audio was provided, transcribes speech into query text and detects language.
    """
    audio_path = state.get("voice_audio_path")
    audio_bytes = state.get("audio_bytes")

    # If neither audio path nor bytes provided, pass through unchanged
    if not audio_path and not audio_bytes:
        return {}

    pipeline = VoicePipeline()

    if audio_bytes is None and audio_path:
        p = Path(audio_path)
        if p.exists():
            audio_bytes = p.read_bytes()
        else:
            logger.warning("Voice audio file not found at %s", audio_path)
            return {}

    filename = Path(audio_path).name if audio_path else "mic_input.wav"
    language_hint = state.get("language")

    result, saved_path = await pipeline.process_incoming_audio(
        audio_bytes=audio_bytes,
        language=language_hint if language_hint and language_hint != "auto" else None,
        filename=filename,
    )

    return {
        "query": result.normalized_transcript,
        "language": result.detected_language,
        "voice_audio_path": saved_path,
    }


async def tts_generator_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph exit node executing after Hallucination Guard.
    Synthesizes merged advisory text into natural audio speech if audio was requested or voice mode was used.
    """
    merged_text = state.get("merged_response", "")
    language = state.get("language", "hi")
    had_voice_input = bool(state.get("voice_audio_path") or state.get("audio_bytes"))
    generate_tts = state.get("generate_tts", False)

    # Synthesize audio if voice mode was active or audio explicitly requested
    if not merged_text or not (had_voice_input or generate_tts):
        return {}

    pipeline = VoicePipeline()
    # Synthesize speech in detected farmer language
    synth_result = await pipeline.generate_speech_response(
        text=merged_text,
        language=language,
    )

    return {
        "tts_audio_path": synth_result.audio_path,
    }
