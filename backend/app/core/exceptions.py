"""Centralized custom exceptions and FastAPI exception handlers."""

import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# ==============================================================================
# Domain / Service Exception Hierarchy
# ==============================================================================

class AIServiceError(Exception):
    """Base exception for all AI service errors."""
    def __init__(self, message: str = "An unexpected AI service error occurred.") -> None:
        self.message = message
        super().__init__(self.message)


class AIConfigurationError(AIServiceError):
    """Raised when AI service credentials or configurations are missing or invalid."""
    pass


class AIRateLimitError(AIServiceError):
    """Raised when the AI provider rate limit or quota is exceeded."""
    pass


class AITimeoutError(AIServiceError):
    """Raised when the AI provider request times out."""
    pass


class AIServiceUnavailableError(AIServiceError):
    """Raised when the AI provider is temporarily unavailable or experiencing high demand."""
    pass


class AIResponseValidationError(AIServiceError):
    """Raised when the AI response does not match the expected schema."""
    pass


class AIProviderError(AIServiceError):
    """Raised when the upstream AI provider returns an API error."""
    pass


class AIAudioValidationError(AIServiceError):
    """Raised when uploaded audio is empty, invalid, exceeds size, or is corrupted."""
    pass


# ==============================================================================
# Global FastAPI Exception Handlers
# ==============================================================================

async def ai_configuration_error_handler(request: Request, exc: AIConfigurationError) -> JSONResponse:
    logger.error("Configuration error at %s: %s", request.url.path, exc.message)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": exc.message},
    )


async def ai_service_unavailable_error_handler(request: Request, exc: AIServiceUnavailableError) -> JSONResponse:
    logger.warning("AI service unavailable at %s: %s", request.url.path, exc.message)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": exc.message},
    )


async def ai_rate_limit_error_handler(request: Request, exc: AIRateLimitError) -> JSONResponse:
    logger.warning("Rate limit exceeded at %s: %s", request.url.path, exc.message)
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": exc.message},
    )


async def ai_timeout_error_handler(request: Request, exc: AITimeoutError) -> JSONResponse:
    logger.error("AI request timeout at %s: %s", request.url.path, exc.message)
    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content={"detail": exc.message},
    )


async def ai_response_validation_error_handler(request: Request, exc: AIResponseValidationError) -> JSONResponse:
    logger.error("AI response schema validation failed at %s: %s", request.url.path, exc.message)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": exc.message},
    )


async def ai_provider_error_handler(request: Request, exc: AIProviderError) -> JSONResponse:
    logger.error("Upstream AI provider error at %s: %s", request.url.path, exc.message)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": exc.message},
    )


async def ai_audio_validation_error_handler(request: Request, exc: AIAudioValidationError) -> JSONResponse:
    logger.warning("Audio validation failed at %s: %s", request.url.path, exc.message)
    status_code = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", status.HTTP_422_UNPROCESSABLE_ENTITY)
    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message},
    )


async def general_ai_service_error_handler(request: Request, exc: AIServiceError) -> JSONResponse:
    logger.error("Unhandled AIServiceError at %s: %s", request.url.path, exc.message)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": exc.message},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all centralized domain exception handlers with the FastAPI app."""
    app.add_exception_handler(AIAudioValidationError, ai_audio_validation_error_handler)
    app.add_exception_handler(AIConfigurationError, ai_configuration_error_handler)
    app.add_exception_handler(AIServiceUnavailableError, ai_service_unavailable_error_handler)
    app.add_exception_handler(AIRateLimitError, ai_rate_limit_error_handler)
    app.add_exception_handler(AITimeoutError, ai_timeout_error_handler)
    app.add_exception_handler(AIResponseValidationError, ai_response_validation_error_handler)
    app.add_exception_handler(AIProviderError, ai_provider_error_handler)
    app.add_exception_handler(AIServiceError, general_ai_service_error_handler)


# ==============================================================================
# Common OpenAPI Documentation Responses
# ==============================================================================

COMMON_AI_RESPONSES = {
    422: {"description": "Validation error (e.g. empty or invalid message / audio)."},
    429: {"description": "AI provider rate limit or quota exceeded."},
    502: {"description": "Upstream AI provider error or invalid output schema."},
    503: {"description": "AI service configuration error or high demand spike."},
    504: {"description": "AI provider request timed out."},
}

CHAT_RESPONSES = {
    200: {"description": "Structured skin care analysis successfully generated."},
    **COMMON_AI_RESPONSES,
}

VOICE_RESPONSES = {
    200: {"description": "Voice analysis and synthesized speech response successfully generated."},
    **COMMON_AI_RESPONSES,
}
