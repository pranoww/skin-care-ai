"""Groq provider support. Everything here is offline: models are constructed but
never invoked, and the Whisper client is a fake."""

import asyncio
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.core.exceptions import (
    AIAudioValidationError,
    AIProviderError,
    AIRateLimitError,
    AIServiceUnavailableError,
    AITimeoutError,
)
from app.services.ai_service import LangChainAIService
from app.services.llm import build_chat_model, map_llm_error, sdk_max_retries
from app.services.speech_service import (
    GroqWhisperSpeechService,
    LangChainSpeechService,
    build_speech_service,
)
from app.services.tts_service import (
    GeminiTTSService,
    UnavailableTTSService,
    build_tts_service,
)


@pytest.fixture
def groq_env(monkeypatch):
    """Simulate a .env that switched to Groq but still contains Gemini values."""
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.8-flash")
    for name in ("LLM_MODEL", "LLM_STT_MODEL", "LLM_FALLBACK_MODEL", "TTS_ENABLED", "LLM_MAX_RETRIES"):
        monkeypatch.delenv(name, raising=False)
    return Settings()


def test_groq_settings_ignore_gemini_values(groq_env):
    assert groq_env.LLM_API_KEY == "groq-key"
    assert groq_env.LLM_MODEL == "openai/gpt-oss-120b"
    assert groq_env.LLM_FALLBACK_MODEL == "openai/gpt-oss-20b"
    assert groq_env.LLM_STT_MODEL == "whisper-large-v3-turbo"
    assert groq_env.TTS_ENABLED is False


def test_llm_api_key_overrides_provider_key(groq_env, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "explicit")
    assert Settings().LLM_API_KEY == "explicit"


def test_retry_setting_means_the_same_for_every_provider(groq_env):
    google = Settings()
    google.LLM_PROVIDER = "google_genai"
    assert sdk_max_retries(groq_env) == 0       # Groq: retries after first attempt
    assert sdk_max_retries(google) == 1         # Gemini: total attempts


def test_build_groq_chat_model_offline(groq_env):
    model = build_chat_model(groq_env, groq_env.LLM_MODEL, temperature=0.2)
    assert type(model).__name__ == "ChatGroq"
    assert model.model_name == "openai/gpt-oss-120b"
    assert model.max_retries == 0


def test_groq_analysis_service_builds_structured_primary_and_fallback(groq_env):
    service = LangChainAIService(settings=groq_env)
    assert service._get_structured_model() is not None
    assert service._get_fallback_model() is not None


def test_provider_selects_speech_and_tts_implementations(groq_env):
    assert isinstance(build_speech_service(groq_env), GroqWhisperSpeechService)
    assert isinstance(build_tts_service(groq_env), UnavailableTTSService)

    google = Settings()
    google.LLM_PROVIDER = "google_genai"
    assert isinstance(build_speech_service(google), LangChainSpeechService)
    assert isinstance(build_tts_service(google), GeminiTTSService)


def test_unavailable_tts_raises_domain_error():
    with pytest.raises(AIProviderError):
        asyncio.run(UnavailableTTSService("groq").synthesize_speech("hello"))


# ------------------------------------------------------------------------------
# Groq Whisper with a fake client
# ------------------------------------------------------------------------------

class _FakeTranscriptions:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _fake_client(*outcomes):
    transcriptions = _FakeTranscriptions(outcomes)
    return SimpleNamespace(audio=SimpleNamespace(transcriptions=transcriptions)), transcriptions


def _status_error(code):
    exc = Exception(f"status {code}")
    exc.status_code = code
    return exc


def test_whisper_transcribes_with_configured_model(groq_env):
    client, calls = _fake_client(SimpleNamespace(text="  Itchy rash on my wrist. "))
    service = GroqWhisperSpeechService(groq_env, client=client)

    text = asyncio.run(service.transcribe_audio(b"\x1aE\xdf\xa3webm", filename="voice_recording.webm"))
    assert text == "Itchy rash on my wrist."
    sent = calls.calls[0]
    assert sent["model"] == "whisper-large-v3-turbo"
    assert sent["file"] == ("voice_recording.webm", b"\x1aE\xdf\xa3webm")


