"""AI service layer for skin care analysis, provider-neutral via LangChain."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.exceptions import (  # noqa: F401  (re-exported for callers/tests)
    AIConfigurationError,
    AIProviderError,
    AIRateLimitError,
    AIResponseValidationError,
    AIServiceError,
    AIServiceUnavailableError,
    AITimeoutError,
)
from app.core.guardrails import AIGuardrail
from app.core.prompts import SKINCARE_SYSTEM_PROMPT
from app.schemas.chat import ANALYSIS_OUTPUT_SCHEMA, ChatResponse
from app.services.llm import build_chat_model, invoke_with_overload_handling

logger = logging.getLogger(__name__)


class BaseAIService(ABC):
    """Abstract base class for AI skin care analysis providers."""

    @abstractmethod
    async def analyze_skin_concern(self, message: str) -> ChatResponse:
        """Analyze a user's skin concern description and return a structured response."""


class LangChainAIService(BaseAIService):
    """Skin concern analysis using any LangChain chat model with structured output.

    ``structured_model`` can be injected (tests, alternative chains). By default
    it is built from settings the first time a message passes the input
    guardrail, so blocked messages never touch the provider.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        structured_model: Optional[Runnable] = None,
        fallback_structured_model: Optional[Runnable] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._structured_model = structured_model
        self._fallback_model = fallback_structured_model

    def _build_structured(self, model_name: str) -> Runnable:
        chat_model = build_chat_model(self.settings, model_name, temperature=0.2)
        method = self.settings.LLM_STRUCTURED_OUTPUT
        if method == "json_schema":
            # Strict constrained decoding: the reply must match the schema, so the
            # model cannot fall back to plain text. Returns a dict (see _coerce).
            return chat_model.with_structured_output(ANALYSIS_OUTPUT_SCHEMA, method="json_schema", strict=True)
        if method:
            return chat_model.with_structured_output(ChatResponse, method=method)
        return chat_model.with_structured_output(ChatResponse)

    def _get_structured_model(self) -> Runnable:
        if self._structured_model is None:
            self._structured_model = self._build_structured(self.settings.LLM_MODEL)
        return self._structured_model

    def _get_fallback_model(self) -> Optional[Runnable]:
        fallback_name = self.settings.LLM_FALLBACK_MODEL
        if self._fallback_model is None and fallback_name and fallback_name != self.settings.LLM_MODEL:
            self._fallback_model = self._build_structured(fallback_name)
        return self._fallback_model

    @staticmethod
    def _coerce(result: Any) -> ChatResponse:
        if isinstance(result, ChatResponse):
            return result
        if isinstance(result, dict):
            confidence = result.get("confidence")
            if isinstance(confidence, (int, float)):
                result = {**result, "confidence": min(1.0, max(0.0, float(confidence)))}
            try:
                return ChatResponse.model_validate(result)
            except ValidationError as exc:
                raise AIResponseValidationError(
                    "AI returned a response that could not be validated against the schema."
                ) from exc
        raise AIResponseValidationError("AI returned an empty or unrecognised response.")

    async def analyze_skin_concern(self, message: str) -> ChatResponse:
        """Analyze a skin concern with pre- and post-execution guardrails."""
        guardrail_override = AIGuardrail.check_input_guardrail(message)
        if guardrail_override is not None:
            return guardrail_override

        models = [self._get_structured_model()]
        fallback = self._get_fallback_model()
        if fallback is not None:
            models.append(fallback)

        result = await invoke_with_overload_handling(
            models,
            [SystemMessage(content=SKINCARE_SYSTEM_PROMPT), HumanMessage(content=message)],
            self.settings,
            "AI analysis",
        )

        return AIGuardrail.apply_output_guardrail(self._coerce(result), user_input=message)


# Default implementation used by the API layer.
AIService = LangChainAIService
