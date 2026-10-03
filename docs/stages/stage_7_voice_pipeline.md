# Stage 7: Multilingual Voice Pipeline (Whisper & Indic TTS)

## 1. Overview & Objectives
Stage 7 implements the **Multilingual Voice Pipeline (§11)** in AgriSys. A high percentage of Indian smallholder farmers face literacy and typing barriers in complex technical agronomy interfaces. Providing voice-first interactions in vernacular dialects (Hindi, Marathi, Telugu, Tamil, Punjabi, Bengali, Kannada, Malayalam, and English) empowers farmers to speak questions naturally into mobile or web clients and listen to actionable spoken advisories.

### Key Objectives:
1. **Vernacular ASR Provider Abstraction (§11.1)**:
   - Pluggable speech recognition interface (`BaseASRProvider`).
   - `WhisperASRProvider`: Connects to OpenAI Whisper API with graceful fallbacks.
   - `BhashiniASRProvider`: Integrates with India's National Language Translation Mission (NLTM / ULCA) Bhashini pipeline.
   - `MockASRProvider`: Deterministic offline provider for test suites and offline operation.
2. **Fine-Tuning Script for Agricultural Vernacular Speech (§11.1)**:
   - Created `scripts/training/finetune_whisper.py` implementing HuggingFace Transformers `Seq2SeqTrainer` with LoRA (Low-Rank Adaptation, $r=16, \alpha=32$) targeting agricultural entity terms, fertilizer names, and regional dialects.
3. **Indic Script Normalization & Language Identification (§11.2)**:
   - `IndicTextNormalizer`: Performs Unicode NFC canonicalization, removes zero-width characters (ZWNJ/ZWJ), converts Devanagari numerals to Western digits, normalizes danda (`।`), and standardizes agricultural abbreviations (`किग्रा` $\to$ `किलोग्राम`, `हैक्टर`/`हेक्टर` $\to$ `हेक्टेयर`).
   - `IndicLanguageDetector`: Script range analyzer identifying Hindi, Marathi, Punjabi, Bengali, Tamil, Telugu, Gujarati, Kannada, Malayalam, and English. Employs distinctive morphological rules to differentiate Marathi from Hindi within Devanagari.
4. **Natural Indic Speech Synthesis (TTS) (§11.3)**:
   - Pluggable speech synthesis interface (`BaseTTSProvider`).
   - `OpenAITTSProvider`: High-fidelity neural voice synthesis.
   - `BhashiniTTSProvider`: Government of India vernacular text-to-speech engine.
   - `MockTTSProvider`: Generates genuine 16kHz mono 16-bit PCM WAV audio via standard library math/wave without external heavy binary dependencies.
5. **Audio Persistence & Web Playback (§11.4)**:
   - `AudioStorageManager`: Persists voice recordings to `data/artifacts/audio/` with unique UUID hashes and provides web-accessible URLs (`/static/audio/*`).
6. **LangGraph Pipeline Integration & Endpoints**:
   - `voice_processor_node`: Pre-router node transcribing incoming voice recordings into query text and identifying language before intent classification.
   - `tts_generator_node`: Post-guard node synthesizing merged advisory responses into spoken audio for voice queries or explicit audio requests.
   - REST Endpoints:
     - `POST /api/voice/transcribe` (multipart audio upload)
     - `POST /api/voice/synthesize` (text to speech)
     - Mounted static directory: `/static/audio`

---

## 2. SOLID Architecture Compliance

| Principle | Implementation in Stage 7 |
| :--- | :--- |
| **Single Responsibility (SRP)** | `AudioStorageManager` only handles file I/O. `IndicTextNormalizer` only handles string and script cleanup. `WhisperASRProvider` only handles audio-to-text. `OpenAITTSProvider` only handles text-to-audio. `VoicePipeline` orchestrates the complete flow. |
| **Open/Closed (OCP)** | New ASR/TTS engines (e.g., Google Cloud Speech, Azure Speech, Coqui TTS) can be plugged in by subclassing `BaseASRProvider` or `BaseTTSProvider` without changing orchestrator nodes. |
| **Liskov Substitution (LSP)** | `WhisperASRProvider`, `BhashiniASRProvider`, and `MockASRProvider` conform strictly to `BaseASRProvider` returning `TranscriptionResult`. |
| **Interface Segregation (ISP)** | Transcription (`TranscriptionResult`), speech synthesis (`SynthesisResult`), and storage metadata (`AudioMetadata`) have clean, isolated schemas. |
| **Dependency Inversion (DIP)** | LangGraph nodes and FastAPI endpoints interact with the `VoicePipeline` coordinator and abstract provider interfaces rather than vendor-specific SDKs. |

---

## 3. End-to-End Voice Flow Architecture

```
                  Farmer Speaks in Native Dialect (Mic)
                                   │
                                   ▼
          ┌─────────────────────────────────────────────────┐
          │     AudioStorageManager (Save raw .wav)         │
          └─────────────────────────────────────────────────┘
                                   │
                                   ▼
          ┌─────────────────────────────────────────────────┐
          │     ASR Engine (Whisper / Bhashini / Mock)      │
          └─────────────────────────────────────────────────┘
                                   │
                                   ▼
          ┌─────────────────────────────────────────────────┐
          │   IndicTextNormalizer & LanguageDetector        │
          │   (Unicode NFC, ZWNJ removal, Unit expansion)   │
          └─────────────────────────────────────────────────┘
                                   │
                                   ▼
          ═══════════════════════════════════════════════════
          AgriSys LangGraph StateGraph Multi-Agent Pipeline
          (Intent Router ──> Specialist Agents ──> Merger)
          ═══════════════════════════════════════════════════
                                   │
                                   ▼
          ┌─────────────────────────────────────────────────┐
          │  Hallucination Guard (Factual Verification)     │
          └─────────────────────────────────────────────────┘
                                   │
                                   ▼
          ┌─────────────────────────────────────────────────┐
          │       TTS Generator Node (Indic Voice)          │
          │       (OpenAI / Bhashini / Waveform Synth)      │
          └─────────────────────────────────────────────────┘
                                   │
                                   ▼
             Spoken Advisory Played on Farmer's Device (.wav)
```

---

## 4. Verification & Test Coverage

All 11 unit and integration tests passed in `tests/test_voice_pipeline.py`:

```
tests/test_voice_pipeline.py::test_indic_normalizer PASSED               [  9%]
tests/test_voice_pipeline.py::test_indic_language_detector PASSED        [ 18%]
tests/test_voice_pipeline.py::test_audio_storage_manager PASSED          [ 27%]
tests/test_voice_pipeline.py::test_mock_tts_provider PASSED              [ 36%]
tests/test_voice_pipeline.py::test_mock_asr_provider PASSED              [ 45%]
tests/test_voice_pipeline.py::test_voice_pipeline_flow PASSED            [ 54%]
tests/test_voice_pipeline.py::test_voice_processor_node PASSED           [ 63%]
tests/test_voice_pipeline.py::test_tts_generator_node PASSED             [ 72%]
tests/test_voice_pipeline.py::test_api_voice_transcribe PASSED           [ 81%]
tests/test_voice_pipeline.py::test_api_voice_synthesize PASSED           [ 90%]
tests/test_voice_pipeline.py::test_api_orchestrate_with_voice PASSED     [100%]
```

Full repository test suite across Stages 1–7: **112 passed in 60.59s**.
