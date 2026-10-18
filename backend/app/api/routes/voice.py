"""API routes for voice-driven skin care analysis."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.core.exceptions import AIAudioValidationError, VOICE_RESPONSES
from app.schemas.chat import VoiceChatResponse
from app.services.ai_service import AIService, BaseAIService
from app.services.speech_service import BaseSpeechService, SpeechService
from app.services.tts_service import (
    BaseTTSService,
    TTSService,
    audio_bytes_to_data_uri,
    build_spoken_summary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice"])


def get_speech_service() -> BaseSpeechService:
    """Dependency provider for Speech-to-Text service."""
    return SpeechService()


def get_ai_service() -> BaseAIService:
    """Dependency provider for skin care AI analysis service."""
    return AIService()


def get_tts_service() -> BaseTTSService:
    """Dependency provider for Text-to-Speech service."""
    return TTSService()


@router.post(
    "/chat",
    response_model=VoiceChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Voice Skin Care Chat Analysis",
    description=(
        "Accepts recorded audio (multipart/form-data), transcribes it via Gemini Speech-to-Text, "
        "processes it through the existing input/output guardrails and AI analysis pipeline, "
        "synthesizes natural conversational speech via Gemini TTS, and returns the transcription, "
        "structured analysis, and playable audio."
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
        description="Optional speech transcript hint",
    ),
    speech_service: BaseSpeechService = Depends(get_speech_service),
    ai_service: BaseAIService = Depends(get_ai_service),
    tts_service: BaseTTSService = Depends(get_tts_service),
) -> VoiceChatResponse:
    """Full voice-in to voice-out skin care analysis pipeline."""
    # 1. Read and validate uploaded audio
    if not audio:
        raise AIAudioValidationError("No audio file was uploaded.")

    audio_bytes = await audio.read()
    if not audio_bytes or len(audio_bytes.strip()) == 0:
        raise AIAudioValidationError("Uploaded audio file is empty. Please record audio before submitting.")

    # 2. Transcribe voice to text via Gemini Speech-to-Text
    transcription = await speech_service.transcribe_audio(
        audio_bytes=audio_bytes,
        filename=audio.filename,
        transcript_hint=transcript_hint,
    )

    # 3. Process transcribed text through existing input guardrails & Gemini AI analysis
    # analyze_skin_concern runs AIGuardrail.check_input_guardrail and apply_output_guardrail
    analysis = await ai_service.analyze_skin_concern(transcription)

    # 4. Create natural conversational summary for voice
    spoken_summary = build_spoken_summary(analysis)

    # 5. Synthesize speech from conversational summary via Gemini TTS
    audio_data_uri: Optional[str] = None
    try:
        synthesized_bytes = await tts_service.synthesize_speech(spoken_summary)
        if synthesized_bytes:
            audio_data_uri = audio_bytes_to_data_uri(synthesized_bytes, mime_type="audio/wav")
    except Exception as tts_exc:
        # If TTS service encounters an issue, log the error while preserving the structured analysis
        logger.warning("TTS synthesis failed or unavailable: %s", str(tts_exc))
        # Re-raise if it's a domain exception in unit tests where TTS failure is tested explicitly
        # But ensure we adhere to domain exceptions
        raise

    return VoiceChatResponse(
        transcription=transcription,
        analysis=analysis,
        spoken_summary=spoken_summary,
        audio=audio_data_uri,
    )
