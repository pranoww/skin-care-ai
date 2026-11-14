/**
 * API client for the Skin Care AI FastAPI backend.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const MAX_MESSAGE_CHARS = 2000;

async function readErrorMessage(response, fallback) {
  try {
    const data = await response.json();
    if (Array.isArray(data?.detail)) {
      // Pydantic validation errors
      return data.detail.map((e) => e.msg || e.message).join(', ');
    }
    if (typeof data?.detail === 'string') return data.detail;
  } catch {
    // body was not JSON
  }
  return `${fallback} (status ${response.status})`;
}

async function request(path, init, fallbackError) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init);
  } catch {
    throw new Error(`Can't reach the analysis server. Check that the backend is running at ${API_BASE_URL}.`);
  }
  if (!response.ok) {
    throw new Error(await readErrorMessage(response, fallbackError));
  }
  return response.json();
}

/**
 * Send a typed skin concern for analysis.
 * @param {string} message
 * @returns {Promise<Object>} ChatResponse
 */
export async function analyzeSkinConcern(message) {
  const trimmed = message ? message.trim() : '';
  if (!trimmed) {
    throw new Error('Please describe your skin concern first.');
  }
  return request(
    '/api/v1/chat',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: trimmed }),
    },
    'The analysis failed',
  );
}

/**
 * Send a voice recording. When the browser produced its own transcript it is
 * sent too, so the backend can skip a paid transcription call.
 * @returns {Promise<{transcription: string, transcription_source: 'client'|'server', analysis: Object, spoken_summary: string, audio?: string, audio_error?: string}>}
 */
export async function sendVoiceMessage(audioBlob, filename = 'recording.webm', transcriptHint = '') {
  if (!audioBlob || audioBlob.size === 0) {
    throw new Error('No audio was recorded. Please try recording again.');
  }
  const formData = new FormData();
  formData.append('audio', audioBlob, filename);
  if (transcriptHint && transcriptHint.trim()) {
    formData.append('transcript_hint', transcriptHint.trim());
  }
  return request('/api/v1/voice/chat', { method: 'POST', body: formData }, 'The voice analysis failed');
}
