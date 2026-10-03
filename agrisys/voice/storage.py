"""Audio file persistence and metadata management for Voice Pipeline."""

from __future__ import annotations
import logging
import os
import uuid
import wave
from pathlib import Path
from typing import Optional, Tuple
from agrisys.voice.models import AudioMetadata

logger = logging.getLogger(__name__)

DEFAULT_AUDIO_DIR = Path("data/artifacts/audio")


class AudioStorageManager:
    """Stores incoming microphone audio and synthesized speech artifacts."""

    def __init__(self, base_dir: Path = DEFAULT_AUDIO_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_audio(self, audio_bytes: bytes, extension: str = "wav", prefix: str = "rec") -> tuple[str, str]:
        """
        Saves raw audio bytes to disk and returns (absolute_filepath, public_url).
        """
        unique_name = f"{prefix}_{uuid.uuid4().hex[:10]}.{extension.lstrip('.')}"
        file_path = self.base_dir / unique_name
        file_path.write_bytes(audio_bytes)

        public_url = f"/static/audio/{unique_name}"
        logger.debug("Saved audio artifact (%d bytes) to %s", len(audio_bytes), file_path)
        return str(file_path.resolve()), public_url

    def read_audio(self, filepath: str | Path) -> bytes:
        """Reads audio bytes from disk."""
        p = Path(filepath)
        if not p.exists():
            raise FileNotFoundError(f"Audio file not found: {filepath}")
        return p.read_bytes()

    def get_wav_duration(self, filepath: str | Path) -> float:
        """Calculates audio duration in seconds using standard Python wave library."""
        try:
            with wave.open(str(filepath), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return round(frames / float(rate), 2)
        except Exception:
            pass
        return 0.0
