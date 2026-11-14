"""Text-to-Speech service layer.

LangChain has no provider-neutral speech-synthesis interface, so TTS stays behind
``BaseTTSService``. The default implementation calls a Gemini TTS model through
LangChain's Gemini chat model; another provider means another subclass.
"""

import base64
import io
import logging
import wave
from abc import ABC, abstractmethod
from typing import Any, Optional

from langchain_core.language_models import BaseChatModel

from app.core.config import Settings, get_settings
from app.core.exceptions import AIProviderError
from app.schemas.chat import ChatResponse
from app.services.llm import build_chat_model, map_llm_error

logger = logging.getLogger(__name__)

# Gemini TTS returns 16-bit mono PCM at 24 kHz with no container.
PCM_SAMPLE_RATE = 24000
PCM_SAMPLE_WIDTH_BYTES = 2
PCM_CHANNELS = 1


def build_spoken_summary(analysis: ChatResponse) -> str:
    """Transform structured analysis into a natural conversational spoken summary.

    Avoids reading technical details, confidence scores, or raw JSON.
    """
    parts = []

    if analysis.summary and analysis.summary.strip():
        parts.append(analysis.summary.strip())
    elif analysis.skin_concern:
        parts.append(f"Regarding your skin concern, {analysis.skin_concern}.")

    if analysis.possible_factors:
        factors = [f.strip() for f in analysis.possible_factors if f.strip()][:3]
        if len(factors) == 1:
            parts.append(f"A possible contributing factor could be {factors[0]}.")
        elif factors:
            parts.append(f"Possible factors include {', '.join(factors[:-1])}, or {factors[-1]}.")

    if analysis.recommendations:
        recs = [r.strip().rstrip(".") for r in analysis.recommendations if r.strip()][:2]
        if recs:
            parts.append(f"For general care: {'. '.join(recs)}.")

    if analysis.professional_advice:
        parts.append("Because symptoms may vary, consulting a board-certified dermatologist is advised.")

    return " ".join(parts).strip()


def ensure_wav(audio_bytes: bytes, sample_rate: int = PCM_SAMPLE_RATE) -> bytes:
    """Return playable WAV bytes, wrapping raw PCM in a WAV container if needed.

    Browsers cannot play headerless PCM, even when labelled audio/wav.
    """
    if audio_bytes.startswith(b"RIFF"):
        return audio_bytes
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(PCM_CHANNELS)
        wav_file.setsampwidth(PCM_SAMPLE_WIDTH_BYTES)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_bytes)
    return buffer.getvalue()


def audio_bytes_to_data_uri(audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
    """Encode raw audio bytes into a base64 Data URI."""
    encoded = base64.b64encode(audio_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


class BaseTTSService(ABC):
    """Abstract base class for Text-to-Speech providers."""

    @abstractmethod
    async def synthesize_speech(self, text: str) -> bytes:
        """Synthesize natural speech from text, returning WAV audio bytes."""


def _extract_audio(response: Any) -> Optional[bytes]:
    """Find audio bytes in a LangChain chat response (legacy and v1 content shapes)."""
    audio = getattr(response, "additional_kwargs", {}).get("audio")
    if isinstance(audio, (bytes, bytearray)) and audio:
        return bytes(audio)
    content = getattr(response, "content", None)
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "audio" and block.get("base64"):
                return base64.b64decode(block["base64"])
    return None


class GeminiTTSService(BaseTTSService):
    """Gemini TTS through LangChain's Gemini chat model."""

    def __init__(self, settings: Optional[Settings] = None, model: Optional[BaseChatModel] = None) -> None:
        self.settings = settings or get_settings()
        self._model = model

    def _get_model(self) -> BaseChatModel:
        if self._model is None:
            self._model = build_chat_model(self.settings, self.settings.LLM_TTS_MODEL)
        return self._model

    def _generation_config(self) -> dict:
        return {
            "response_modalities": ["AUDIO"],
            "speech_config": {
                "voice_config": {
                    "prebuilt_voice_config": {"voice_name": self.settings.LLM_TTS_VOICE or "Kore"}
                }
            },
        }

    async def synthesize_speech(self, text: str) -> bytes:
        cleaned = text.strip()
        if not cleaned:
            raise AIProviderError("Cannot synthesize speech from empty text.")

        try:
            response = await self._get_model().ainvoke(cleaned, generation_config=self._generation_config())
        except Exception as exc:
            raise map_llm_error(exc, self.settings, "Text-to-Speech") from exc

        audio = _extract_audio(response)
        if not audio:
            raise AIProviderError("Text-to-Speech returned no audio.")
        return ensure_wav(audio)




class UnavailableTTSService(BaseTTSService):
    """Used when the configured provider has no TTS implementation here.

    The voice route reports this as ``audio_error`` and the frontend falls back
    to the browser's built-in speech synthesis.
    """

    def __init__(self, provider: str) -> None:
        self.provider = provider

    async def synthesize_speech(self, text: str) -> bytes:
        raise AIProviderError(f"Server voice playback isn't available with the '{self.provider}' provider.")


def build_tts_service(settings: Optional[Settings] = None) -> BaseTTSService:
    """Pick the speech-synthesis implementation for the configured provider."""
    settings = settings or get_settings()
    if settings.LLM_PROVIDER == "google_genai":
        return GeminiTTSService(settings)
    return UnavailableTTSService(settings.LLM_PROVIDER)
