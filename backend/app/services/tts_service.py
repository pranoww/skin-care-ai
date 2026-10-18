"""Text-to-Speech service layer using Google Gemini."""

import asyncio
import base64
import logging
from abc import ABC, abstractmethod
from typing import Optional

from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AIConfigurationError,
    AIProviderError,
    AIRateLimitError,
    AIServiceUnavailableError,
    AITimeoutError,
)
from app.schemas.chat import ChatResponse

logger = logging.getLogger(__name__)


def build_spoken_summary(analysis: ChatResponse) -> str:
    """Transform structured analysis into a natural conversational spoken summary.
    
    Avoids reading technical details, confidence scores, or raw JSON.
    """
    parts = []
    
    # 1. Main summary
    if analysis.summary and analysis.summary.strip():
        parts.append(analysis.summary.strip())
    elif analysis.skin_concern:
        parts.append(f"Regarding your skin concern, {analysis.skin_concern}.")

    # 2. Possible contributing factors (up to 3)
    if analysis.possible_factors:
        factors = [f.strip() for f in analysis.possible_factors if f.strip()][:3]
        if factors:
            if len(factors) == 1:
                parts.append(f"A possible contributing factor could be {factors[0]}.")
            else:
                parts.append(f"Possible factors include {', '.join(factors[:-1])}, or {factors[-1]}.")

    # 3. Recommendations (top 2 gentle tips)
    if analysis.recommendations:
        recs = [r.strip() for r in analysis.recommendations if r.strip()][:2]
        if recs:
            parts.append(f"For general care: {'. '.join(recs)}.")

    # 4. Professional medical disclaimer if required
    if analysis.professional_advice:
        parts.append("Because symptoms may vary, consulting a board-certified dermatologist is advised.")

    return " ".join(parts).strip()


class BaseTTSService(ABC):
    """Abstract base class for Text-to-Speech providers."""

    @abstractmethod
    async def synthesize_speech(self, text: str) -> bytes:
        """Synthesize natural speech from text, returning audio bytes."""
        pass


class GeminiTTSService(BaseTTSService):
    """Google Gemini implementation for Text-to-Speech synthesis."""

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
            logger.error("Failed to initialize Gemini client for TTS: %s", str(e))
            raise AIConfigurationError("Failed to initialize Gemini client for Text-to-Speech.")

    def _sanitize_message(self, message: str) -> str:
        """Sanitize error messages to avoid leaking keys."""
        api_key = self.settings.GEMINI_API_KEY
        if api_key and api_key in message:
            return message.replace(api_key, "[REDACTED]")
        return message

    def _call_gemini_tts(self, text: str) -> bytes:
        """Synchronously execute Gemini TTS inference."""
        client = self._get_client()
        model = self.settings.GEMINI_TTS_MODEL
        voice_name = self.settings.GEMINI_TTS_VOICE

        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name or "Kore"
                    )
                )
            ),
        )

        try:
            response = client.models.generate_content(
                model=model,
                contents=text,
                config=config,
            )
        except APIError as api_err:
            raw_msg = self._sanitize_message(str(getattr(api_err, "message", None) or api_err))
            status_code = getattr(api_err, "code", None)
            logger.error("Gemini TTS APIError (%s): %s", status_code, raw_msg)

            if status_code == 429 or "RESOURCE_EXHAUSTED" in raw_msg.upper() or "QUOTA" in raw_msg.upper():
                raise AIRateLimitError("Gemini TTS rate limit or quota exceeded. Please try again later.")
            if status_code == 503 or "HIGH DEMAND" in raw_msg.upper() or "UNAVAILABLE" in raw_msg.upper():
                raise AIServiceUnavailableError("Gemini TTS service is temporarily unavailable. Please try again.")
            if status_code in (504, 408) or "DEADLINE_EXCEEDED" in raw_msg.upper() or "TIMEOUT" in raw_msg.upper():
                raise AITimeoutError("Gemini TTS request timed out. Please try again.")

            raise AIProviderError(f"Gemini TTS provider error: {raw_msg}")
        except TimeoutError:
            logger.error("Timeout occurred during Gemini TTS request")
            raise AITimeoutError("Gemini TTS request timed out. Please try again.")
        except (AIConfigurationError, AIRateLimitError, AIServiceUnavailableError, AITimeoutError, AIProviderError):
            raise
        except Exception as exc:
            raw_msg = self._sanitize_message(str(exc))
            logger.error("Unexpected error during Gemini TTS synthesis: %s", raw_msg)
            raise AIProviderError("Failed to synthesize speech with Gemini TTS.")

        audio_bytes = None
        if (
            hasattr(response, "candidates")
            and response.candidates
            and response.candidates[0].content
            and response.candidates[0].content.parts
        ):
            for part in response.candidates[0].content.parts:
                inline_data = getattr(part, "inline_data", None)
                if inline_data and getattr(inline_data, "data", None):
                    audio_bytes = inline_data.data
                    break

        if not audio_bytes or len(audio_bytes) == 0:
            raise AIProviderError("Gemini TTS returned empty audio bytes.")

        return audio_bytes

    async def synthesize_speech(self, text: str) -> bytes:
        """Synthesize speech asynchronously from text without blocking the event loop."""
        cleaned = text.strip()
        if not cleaned:
            raise AIProviderError("Cannot synthesize speech from empty text.")

        return await asyncio.to_thread(self._call_gemini_tts, cleaned)


def audio_bytes_to_data_uri(audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
    """Encode raw audio bytes into a base64 Data URI."""
    encoded = base64.b64encode(audio_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


# Default export alias
TTSService = GeminiTTSService
