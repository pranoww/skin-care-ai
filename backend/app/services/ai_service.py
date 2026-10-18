"""AI Service layer for skin care analysis using Gemini API."""

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Optional

from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AIServiceError,
    AIConfigurationError,
    AIRateLimitError,
    AITimeoutError,
    AIServiceUnavailableError,
    AIResponseValidationError,
    AIProviderError,
)
from app.core.guardrails import AIGuardrail
from app.core.prompts import SKINCARE_SYSTEM_PROMPT
from app.schemas.chat import ChatResponse

logger = logging.getLogger(__name__)


class BaseAIService(ABC):
    """Abstract base class for AI skin care analysis providers.
    
    This isolation ensures that alternative providers (e.g. local models)
    can be integrated in the future without altering the API layer.
    """

    @abstractmethod
    async def analyze_skin_concern(self, message: str) -> ChatResponse:
        """Analyze a user's skin concern description and return a structured response."""
        pass


class GeminiAIService(BaseAIService):
    """Google Gemini implementation of the AI skin care analysis service."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._client: Optional[genai.Client] = None

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
            logger.error("Failed to initialize Gemini client: %s", str(e))
            raise AIConfigurationError("Failed to initialize Gemini client with provided configuration.")

    def _clean_json_text(self, text: str) -> str:
        """Clean markdown formatting or fences from JSON string."""
        cleaned = text.strip()
        # Remove markdown code block if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()

    def _call_gemini(self, message: str) -> ChatResponse:
        """Synchronous call to Gemini API with structured output configuration."""
        client = self._get_client()

        config = types.GenerateContentConfig(
            system_instruction=SKINCARE_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=ChatResponse,
            temperature=0.2,
        )

        response = None
        max_retries = 3

        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=self.settings.GEMINI_MODEL,
                    contents=message,
                    config=config,
                )
                break
            except APIError as api_err:
                raw_msg = str(getattr(api_err, "message", None) or api_err)
                sanitized_msg = raw_msg
                if self.settings.GEMINI_API_KEY:
                    sanitized_msg = sanitized_msg.replace(self.settings.GEMINI_API_KEY, "[REDACTED]")

                is_demand_spike = (
                    api_err.code == 503
                    or "HIGH DEMAND" in sanitized_msg.upper()
                    or "UNAVAILABLE" in sanitized_msg.upper()
                )

                if is_demand_spike and attempt < max_retries - 1:
                    logger.warning(
                        "Gemini temporary demand spike encountered (attempt %d/%d). Retrying...",
                        attempt + 1,
                        max_retries,
                    )
                    import time
                    time.sleep(1.5 * (attempt + 1))
                    continue

                logger.error("Gemini APIError encountered: %s", sanitized_msg)

                # Check for rate limiting / quota exhaustion
                if api_err.code == 429 or "RESOURCE_EXHAUSTED" in sanitized_msg.upper() or "QUOTA" in sanitized_msg.upper():
                    raise AIRateLimitError("Gemini API rate limit or quota exceeded. Please try again later.")
                # Check for temporary service unavailability
                if is_demand_spike:
                    raise AIServiceUnavailableError(
                        "Gemini API is temporarily experiencing high demand. Please try again in a few moments."
                    )
                # Check for timeout / deadline exceeded
                if api_err.code == 504 or "DEADLINE_EXCEEDED" in sanitized_msg.upper():
                    raise AITimeoutError("Gemini API request timed out. Please try again.")

                code_prefix = f" ({api_err.code})" if api_err.code else ""
                raise AIProviderError(f"Upstream Gemini API error{code_prefix}: {sanitized_msg}")
            except TimeoutError:
                logger.error("Timeout occurred while calling Gemini API")
                raise AITimeoutError("Gemini API request timed out. Please try again.")
            except (AIRateLimitError, AIServiceUnavailableError, AITimeoutError, AIProviderError):
                raise
            except Exception as e:
                logger.error("Unexpected error during Gemini API call: %s", str(e))
                raise AIProviderError("Failed to communicate with Gemini API.")

        # If SDK parsed the response directly into the schema
        if hasattr(response, "parsed") and isinstance(response.parsed, ChatResponse):
            return response.parsed

        # Otherwise parse raw JSON text
        raw_text = getattr(response, "text", None)
        if not raw_text or not raw_text.strip():
            logger.error("Empty response received from Gemini API")
            raise AIResponseValidationError("AI returned an empty response.")

        clean_text = self._clean_json_text(raw_text)

        try:
            parsed_data = json.loads(clean_text)
            return ChatResponse.model_validate(parsed_data)
        except (json.JSONDecodeError, Exception) as val_err:
            logger.error("Failed to parse/validate Gemini response: %s | Raw: %s", str(val_err), raw_text)
            raise AIResponseValidationError("AI returned a response that could not be validated against the schema.")

    async def analyze_skin_concern(self, message: str) -> ChatResponse:
        """Asynchronously analyze skin concern using Gemini with pre/post guardrails."""
        # 1. Pre-execution input guardrail check
        guardrail_override = AIGuardrail.check_input_guardrail(message)
        if guardrail_override is not None:
            return guardrail_override

        # 2. Non-blocking Gemini LLM execution
        raw_response = await asyncio.to_thread(self._call_gemini, message)

        # 3. Post-execution output guardrail sanitization
        return AIGuardrail.apply_output_guardrail(raw_response, user_input=message)


# Default export alias as required
AIService = GeminiAIService
