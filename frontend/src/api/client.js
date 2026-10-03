/**
 * AgriSys API Client connecting to FastAPI backend
 */

const API_BASE = 'http://localhost:8000';

export async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    return await res.json();
  } catch (err) {
    console.warn("Backend not reached:", err);
    return null;
  }
}

export async function orchestrateQuery({ query, sensorData, language = 'en', generateTts = false }) {
  const res = await fetch(`${API_BASE}/api/orchestrate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      sensor_data: sensorData || null,
      language,
      generate_tts: generateTts,
    }),
  });
  if (!res.ok) throw new Error(`Orchestration failed: ${res.statusText}`);
  return await res.json();
}

export async function diagnoseDisease(file, language = 'en') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('language', language);

  const res = await fetch(`${API_BASE}/api/disease/diagnose`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(`Disease diagnosis failed: ${res.statusText}`);
  return await res.json();
}

export async function diagnoseNutrition({ crop = 'Tomato', sensorData, language = 'en' }) {
  const res = await fetch(`${API_BASE}/api/nutrition/diagnose`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      crop,
      sensor_data: sensorData,
      language,
    }),
  });
  if (!res.ok) throw new Error(`Nutrition diagnosis failed: ${res.statusText}`);
  return await res.json();
}

export async function fetchMarketAdvisory({ commodity = 'Tomato', latitude = 26.8467, longitude = 80.9462, locationName = 'Lucknow, UP', language = 'en' }) {
  const res = await fetch(`${API_BASE}/api/market/advisory`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      commodity,
      latitude,
      longitude,
      location_name: locationName,
      language,
    }),
  });
  if (!res.ok) throw new Error(`Market advisory failed: ${res.statusText}`);
  return await res.json();
}

export async function fetchWeatherForecast({ crop = 'Wheat', cropStage = 'Mid', latitude = 26.8467, longitude = 80.9462, locationName = 'Lucknow, UP', language = 'en' }) {
  const res = await fetch(`${API_BASE}/api/weather/forecast`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      crop,
      crop_stage: cropStage,
      latitude,
      longitude,
      location_name: locationName,
      language,
    }),
  });
  if (!res.ok) throw new Error(`Weather advisory failed: ${res.statusText}`);
  return await res.json();
}

export async function transcribeAudio(audioBlob, language = 'hi') {
  const formData = new FormData();
  formData.append('file', audioBlob, 'mic_recording.wav');
  formData.append('language', language);

  const res = await fetch(`${API_BASE}/api/voice/transcribe`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error(`Voice transcription failed: ${res.statusText}`);
  return await res.json();
}

export async function synthesizeSpeech({ text, language = 'hi', speed = 1.0 }) {
  const res = await fetch(`${API_BASE}/api/voice/synthesize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, language, speed }),
  });
  if (!res.ok) throw new Error(`Speech synthesis failed: ${res.statusText}`);
  return await res.json();
}
