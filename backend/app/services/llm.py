"""Provider-neutral LLM access through LangChain.

Everything provider-specific lives behind ``build_chat_model`` (which model class
to construct) and ``map_llm_error`` (how failures become domain exceptions).
Services only ever see LangChain ``BaseChatModel`` / ``Runnable`` objects and the
exceptions in ``app.core.exceptions``.
"""

import asyncio
import logging
from typing import Any, Optional, Sequence, Type

from langchain.chat_models import init_chat_model
from langchain_core.exceptions import (
    ModelAPIError,
    ModelAuthenticationError,
    ModelConnectionError,
    ModelInvalidRequestError,
    ModelNotFoundError,
    ModelPermissionDeniedError,
    ModelRateLimitError,
    ModelTimeoutError,
    OutputParserException,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import (
    AIConfigurationError,
    AIProviderError,
    AIRateLimitError,
    AIResponseValidationError,
    AIServiceError,
    AIServiceUnavailableError,
    AITimeoutError,
)

logger = logging.getLogger(__name__)


def sdk_max_retries(settings: Settings) -> int:
    """Translate LLM_MAX_RETRIES (extra retries) into the provider SDK's own unit.

    Gemini's SDK counts total attempts (1 = no retry); most others, including
    Groq and OpenAI, count retries after the first attempt.
    """
    extra = max(0, settings.LLM_MAX_RETRIES)
    return extra + 1 if settings.LLM_PROVIDER == "google_genai" else extra


def build_chat_model(settings: Settings, model: Optional[str], **model_kwargs: Any) -> BaseChatModel:
    """Construct a chat model for the configured provider.

    No network request is made here; the first request happens on invoke.
    """
    if not settings.LLM_API_KEY:
        raise AIConfigurationError(
            f"No API key configured for provider '{settings.LLM_PROVIDER}'. "
            "Set LLM_API_KEY (or the provider's usual key variable) in your .env file."
        )
    if not model:
        raise AIConfigurationError(
            f"No model configured for provider '{settings.LLM_PROVIDER}'. Set LLM_MODEL in your .env file."
        )
    try:
        return init_chat_model(
            model,
            model_provider=settings.LLM_PROVIDER,
            api_key=settings.LLM_API_KEY,
            max_retries=sdk_max_retries(settings),
            timeout=settings.LLM_TIMEOUT_SECONDS,
            **model_kwargs,
        )
    except Exception as exc:  # unknown provider, missing integration package, bad kwargs
        logger.error(
            "Failed to initialise chat model %r for provider %r: %s",
            model,
            settings.LLM_PROVIDER,
            redact(str(exc), settings),
        )
        raise AIConfigurationError(
            f"Could not initialise model '{model}' for provider '{settings.LLM_PROVIDER}'. "
            "Check LLM_PROVIDER, the model name, and that the provider's LangChain package is installed."
        ) from exc


def redact(message: str, settings: Settings) -> str:
    """Remove the configured API key from a string before it is logged or returned."""
    if settings.LLM_API_KEY:
        message = message.replace(settings.LLM_API_KEY, "[REDACTED]")
    return message


def _status_code(exc: BaseException) -> Optional[int]:
    for attr in ("code", "status_code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    value = getattr(response, "status_code", None)
    return value if isinstance(value, int) else None


# Provider messages meaning "the model answered, but not in the requested format".
_STRUCTURED_FAILURE_MARKERS = (
    "tool_use_failed",
    "did not call a tool",
    "json_validate_failed",
    "failed to generate json",
)


def map_llm_error(
    exc: BaseException,
    settings: Settings,
    label: str,
    invalid_request_error: Type[AIServiceError] = AIProviderError,
) -> AIServiceError:
    """Translate any provider/LangChain failure into a domain exception.

    ``label`` names the operation for user-facing messages (e.g. "Speech-to-Text").
    ``invalid_request_error`` lets callers decide what an HTTP 400 means for them
    (for transcription it means the audio itself was rejected).
    """
    if isinstance(exc, AIServiceError):
        return exc

    detail = redact(str(exc), settings)
    code = _status_code(exc)
    logger.error("%s request failed (%s, status=%s): %s", label, type(exc).__name__, code, detail)

    if isinstance(exc, ModelRateLimitError) or code == 429:
        return AIRateLimitError(f"{label} rate limit or quota exceeded. Please try again later.")
    type_name = type(exc).__name__
    if (
        isinstance(exc, (ModelTimeoutError, TimeoutError, asyncio.TimeoutError))
        or code in (408, 504)
        or "Timeout" in type_name
    ):
        return AITimeoutError(f"{label} request timed out. Please try again.")
    if isinstance(exc, (ModelAuthenticationError, ModelPermissionDeniedError)) or code in (401, 403):
        return AIConfigurationError(f"{label} rejected the API key. Check LLM_API_KEY in your .env file.")
    if isinstance(exc, ModelNotFoundError) or code == 404:
        return AIConfigurationError(f"{label} model was not found. Check the model name in your .env file.")
    if isinstance(exc, ModelConnectionError) or (code is None and "Connection" in type_name):
        return AIServiceUnavailableError(
            f"Could not reach the {label} provider. Check the server's internet connection and try again."
        )
    if isinstance(exc, ModelAPIError) or (code is not None and code >= 500):
        return AIServiceUnavailableError(
            f"{label} service is temporarily unavailable or under high demand. Please try again shortly."
        )
    if any(marker in detail.lower() for marker in _STRUCTURED_FAILURE_MARKERS):
        return AIResponseValidationError(
            f"{label} couldn't produce a structured answer for this message. "
            "Please rephrase it as a description of your skin concern and try again."
        )
    if isinstance(exc, ModelInvalidRequestError) or code == 400:
        return invalid_request_error(f"{label} rejected the request as invalid.")
    if isinstance(exc, (OutputParserException, ValidationError)):
        return AIResponseValidationError(f"{label} returned a response that did not match the expected format.")

    # Providers without LangChain error classification: fall back to keywords.
    upper = detail.upper()
    if "RESOURCE_EXHAUSTED" in upper or "QUOTA" in upper or "RATE LIMIT" in upper:
        return AIRateLimitError(f"{label} rate limit or quota exceeded. Please try again later.")
    if "UNAVAILABLE" in upper or "HIGH DEMAND" in upper or "OVERLOADED" in upper:
        return AIServiceUnavailableError(
            f"{label} service is temporarily unavailable or under high demand. Please try again shortly."
        )
    if "DEADLINE_EXCEEDED" in upper or "TIMED OUT" in upper:
        return AITimeoutError(f"{label} request timed out. Please try again.")
    return AIProviderError(f"{label} provider error. Please try again.")


def message_text(message: Any) -> str:
    """Extract plain text from a chat model response, whatever the content shape."""
    if isinstance(message, str):
        return message
    if isinstance(message, BaseMessage):
        content = message.content
    else:
        content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "".join(parts)


_OVERLOAD_STATUS_CODES = {500, 502, 503}
_OVERLOAD_KEYWORDS = ("UNAVAILABLE", "HIGH DEMAND", "OVERLOADED")


def is_overload_error(exc: BaseException) -> bool:
    """True for transient "server busy" failures that are worth retrying.

    Quota (429), timeouts (504), auth and invalid-request errors are excluded:
    retrying those either cannot help or spends quota.
    """
    if isinstance(exc, (ModelRateLimitError, ModelTimeoutError, ModelInvalidRequestError)):
        return False
    code = _status_code(exc)
    if code is not None:
        return code in _OVERLOAD_STATUS_CODES
    if isinstance(exc, ModelAPIError):
        return True
    upper = str(exc).upper()
    return any(keyword in upper for keyword in _OVERLOAD_KEYWORDS)


async def invoke_with_overload_handling(
    runnables: Sequence[Any],
    payload: Any,
    settings: Settings,
    label: str,
    invalid_request_error: Type[AIServiceError] = AIProviderError,
    **invoke_kwargs: Any,
) -> Any:
    """Invoke the first runnable, retrying only on overload, then try fallbacks in order.

    Each runnable gets 1 + LLM_OVERLOAD_RETRIES attempts with linear backoff.
    Any non-overload error is mapped and raised immediately.
    """
    last_exc: Optional[BaseException] = None
    retries = max(0, settings.LLM_OVERLOAD_RETRIES)
    for index, runnable in enumerate(runnables):
        for attempt in range(retries + 1):
            try:
                return await runnable.ainvoke(payload, **invoke_kwargs)
            except Exception as exc:
                if not is_overload_error(exc):
                    raise map_llm_error(exc, settings, label, invalid_request_error) from exc
                last_exc = exc
                if attempt < retries:
                    delay = settings.LLM_OVERLOAD_BACKOFF_SECONDS * (attempt + 1)
                    logger.warning(
                        "%s provider overloaded (model #%d, attempt %d/%d); retrying in %.1fs",
                        label, index + 1, attempt + 1, retries + 1, delay,
                    )
                    if delay > 0:
                        await asyncio.sleep(delay)
        if index + 1 < len(runnables):
            logger.warning("%s primary model still overloaded; switching to fallback model", label)
    assert last_exc is not None
    raise map_llm_error(last_exc, settings, label, invalid_request_error) from last_exc
