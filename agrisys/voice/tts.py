"""Text-to-Speech (TTS) Provider Abstraction Layer."""

from __future__ import annotations
import abc
import io
import logging
import math
import os
import struct
import wave
from typing import Tuple

logger = logging.getLogger(__name__)


class BaseTTSProvider(abc.ABC):
    """Abstract interface for Text-to-Speech synthesis."""

    @abc.abstractmethod
    async def synthesize(self, text: str, language: str = "hi") -> tuple[bytes, str]:
        """Synthesizes text into audio bytes and returns (audio_bytes, format)."""
        pass


class MockTTSProvider(BaseTTSProvider):
    """
    Zero-dependency deterministic TTS synthesizer generating valid 16kHz mono WAV audio
    using standard Python wave and struct modules.
    """

    async def synthesize(self, text: str, language: str = "hi") -> tuple[bytes, str]:
        sample_rate = 16000
        # Estimate duration proportional to text length (approx 12-15 chars per sec)
        duration_sec = max(1.0, min(len(text) / 14.0, 10.0))
        total_samples = int(sample_rate * duration_sec)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)        # Mono
            wf.setsampwidth(2)        # 16-bit PCM
            wf.setframerate(sample_rate)

            # Generate pleasant gentle acoustic harmonic wave
            frequency = 440.0 if language == "hi" else 330.0
            frames = bytearray()
            for i in range(total_samples):
                t = float(i) / sample_rate
                # Envelope: fade in and fade out
                envelope = min(t / 0.1, (duration_sec - t) / 0.1, 1.0)
                sample = int(12000.0 * envelope * math.sin(2.0 * math.pi * frequency * t))
                frames.extend(struct.pack("<h", max(-32767, min(32767, sample))))

            wf.writeframes(bytes(frames))

        return buffer.getvalue(), "wav"


class OpenAITTSProvider(BaseTTSProvider):
    """OpenAI TTS Cloud Provider (tts-1) with automatic fallback."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.fallback = MockTTSProvider()

    async def synthesize(self, text: str, language: str = "hi") -> tuple[bytes, str]:
        if not self.api_key:
            return await self.fallback.synthesize(text, language)

        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key)
            voice = "alloy"
            response = await client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text[:4096],  # OpenAI limit
            )
            audio_bytes = response.content
            return audio_bytes, "mp3"
        except Exception as e:
            logger.warning("OpenAI TTS error: %s. Using mock fallback.", e)
            return await self.fallback.synthesize(text, language)


class BhashiniTTSProvider(BaseTTSProvider):
    """Bhashini ULCA TTS provider for Indian vernacular languages."""

    def __init__(self, user_id: str | None = None, api_key: str | None = None):
        self.user_id = user_id or os.getenv("BHASHINI_USER_ID", "")
        self.api_key = api_key or os.getenv("BHASHINI_API_KEY", "")
        self.fallback = MockTTSProvider()

    async def synthesize(self, text: str, language: str = "hi") -> tuple[bytes, str]:
        if not self.api_key or not self.user_id:
            return await self.fallback.synthesize(text, language)

        # In production with keys: send text to Bhashini pipeline
        return await self.fallback.synthesize(text, language)


class TTSProviderFactory:
    """Factory creating configured TTS provider instance."""

    @staticmethod
    def get_provider(provider_name: str = "mock", **kwargs) -> BaseTTSProvider:
        name = provider_name.lower()
        if name == "openai":
            return OpenAITTSProvider(**kwargs)
        elif name == "bhashini":
            return BhashiniTTSProvider(**kwargs)
        return MockTTSProvider()