def test_whisper_retries_overload_but_not_quota(groq_env):
    groq_env.LLM_OVERLOAD_BACKOFF_SECONDS = 0
    client, calls = _fake_client(_status_error(503), SimpleNamespace(text="ok"))
    assert asyncio.run(GroqWhisperSpeechService(groq_env, client=client).transcribe_audio(b"RIFFx")) == "ok"
    assert len(calls.calls) == 2

    client, calls = _fake_client(_status_error(429))
    with pytest.raises(AIRateLimitError):
        asyncio.run(GroqWhisperSpeechService(groq_env, client=client).transcribe_audio(b"RIFFx"))
    assert len(calls.calls) == 1


def test_whisper_bad_audio_and_empty_text(groq_env):
    client, _ = _fake_client(_status_error(400))
    with pytest.raises(AIAudioValidationError):
        asyncio.run(GroqWhisperSpeechService(groq_env, client=client).transcribe_audio(b"RIFFx"))

    client, _ = _fake_client(SimpleNamespace(text="   "))
    with pytest.raises(AIAudioValidationError):
        asyncio.run(GroqWhisperSpeechService(groq_env, client=client).transcribe_audio(b"RIFFx"))


def test_real_groq_sdk_errors_map_correctly(groq_env):
    import groq
    import httpx

    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    rate_limited = groq.RateLimitError("quota", response=httpx.Response(429, request=request), body=None)
    server_busy = groq.InternalServerError("busy", response=httpx.Response(503, request=request), body=None)

    assert type(map_llm_error(rate_limited, groq_env, "AI analysis")) is AIRateLimitError
    assert type(map_llm_error(server_busy, groq_env, "AI analysis")) is AIServiceUnavailableError
    assert type(map_llm_error(groq.APITimeoutError(request=request), groq_env, "AI analysis")) is AITimeoutError
    connection = map_llm_error(groq.APIConnectionError(request=request), groq_env, "AI analysis")
    assert type(connection) is AIServiceUnavailableError and "reach" in connection.message


# ------------------------------------------------------------------------------
# Structured output: Groq uses strict json_schema (constrained decoding), so the
# model cannot answer in plain text the way tool calling allowed.
# ------------------------------------------------------------------------------

def _bound_kwargs(runnable):
    first = runnable.first if hasattr(runnable, "first") else runnable
    return first.kwargs


def test_groq_analysis_uses_strict_json_schema(groq_env):
    service = LangChainAIService(settings=groq_env)
    response_format = _bound_kwargs(service._get_structured_model())["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True

    schema = response_format["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert "example" not in schema
    assert schema["properties"]["severity"]["enum"] == ["low", "medium", "high", "unknown"]


def test_groq_fallback_model_also_uses_strict_json_schema(groq_env):
    service = LangChainAIService(settings=groq_env)
    assert _bound_kwargs(service._get_fallback_model())["response_format"]["json_schema"]["strict"] is True


def test_structured_output_method_is_configurable(groq_env, monkeypatch):
    monkeypatch.setenv("LLM_STRUCTURED_OUTPUT", "function_calling")
    settings = Settings()
    assert settings.LLM_STRUCTURED_OUTPUT == "function_calling"
    tools = _bound_kwargs(LangChainAIService(settings=settings)._get_structured_model())
    assert "tools" in tools


def test_tool_use_failure_is_a_response_error_not_invalid_request(groq_env):
    import groq
    import httpx

    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    body = {"error": {"message": "Tool choice is required, but model did not call a tool",
                      "type": "invalid_request_error", "code": "tool_use_failed"}}
    exc = groq.BadRequestError("Error code: 400 - " + str(body), response=httpx.Response(400, request=request), body=body)
    mapped = map_llm_error(exc, groq_env, "AI analysis")
    assert type(mapped).__name__ == "AIResponseValidationError"
    assert "rephras" in mapped.message.lower()


def test_out_of_range_confidence_is_clamped_not_rejected():
    raw = {
        "skin_concern": "Possible dryness", "summary": "Mild dryness.", "possible_factors": [],
        "recommendations": [], "severity": "low", "confidence": 1.4, "professional_advice": False,
    }
    assert LangChainAIService._coerce(raw).confidence == 1.0
