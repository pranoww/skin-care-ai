/**
 * API client module for communicating with the FastAPI Skin Care AI backend.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Sends a natural language skin concern description to the backend for analysis.
 * 
 * @param {string} message - User's skin concern description
 * @returns {Promise<Object>} Structured skin concern analysis response
 */
export async function analyzeSkinConcern(message) {
  const trimmed = message ? message.trim() : '';
  if (!trimmed) {
    throw new Error('Please enter a description of your skin concern.');
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message: trimmed }),
    });

    if (!response.ok) {
      let errorMessage = 'An error occurred while analyzing your concern.';
      try {
        const errorData = await response.json();
        if (errorData && errorData.detail) {
          if (Array.isArray(errorData.detail)) {
            // Pydantic validation error list
            errorMessage = errorData.detail.map(e => e.msg || e.message).join(', ');
          } else if (typeof errorData.detail === 'string') {
            errorMessage = errorData.detail;
          }
        }
      } catch {
        errorMessage = `Service returned status ${response.status} (${response.statusText})`;
      }
      throw new Error(errorMessage);
    }

    const data = await response.json();
    return data;
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error('Unable to connect to the AI analysis server. Please ensure the backend is running at ' + API_BASE_URL);
    }
    throw err;
  }
}

/**
 * Checks backend health status.
 * 
 * @returns {Promise<boolean>} True if backend is healthy
 */
export async function checkBackendHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      cache: 'no-store',
    });
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Sends recorded audio to the voice analysis endpoint.
 * 
 * @param {Blob} audioBlob - Recorded audio blob from MediaRecorder
 * @param {string} [filename='recording.webm'] - Audio filename
 * @returns {Promise<{transcription: string, analysis: Object, spoken_summary: string, audio?: string}>}
 */
export async function sendVoiceMessage(audioBlob, filename = 'recording.webm', transcriptHint = '') {
  if (!audioBlob || audioBlob.size === 0) {
    throw new Error('No audio was recorded. Please record your concern and try again.');
  }

  const formData = new FormData();
  formData.append('audio', audioBlob, filename);
  if (transcriptHint && transcriptHint.trim()) {
    formData.append('transcript_hint', transcriptHint.trim());
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/voice/chat`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let errorMessage = 'An error occurred while analyzing your voice recording.';
      try {
        const errorData = await response.json();
        if (errorData && errorData.detail) {
          if (Array.isArray(errorData.detail)) {
            errorMessage = errorData.detail.map(e => e.msg || e.message).join(', ');
          } else if (typeof errorData.detail === 'string') {
            errorMessage = errorData.detail;
          }
        }
      } catch {
        errorMessage = `Service returned status ${response.status} (${response.statusText})`;
      }
      throw new Error(errorMessage);
    }

    const data = await response.json();
    return data;
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error('Unable to connect to the AI analysis server. Please ensure the backend is running at ' + API_BASE_URL);
    }
    throw err;
  }
}
