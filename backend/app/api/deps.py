"""FastAPI dependency providers for the service layer.

Shared by all routers so a single ``app.dependency_overrides[...]`` entry swaps
a service everywhere (used by the tests). Implementations are chosen by
``LLM_PROVIDER``.
"""

from app.core.config import Settings, get_settings
from app.services.ai_service import AIService, BaseAIService
from app.services.speech_service import BaseSpeechService, build_speech_service
from app.services.tts_service import BaseTTSService, build_tts_service


def get_app_settings() -> Settings:
    return get_settings()


def get_ai_service() -> BaseAIService:
    return AIService()


def get_speech_service() -> BaseSpeechService:
    return build_speech_service()


def get_tts_service() -> BaseTTSService:
    return build_tts_service()
