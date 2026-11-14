"""API routes for voice-driven skin care analysis."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.api.deps import (
    get_ai_service,
    get_app_settings,
    get_speech_service,
    get_tts_service,
)
from app.core.config import Settings
from app.core.exceptions import VOICE_RESPONSES, AIAudioValidationError, AIServiceError
from app.schemas.chat import VoiceChatResponse
from app.services.ai_service import BaseAIService
from app.services.speech_service import BaseSpeechService
from app.services.tts_service import (
    BaseTTSService,
    audio_bytes_to_data_uri,
    build_spoken_summary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice"])

__all__ = ["router", "get_ai_service", "get_speech_service", "get_tts_service"]


async def _read_upload_capped(audio: UploadFile, max_bytes: int) -> bytes:
    """Read the upload, refusing to load more than ``max_bytes`` into memory."""
    data = await audio.read(max_bytes + 1)
    if len(data) > max_bytes:
        max_mb = max_bytes // (1024 * 1024)
        raise AIAudioValidationError(f"Audio payload exceeds maximum allowed size of {max_mb}MB.")
    return data


def _check_transcript_length(text: str, settings: Settings) -> str:
    if len(text) > settings.MAX_MESSAGE_CHARS:
        raise AIAudioValidationError(
            f"The recording is too long to analyse (over {settings.MAX_MESSAGE_CHARS} characters of speech). "
            "Please describe your concern more briefly."
        )
    return text


@router.post(
    "/chat",
    response_model=VoiceChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Voice Skin Care Chat Analysis",
    description=(
        "Accepts recorded audio (multipart/form-data). Uses the browser transcript when supplied "
        "(and USE_CLIENT_TRANSCRIPT is on), otherwise transcribes the audio server-side. The text "
        "goes through the same guardrails and analysis as /chat, then a spoken summary is "
        "synthesized when TTS is enabled. A TTS failure never discards the analysis."
    ),
    responses=VOICE_RESPONSES,
)
async def voice_chat(
    audio: UploadFile = File(
        ...,
        description="Recorded audio file (e.g. audio/webm, audio/wav, audio/ogg, audio/mp4)",
    ),
    transcript_hint: Optional[str] = Form(
        None,
        description="Transcript produced by the browser's speech recognition, if available",
    ),
    settings: Settings = Depends(get_app_settings),
    speech_service: BaseSpeechService = Depends(get_speech_service),
    ai_service: BaseAIService = Depends(get_ai_service),
    tts_service: BaseTTSService = Depends(get_tts_service),
) -> VoiceChatResponse:
    """Voice-in to voice-out skin care analysis pipeline."""
    audio_bytes = await _read_upload_capped(audio, settings.MAX_AUDIO_SIZE_BYTES)
    if not audio_bytes:
        raise AIAudioValidationError("Uploaded audio file is empty. Please record audio before submitting.")

    # 1. Transcript: free browser transcript first, paid server transcription otherwise
    hint = (transcript_hint or "").strip()
    if hint and settings.USE_CLIENT_TRANSCRIPT:
        transcription = hint
        transcription_source = "client"
    else:
        transcription = await speech_service.transcribe_audio(
            audio_bytes=audio_bytes,
            filename=audio.filename,
            transcript_hint=hint or None,
        )
        transcription_source = "server"
    transcription = _check_transcript_length(transcription, settings)

    # 2. Same guardrails + analysis pipeline as the text endpoint
    analysis = await ai_service.analyze_skin_concern(transcription)

    # 3. Spoken summary + optional synthesis; failure here keeps the analysis
    spoken_summary = build_spoken_summary(analysis)
    audio_data_uri: Optional[str] = None
    audio_error: Optional[str] = None
    if settings.TTS_ENABLED:
        try:
            synthesized = await tts_service.synthesize_speech(spoken_summary)
            audio_data_uri = audio_bytes_to_data_uri(synthesized, mime_type="audio/wav")
        except AIServiceError as tts_exc:
            logger.warning("TTS failed; returning analysis without audio: %s", tts_exc.message)
            audio_error = tts_exc.message
    else:
        audio_error = "Voice playback is disabled on this server."

    return VoiceChatResponse(
        transcription=transcription,
        transcription_source=transcription_source,
        analysis=analysis,
        spoken_summary=spoken_summary,
        audio=audio_data_uri,
        audio_error=audio_error,
    )
