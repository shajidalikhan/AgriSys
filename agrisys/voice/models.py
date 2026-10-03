"""Pydantic data models and schemas for Multilingual Voice Pipeline."""

from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class TranscriptionResult(BaseModel):
    """Result of Automatic Speech Recognition (ASR)."""
    raw_transcript: str = Field(..., description="Original raw transcript from ASR engine")
    normalized_transcript: str = Field(..., description="Cleaned, unicode-standardized transcript")
    detected_language: str = Field(default="hi", description="ISO 639-1 language code (e.g. 'hi', 'en', 'pa')")
    confidence: float = Field(default=0.90, ge=0.0, le=1.0, description="Speech recognition confidence score")
    duration_seconds: float = Field(default=0.0, ge=0.0, description="Audio duration in seconds")
    audio_format: str = Field(default="wav", description="Audio format container (wav, mp3, webm, ogg)")


class SynthesisResult(BaseModel):
    """Result of Text-to-Speech (TTS) synthesis."""
    audio_path: str = Field(..., description="Local file system path or S3 key to synthesized audio")
    audio_url: str = Field(..., description="Reachable HTTP/WebSocket URL to stream or play audio")
    language: str = Field(..., description="Language code of synthesized speech")
    duration_seconds: float = Field(default=0.0, ge=0.0, description="Synthesized audio duration in seconds")
    audio_format: str = Field(default="wav", description="Audio container format (wav, mp3)")
    sampling_rate: int = Field(default=24000, description="Sampling rate in Hz (e.g. 16000, 24000)")


class AudioMetadata(BaseModel):
    """Metadata for uploaded or synthesized speech recording."""
    filename: str
    size_bytes: int
    duration_seconds: float
    channels: int = 1
    sample_width: int = 2
    frame_rate: int = 16000
