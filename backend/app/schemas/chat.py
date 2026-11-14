from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import Settings


class SeverityLevel(str, Enum):
    """Severity classification for skin care concerns."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class ChatRequest(BaseModel):
    """User input payload for skin concern analysis."""
    message: str = Field(
        ...,
        description="Natural language description of the skin concern.",
        examples=["I have small red bumps on my forehead and my skin feels itchy."]
    )

    model_config = ConfigDict(
        str_strip_whitespace=True
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Message cannot be empty or contain only whitespace.")
        if len(trimmed) > Settings.MAX_MESSAGE_CHARS:
            raise ValueError(
                f"Message exceeds maximum allowed length of {Settings.MAX_MESSAGE_CHARS} characters."
            )
        return trimmed


class ChatResponse(BaseModel):
    """Structured response containing skin concern analysis."""
    skin_concern: str = Field(
        ...,
        description="Identified potential skin concern or category."
    )
    summary: str = Field(
        ...,
        description="Short non-definitive explanation of the condition."
    )
    possible_factors: List[str] = Field(
        default_factory=list,
        description="List of possible contributing factors."
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="General non-prescription skincare recommendations."
    )
    severity: SeverityLevel = Field(
        ...,
        description="Estimated severity level: low, medium, high, or unknown."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for the analysis between 0.0 and 1.0."
    )
    professional_advice: bool = Field(
        ...,
        description="Indicates whether professional medical evaluation is recommended."
    )

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "skin_concern": "Possible acne/follicular irritation",
                "summary": "The symptoms may be related to acne, irritation, or another skin condition. A text description alone is not enough to determine the exact cause.",
                "possible_factors": [
                    "Excess oil production",
                    "Sweat and heat",
                    "Hair or skincare products",
                    "Skin irritation"
                ],
                "recommendations": [
                    "Use a gentle cleanser",
                    "Avoid picking or squeezing the bumps",
                    "Use non-comedogenic skincare products",
                    "Monitor whether the condition improves"
                ],
                "severity": "low",
                "confidence": 0.70,
                "professional_advice": False
            }
        }
    )


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str = "ok"


class VoiceChatResponse(BaseModel):
    """Response schema for voice analysis endpoint."""
    transcription: str = Field(
        ...,
        description="Transcribed text from user's voice input."
    )
    transcription_source: Literal["client", "server"] = Field(
        default="server",
        description="'client' when the browser transcript was used, 'server' when the audio was transcribed by the AI provider.",
    )
    analysis: ChatResponse = Field(
        ...,
        description="Structured skin concern analysis from the AI service."
    )
    spoken_summary: str = Field(
        ...,
        description="Conversational plain-language summary suitable for audio playback."
    )
    audio: Optional[str] = Field(
        default=None,
        description="Synthesized audio data URL (data:audio/wav;base64,...) for client playback."
    )
    audio_error: Optional[str] = Field(
        default=None,
        description="Why audio is missing (TTS disabled or failed). The analysis is still valid.",
    )


# JSON schema sent to the model for structured output. Kept flat and explicit
# (no $refs, no numeric bounds, no examples) so strict constrained decoding
# works across providers; ChatResponse still validates the result afterwards.
ANALYSIS_OUTPUT_SCHEMA = {
    "title": "SkinCareAnalysis",
    "description": "Cautious, non-diagnostic analysis of a described skin concern.",
    "type": "object",
    "properties": {
        "skin_concern": {"type": "string", "description": "Possible concern or category, phrased tentatively."},
        "summary": {"type": "string", "description": "Short explanation using cautious, non-definitive wording."},
        "possible_factors": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Possible contributing factors.",
        },
        "recommendations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "General, non-prescription care suggestions.",
        },
        "severity": {"type": "string", "enum": ["low", "medium", "high", "unknown"]},
        "confidence": {"type": "number", "description": "Between 0.0 and 1.0."},
        "professional_advice": {
            "type": "boolean",
            "description": "True when seeing a dermatologist or doctor is recommended.",
        },
    },
    "required": [
        "skin_concern",
        "summary",
        "possible_factors",
        "recommendations",
        "severity",
        "confidence",
        "professional_advice",
    ],
    "additionalProperties": False,
}
