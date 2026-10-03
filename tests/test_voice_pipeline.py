"""Unit and integration tests for AgriSys Multilingual Voice Pipeline (Stage 7)."""

import io
import wave
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from agrisys.voice.models import TranscriptionResult, SynthesisResult, AudioMetadata
from agrisys.voice.normalizer import IndicTextNormalizer, IndicLanguageDetector
from agrisys.voice.storage import AudioStorageManager
from agrisys.voice.tts import MockTTSProvider, TTSProviderFactory
from agrisys.voice.asr import MockASRProvider, ASRProviderFactory
from agrisys.voice.pipeline import VoicePipeline
from agrisys.voice.node import voice_processor_node, tts_generator_node
from agrisys.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_wav_bytes() -> bytes:
    """Generates a minimal valid 16kHz mono 16-bit PCM WAV audio file in memory."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        # Write 0.1 seconds of silence (1600 samples)
        wf.writeframes(b"\x00\x00" * 1600)
    return buf.getvalue()


# ------------------------------------------------------------------
# 1. Normalizer & Language Detection Tests
# ------------------------------------------------------------------

def test_indic_normalizer():
    normalizer = IndicTextNormalizer()

    # Normalizes units and abbreviations
    text = "कृपया 50 किग्रा यूरिया प्रति हैक्टर डालें।"
    normalized = normalizer.normalize(text, language="hi")
    assert "किलोग्राम" in normalized
    assert "हेक्टेयर" in normalized
    assert "यूरिया" in normalized

    # Handles English text
    eng_text = "Apply 50 kg urea per ha."
    norm_eng = normalizer.normalize(eng_text, language="en")
    assert "50 kg urea" in norm_eng


def test_indic_language_detector():
    detector = IndicLanguageDetector()

    assert detector.detect_script("टमाटर के पत्ते पीले पड़ रहे हैं") == "hi"
    assert detector.detect_script("टोमॅटोच्या पानांवर पिवळे डाग पडले आहेत") == "mr"
    assert detector.detect_script("టమోటా ఆకులపై పసుపు మచ్చలు ఉన్నాయి") == "te"
    assert detector.detect_script("தக்காளி இலைகளில் மஞ்சள் புள்ளிகள் உள்ளன") == "ta"
    assert detector.detect_script("Yellow leaves on tomato plant") == "en"


# ------------------------------------------------------------------
# 2. Audio Storage Manager Tests
# ------------------------------------------------------------------

def test_audio_storage_manager(tmp_path, sample_wav_bytes):
    storage = AudioStorageManager(base_dir=tmp_path)

    file_path, public_url = storage.save_audio(sample_wav_bytes, extension="wav", prefix="test_mic")
    assert Path(file_path).exists()
    assert public_url.startswith("/static/audio/test_mic_")

    read_data = storage.read_audio(file_path)
    assert len(read_data) == len(sample_wav_bytes)

    duration = storage.get_wav_duration(file_path)
    assert duration == pytest.approx(0.1, abs=0.05)


# ------------------------------------------------------------------
# 3. Mock TTS and ASR Providers
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_tts_provider():
    provider = MockTTSProvider()
    audio_bytes, fmt = await provider.synthesize("टमाटर में नाइट्रोजन की कमी है।", language="hi")

    assert fmt == "wav"
    assert len(audio_bytes) > 44  # WAV header is 44 bytes
    assert audio_bytes[:4] == b"RIFF"
    assert audio_bytes[8:12] == b"WAVE"

    # Verify WAV header parameters
    with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000


@pytest.mark.asyncio
async def test_mock_asr_provider(sample_wav_bytes):
    provider = MockASRProvider()
    res = await provider.transcribe(sample_wav_bytes, language="hi")

    assert res.detected_language == "hi"
    assert len(res.normalized_transcript) > 0
    assert res.confidence >= 0.90


# ------------------------------------------------------------------
# 4. Master VoicePipeline Integration
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_voice_pipeline_flow(sample_wav_bytes):
    pipeline = VoicePipeline()

    # Audio In -> Transcribed & Normalized Text
    trans_res, saved_path = await pipeline.process_incoming_audio(
        audio_bytes=sample_wav_bytes,
        language="hi",
        filename="farmer_query.wav",
    )
    assert trans_res.detected_language == "hi"
    assert len(trans_res.normalized_transcript) > 0
    assert Path(saved_path).exists()

    # Text In -> Synthesized Speech Audio Out
    speech_res = await pipeline.generate_speech_response(
        text="यूरिया 45 किलोग्राम प्रति हेक्टेयर डालें।",
        language="hi",
    )
    assert Path(speech_res.audio_path).exists()
    assert speech_res.audio_url.startswith("/static/audio/")
    assert speech_res.audio_format == "wav"


# ------------------------------------------------------------------
# 5. LangGraph Voice State Nodes
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_voice_processor_node(sample_wav_bytes):
    # Case 1: Audio bytes provided
    state_in = {
        "audio_bytes": sample_wav_bytes,
        "language": "hi",
    }
    state_out = await voice_processor_node(state_in)
    assert "query" in state_out
    assert state_out["language"] == "hi"
    assert "voice_audio_path" in state_out

    # Case 2: No audio provided -> pass-through empty
    empty_out = await voice_processor_node({})
    assert empty_out == {}


@pytest.mark.asyncio
async def test_tts_generator_node(sample_wav_bytes):
    # Case 1: generate_tts requested
    state_in = {
        "merged_response": "टमाटर में यूरिया का छिड़काव करें।",
        "language": "hi",
        "generate_tts": True,
    }
    state_out = await tts_generator_node(state_in)
    assert "tts_audio_path" in state_out
    assert Path(state_out["tts_audio_path"]).exists()

    # Case 2: No audio requested and no voice input -> should skip
    state_skip = {
        "merged_response": "Some advisory text.",
        "language": "en",
        "generate_tts": False,
    }
    skip_out = await tts_generator_node(state_skip)
    assert skip_out == {}


# ------------------------------------------------------------------
# 6. FastAPI Voice Endpoints
# ------------------------------------------------------------------

def test_api_voice_transcribe(client, sample_wav_bytes):
    files = {
        "file": ("test_voice.wav", io.BytesIO(sample_wav_bytes), "audio/wav"),
    }
    data = {"language": "hi"}
    response = client.post("/api/voice/transcribe", files=files, data=data)
    assert response.status_code == 200
    res_json = response.json()
    assert "normalized_transcript" in res_json
    assert res_json["detected_language"] == "hi"
    assert "audio_path" in res_json


def test_api_voice_synthesize(client):
    payload = {
        "text": "यूरिया 50 किलोग्राम प्रति एकड़ डालें।",
        "language": "hi",
        "speed": 1.0,
    }
    response = client.post("/api/voice/synthesize", json=payload)
    assert response.status_code == 200
    res_json = response.json()
    assert "audio_path" in res_json
    assert res_json["audio_url"].startswith("/static/audio/")
    assert res_json["audio_format"] == "wav"


def test_api_orchestrate_with_voice(client):
    payload = {
        "query": "टमाटर में यूरिया कितना डालें?",
        "language": "hi",
        "generate_tts": True,
    }
    response = client.post("/api/orchestrate", json=payload)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["merged_response"] is not None
    assert res_json["tts_audio_path"] is not None
    assert Path(res_json["tts_audio_path"]).exists()
