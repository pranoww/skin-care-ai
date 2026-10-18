"""Speech-to-Text service layer using Google Gemini."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AIAudioValidationError,
    AIConfigurationError,
    AIProviderError,
    AIRateLimitError,
    AIServiceUnavailableError,
    AITimeoutError,
)

logger = logging.getLogger(__name__)


class BaseSpeechService(ABC):
    """Abstract base class for Speech-to-Text providers."""

    @abstractmethod
    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        filename: Optional[str] = None,
        transcript_hint: Optional[str] = None,
    ) -> str:
        """Transcribe audio bytes to text."""
        pass


def detect_audio_mime_type(audio_bytes: bytes, filename: Optional[str] = None) -> str:
    """Infer the MIME type of the given audio file or bytes."""
    if filename:
        lower_name = filename.lower()
        if lower_name.endswith(".wav"):
            return "audio/wav"
        if lower_name.endswith(".mp3"):
            return "audio/mp3"
        if lower_name.endswith(".ogg") or lower_name.endswith(".oga"):
            return "audio/ogg"
        if lower_name.endswith(".mp4") or lower_name.endswith(".m4a") or lower_name.endswith(".aac"):
            return "audio/mp4"
        if lower_name.endswith(".webm"):
            return "audio/webm"

    # Inspect magic bytes
    if audio_bytes.startswith(b"RIFF"):
        return "audio/wav"
    if audio_bytes.startswith(b"\x1aE\xdf\xa3"):
        return "audio/webm"
    if audio_bytes.startswith(b"OggS"):
        return "audio/ogg"
    if audio_bytes.startswith(b"ID3") or audio_bytes.startswith(b"\xff\xfb") or audio_bytes.startswith(b"\xff\xf3"):
        return "audio/mp3"

    # Default to webm as captured by browser MediaRecorder
    return "audio/webm"


class GeminiSpeechService(BaseSpeechService):
    """Google Gemini implementation for speech transcription."""

    def __init__(self, settings: Optional[Settings] = None, client: Optional[genai.Client] = None) -> None:
        self.settings = settings or get_settings()
        self._client: Optional[genai.Client] = client

    def _get_client(self) -> genai.Client:
        """Get or initialize the Google GenAI client."""
        if self._client is not None:
            return self._client

        api_key = self.settings.GEMINI_API_KEY
        if not api_key or not api_key.strip():
            raise AIConfigurationError(
                "GEMINI_API_KEY is not configured. Please set GEMINI_API_KEY in your .env file."
            )

        try:
            self._client = genai.Client(api_key=api_key.strip())
            return self._client
        except Exception as e:
            logger.error("Failed to initialize Gemini client for STT: %s", str(e))
            raise AIConfigurationError("Failed to initialize Gemini client for Speech-to-Text.")

    def _sanitize_message(self, message: str) -> str:
        """Sanitize error messages to ensure API keys are never leaked."""
        api_key = self.settings.GEMINI_API_KEY
        if api_key and api_key in message:
            return message.replace(api_key, "[REDACTED]")
        return message

    def _call_gemini_stt(self, audio_bytes: bytes, mime_type: str) -> str:
        """Synchronously execute audio transcription via Gemini with retry for demand spikes."""
        client = self._get_client()
        model = self.settings.GEMINI_STT_MODEL

        prompt = (
            "Generate a verbatim transcription of this audio. "
            "Return ONLY the transcribed text, with no extra commentary, explanations, or quotes."
        )

        response = None
        max_retries = 3

        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=[
                        types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                        prompt,
                    ],
                )
                break
            except APIError as api_err:
                raw_msg = self._sanitize_message(str(getattr(api_err, "message", None) or api_err))
                status_code = getattr(api_err, "code", None)

                is_demand_spike = (
                    status_code == 503
                    or "HIGH DEMAND" in raw_msg.upper()
                    or "UNAVAILABLE" in raw_msg.upper()
                )

                if is_demand_spike and attempt < max_retries - 1:
                    logger.warning(
                        "Gemini STT temporary demand spike (attempt %d/%d). Retrying...",
                        attempt + 1,
                        max_retries,
                    )
                    import time
                    time.sleep(1.5 * (attempt + 1))
                    continue

                logger.error("Gemini STT APIError (%s): %s", status_code, raw_msg)

                if status_code == 429 or "RESOURCE_EXHAUSTED" in raw_msg.upper() or "QUOTA" in raw_msg.upper():
                    raise AIRateLimitError("Gemini Speech-to-Text rate limit or quota exceeded. Please try again later.")
                if is_demand_spike:
                    raise AIServiceUnavailableError("Gemini Speech-to-Text service is temporarily unavailable. Please try again.")
                if status_code in (504, 408) or "DEADLINE_EXCEEDED" in raw_msg.upper() or "TIMEOUT" in raw_msg.upper():
                    raise AITimeoutError("Gemini Speech-to-Text request timed out. Please try again.")
                if status_code == 400 or "INVALID_ARGUMENT" in raw_msg.upper():
                    raise AIAudioValidationError("Audio data is in an unsupported or corrupted format.")

                raise AIProviderError(f"Gemini Speech-to-Text provider error: {raw_msg}")
            except TimeoutError:
                logger.error("Timeout occurred during Gemini STT request")
                raise AITimeoutError("Gemini Speech-to-Text request timed out. Please try again.")
            except (AIAudioValidationError, AIConfigurationError, AIRateLimitError, AIServiceUnavailableError, AITimeoutError, AIProviderError):
                raise
            except Exception as exc:
                raw_msg = self._sanitize_message(str(exc))
                logger.error("Unexpected error during Gemini STT transcription: %s", raw_msg)
                raise AIProviderError("Failed to transcribe audio with Gemini.")

        raw_text = getattr(response, "text", "") or ""
        cleaned = raw_text.strip()
        if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
            cleaned = cleaned[1:-1].strip()

        if not cleaned:
            raise AIAudioValidationError("No understandable speech detected in the audio. Please speak clearly and try again.")

        return cleaned

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        filename: Optional[str] = None,
        transcript_hint: Optional[str] = None,
    ) -> str:
        """Validate audio payload and transcribe asynchronously without blocking event loop."""
        if not audio_bytes or len(audio_bytes.strip()) == 0:
            raise AIAudioValidationError("Audio payload is empty. Please record audio before submitting.")

        if len(audio_bytes) > self.settings.MAX_AUDIO_SIZE_BYTES:
            max_mb = self.settings.MAX_AUDIO_SIZE_BYTES // (1024 * 1024)
            raise AIAudioValidationError(f"Audio payload exceeds maximum allowed size of {max_mb}MB.")

        mime_type = detect_audio_mime_type(audio_bytes, filename)
        return await asyncio.to_thread(self._call_gemini_stt, audio_bytes, mime_type)


# Default export alias
SpeechService = GeminiSpeechService
