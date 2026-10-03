"""Master Voice Pipeline coordinating ASR, TTS, script normalization, and audio persistence."""

from __future__ import annotations
import logging
from typing import Optional, Tuple

from agrisys.voice.models import TranscriptionResult, SynthesisResult
from agrisys.voice.asr import BaseASRProvider, WhisperASRProvider
from agrisys.voice.tts import BaseTTSProvider, OpenAITTSProvider
from agrisys.voice.storage import AudioStorageManager
from agrisys.voice.normalizer import IndicTextNormalizer, IndicLanguageDetector

logger = logging.getLogger(__name__)


class VoicePipeline:
    """Coordinates end-to-end speech recognition and speech synthesis."""

    def __init__(
        self,
        asr_provider: BaseASRProvider | None = None,
        tts_provider: BaseTTSProvider | None = None,
        storage_manager: AudioStorageManager | None = None,
    ):
        self.asr = asr_provider or WhisperASRProvider()
        self.tts = tts_provider or OpenAITTSProvider()
        self.storage = storage_manager or AudioStorageManager()

    async def process_incoming_audio(
        self,
        audio_bytes: bytes,
        language: str | None = None,
        filename: str = "recording.wav",
    ) -> tuple[TranscriptionResult, str]:
        """
        Saves incoming microphone recording, transcribes speech, normalizes script,
        and returns (TranscriptionResult, saved_audio_path).
        """
        # 1. Save audio recording to artifact store
        saved_path, _ = self.storage.save_audio(
            audio_bytes=audio_bytes,
            extension=filename.split(".")[-1],
            prefix="mic_in",
        )

        # 2. ASR Transcription
        result = await self.asr.transcribe(
            audio_bytes=audio_bytes,
            language=language,
            filename=filename,
        )

        # 3. Clean script and detect language if unassigned
        cleaned_text = IndicTextNormalizer.normalize(result.raw_transcript)
        result.normalized_transcript = cleaned_text

        if not language or language == "auto":
            result.detected_language = IndicLanguageDetector.detect_language(cleaned_text)

        logger.info("ASR Transcription: '%s' [%s]", cleaned_text, result.detected_language)
        return result, saved_path

    async def generate_speech_response(
        self,
        text: str,
        language: str = "hi",
        speed: float = 1.0,
    ) -> SynthesisResult:
        """
        Synthesizes advisory text into natural audio speech and saves artifact.
        """
        # 1. Synthesize audio bytes
        audio_bytes, fmt = await self.tts.synthesize(text=text, language=language)

        # 2. Persist audio
        saved_path, public_url = self.storage.save_audio(
            audio_bytes=audio_bytes,
            extension=fmt,
            prefix="tts_out",
        )

        duration = self.storage.get_wav_duration(saved_path) if fmt == "wav" else max(1.5, len(text) / 14.0)

        logger.info("Synthesized speech response (%s, %.1fs) at %s", fmt, duration, public_url)

        return SynthesisResult(
            audio_path=saved_path,
            audio_url=public_url,
            language=language,
            duration_seconds=duration,
            audio_format=fmt,
            sampling_rate=16000 if fmt == "wav" else 24000,
        )
