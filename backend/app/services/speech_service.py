"""Speech-to-Text service layer, provider-neutral via LangChain multimodal input."""

import base64
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableLambda

from app.core.config import Settings, get_settings
from app.core.exceptions import AIAudioValidationError, AIConfigurationError
from app.services.llm import (
    build_chat_model,
    invoke_with_overload_handling,
    message_text,
    sdk_max_retries,
)

logger = logging.getLogger(__name__)

TRANSCRIPTION_PROMPT = (
    "Generate a verbatim transcription of this audio. "
    "Return ONLY the transcribed text, with no extra commentary, explanations, or quotes."
)


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


def detect_audio_mime_type(audio_bytes: bytes, filename: Optional[str] = None) -> str:
    """Infer the MIME type of the given audio file or bytes."""
    if filename:
        lower_name = filename.lower()
        if lower_name.endswith(".wav"):
            return "audio/wav"
        if lower_name.endswith(".mp3"):
            return "audio/mp3"
        if lower_name.endswith((".ogg", ".oga")):
            return "audio/ogg"
        if lower_name.endswith((".mp4", ".m4a", ".aac")):
            return "audio/mp4"
        if lower_name.endswith(".webm"):
            return "audio/webm"

    if audio_bytes.startswith(b"RIFF"):
        return "audio/wav"
    if audio_bytes.startswith(b"\x1aE\xdf\xa3"):
        return "audio/webm"
    if audio_bytes.startswith(b"OggS"):
        return "audio/ogg"
    if audio_bytes.startswith((b"ID3", b"\xff\xfb", b"\xff\xf3")):
        return "audio/mp3"

    # Default to webm as captured by browser MediaRecorder
    return "audio/webm"


class LangChainSpeechService(BaseSpeechService):
    """Transcribes audio by sending it to a multimodal chat model."""

    def __init__(self, settings: Optional[Settings] = None, model: Optional[BaseChatModel] = None) -> None:
        self.settings = settings or get_settings()
        self._model = model

    def _get_model(self) -> BaseChatModel:
        if self._model is None:
            self._model = build_chat_model(self.settings, self.settings.LLM_STT_MODEL, temperature=0)
        return self._model

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        filename: Optional[str] = None,
        transcript_hint: Optional[str] = None,
    ) -> str:
        """Validate the audio payload and transcribe it."""
        if not audio_bytes:
            raise AIAudioValidationError("Audio payload is empty. Please record audio before submitting.")
        if len(audio_bytes) > self.settings.MAX_AUDIO_SIZE_BYTES:
            max_mb = self.settings.MAX_AUDIO_SIZE_BYTES // (1024 * 1024)
            raise AIAudioValidationError(f"Audio payload exceeds maximum allowed size of {max_mb}MB.")

        mime_type = detect_audio_mime_type(audio_bytes, filename)
        message = HumanMessage(
            content=[
                {"type": "text", "text": TRANSCRIPTION_PROMPT},
                {
                    "type": "audio",
                    "base64": base64.b64encode(audio_bytes).decode("ascii"),
                    "mime_type": mime_type,
                },
            ]
        )

        response = await invoke_with_overload_handling(
            [self._get_model()],
            [message],
            self.settings,
            "Speech-to-Text",
            invalid_request_error=AIAudioValidationError,
        )

        cleaned = message_text(response).strip()
        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in "\"'":
            cleaned = cleaned[1:-1].strip()
        if not cleaned:
            raise AIAudioValidationError(
                "No understandable speech detected in the audio. Please speak clearly and try again."
            )
        return cleaned




class GroqWhisperSpeechService(BaseSpeechService):
    """Transcribes audio with Groq's hosted Whisper models.

    Groq chat models do not accept audio, so speech-to-text uses Groq's
    dedicated transcription endpoint instead of a LangChain chat model.
    """

    def __init__(self, settings: Optional[Settings] = None, client: Optional[Any] = None) -> None:
        self.settings = settings or get_settings()
        self._client = client

    def _get_client(self) -> Any:
        if self._client is None:
            if not self.settings.LLM_API_KEY:
                raise AIConfigurationError("No Groq API key configured. Set GROQ_API_KEY in your .env file.")
            from groq import AsyncGroq

            self._client = AsyncGroq(
                api_key=self.settings.LLM_API_KEY,
                max_retries=sdk_max_retries(self.settings),
                timeout=self.settings.LLM_TIMEOUT_SECONDS,
            )
        return self._client

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        filename: Optional[str] = None,
        transcript_hint: Optional[str] = None,
    ) -> str:
        if not audio_bytes:
            raise AIAudioValidationError("Audio payload is empty. Please record audio before submitting.")
        if len(audio_bytes) > self.settings.MAX_AUDIO_SIZE_BYTES:
            max_mb = self.settings.MAX_AUDIO_SIZE_BYTES // (1024 * 1024)
            raise AIAudioValidationError(f"Audio payload exceeds maximum allowed size of {max_mb}MB.")

        client = self._get_client()
        mime_type = detect_audio_mime_type(audio_bytes, filename)
        upload_name = filename or f"recording.{mime_type.split('/')[-1]}"

        async def _transcribe(_payload: Any) -> Any:
            return await client.audio.transcriptions.create(
                file=(upload_name, audio_bytes),
                model=self.settings.LLM_STT_MODEL,
                response_format="json",
                temperature=0,
            )

        result = await invoke_with_overload_handling(
            [RunnableLambda(_transcribe)],
            None,
            self.settings,
            "Speech-to-Text",
            invalid_request_error=AIAudioValidationError,
        )
        text = (getattr(result, "text", None) or "").strip()
        if not text:
            raise AIAudioValidationError(
                "No understandable speech detected in the audio. Please speak clearly and try again."
            )
        return text


def build_speech_service(settings: Optional[Settings] = None) -> BaseSpeechService:
    """Pick the transcription implementation for the configured provider."""
    settings = settings or get_settings()
    if settings.LLM_PROVIDER == "groq":
        return GroqWhisperSpeechService(settings)
    return LangChainSpeechService(settings)
