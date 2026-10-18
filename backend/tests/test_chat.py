"""Unit and API integration tests for the skin care chatbot application."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.routes.chat import get_ai_service
from app.main import app
from app.schemas.chat import ChatRequest, ChatResponse, SeverityLevel
from app.services.ai_service import (
    BaseAIService,
    AIConfigurationError,
    AIRateLimitError,
    AITimeoutError,
    AIResponseValidationError,
    AIProviderError,
)

client = TestClient(app)


class MockSuccessAIService(BaseAIService):
    """Mock AI Service simulating successful structured output."""

    async def analyze_skin_concern(self, message: str) -> ChatResponse:
        return ChatResponse(
            skin_concern="Possible acne/follicular irritation",
            summary="The symptoms may be related to acne, irritation, or another skin condition. A text description alone is not enough to determine the exact cause.",
            possible_factors=[
                "Excess oil production",
                "Sweat and heat",
                "Hair or skincare products",
                "Skin irritation"
            ],
            recommendations=[
                "Use a gentle cleanser",
                "Avoid picking or squeezing the bumps",
                "Use non-comedogenic skincare products",
                "Monitor whether the condition improves"
            ],
            severity=SeverityLevel.LOW,
            confidence=0.70,
            professional_advice=False,
        )


class MockFailingAIService(BaseAIService):
    """Mock AI Service simulating various failure modes."""

    def __init__(self, exception_to_raise: Exception):
        self.exception_to_raise = exception_to_raise

    async def analyze_skin_concern(self, message: str) -> ChatResponse:
        raise self.exception_to_raise


def test_health_check():
    """Verify that the health check endpoint returns 200 and status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_success_with_mock():
    """Verify POST /api/v1/chat returns structured response on successful analysis."""
    app.dependency_overrides[get_ai_service] = lambda: MockSuccessAIService()

    try:
        payload = {"message": "I have small red bumps on my forehead and my skin feels itchy."}
        response = client.post("/api/v1/chat", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["skin_concern"] == "Possible acne/follicular irritation"
        assert "summary" in data
        assert isinstance(data["possible_factors"], list)
        assert len(data["possible_factors"]) > 0
        assert isinstance(data["recommendations"], list)
        assert len(data["recommendations"]) > 0
        assert data["severity"] == "low"
        assert 0.0 <= data["confidence"] <= 1.0
        assert data["professional_advice"] is False
    finally:
        app.dependency_overrides.clear()


def test_chat_validation_empty_message():
    """Verify that an empty message string triggers HTTP 422 Unprocessable Entity."""
    response = client.post("/api/v1/chat", json={"message": ""})
    assert response.status_code == 422


def test_chat_validation_whitespace_only():
    """Verify that a whitespace-only message triggers HTTP 422 Unprocessable Entity."""
    response = client.post("/api/v1/chat", json={"message": "    "})
    assert response.status_code == 422


def test_chat_validation_missing_field():
    """Verify that a request missing the 'message' field triggers HTTP 422."""
    response = client.post("/api/v1/chat", json={})
    assert response.status_code == 422


def test_chat_validation_excessive_length():
    """Verify that a message exceeding maximum length triggers HTTP 422."""
    response = client.post("/api/v1/chat", json={"message": "a" * 2001})
    assert response.status_code == 422


def test_chat_configuration_error_handling():
    """Verify that missing configuration raises HTTP 503."""
    app.dependency_overrides[get_ai_service] = lambda: MockFailingAIService(
        AIConfigurationError("GEMINI_API_KEY is not configured.")
    )

    try:
        response = client.post("/api/v1/chat", json={"message": "I have dry skin."})
        assert response.status_code == 503
        assert "not configured" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_chat_rate_limit_error_handling():
    """Verify that provider rate limits raise HTTP 429."""
    app.dependency_overrides[get_ai_service] = lambda: MockFailingAIService(
        AIRateLimitError("Rate limit exceeded.")
    )

    try:
        response = client.post("/api/v1/chat", json={"message": "I have dry skin."})
        assert response.status_code == 429
        assert "Rate limit" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_chat_timeout_error_handling():
    """Verify that timeouts raise HTTP 504."""
    app.dependency_overrides[get_ai_service] = lambda: MockFailingAIService(
        AITimeoutError("Gemini API request timed out.")
    )

    try:
        response = client.post("/api/v1/chat", json={"message": "I have dry skin."})
        assert response.status_code == 504
        assert "timed out" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_chat_provider_error_handling():
    """Verify that upstream provider errors raise HTTP 502."""
    app.dependency_overrides[get_ai_service] = lambda: MockFailingAIService(
        AIProviderError("Upstream service failure.")
    )

    try:
        response = client.post("/api/v1/chat", json={"message": "I have dry skin."})
        assert response.status_code == 502
    finally:
        app.dependency_overrides.clear()


def test_chat_response_schema_validation():
    """Verify Pydantic schema validation for ChatResponse."""
    valid_data = {
        "skin_concern": "Possible eczema",
        "summary": "This may be consistent with mild irritation.",
        "possible_factors": ["Dry air", "Soaps"],
        "recommendations": ["Moisturize regularly"],
        "severity": "low",
        "confidence": 0.85,
        "professional_advice": False,
    }
    model = ChatResponse.model_validate(valid_data)
    assert model.severity == SeverityLevel.LOW
    assert model.confidence == 0.85

    # Invalid confidence (> 1.0)
    with pytest.raises(ValidationError):
        ChatResponse.model_validate({**valid_data, "confidence": 1.5})

    # Invalid severity
    with pytest.raises(ValidationError):
        ChatResponse.model_validate({**valid_data, "severity": "critical"})
