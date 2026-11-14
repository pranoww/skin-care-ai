"""Application settings loaded from environment variables.

The AI provider is chosen by configuration, not code. ``LLM_PROVIDER`` picks the
LangChain provider (``google_genai``, ``groq``, ...) and the defaults below adapt
to it, so switching usually means changing that one line plus the API key.

API keys are looked up as ``LLM_API_KEY`` first, then the provider's usual
variable (``GEMINI_API_KEY``/``GOOGLE_API_KEY`` for Gemini, ``GROQ_API_KEY`` for
Groq, ``<PROVIDER>_API_KEY`` otherwise). Legacy ``GEMINI_*`` model names are
only honoured when the provider is Gemini.
"""

import os
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

# Load variables from .env file into environment
load_dotenv()

GOOGLE = "google_genai"
GROQ = "groq"

# Per-provider defaults: model, fallback model, STT model, TTS model, TTS on?
_PROVIDER_DEFAULTS: Dict[str, dict] = {
    GOOGLE: {
        "model": "gemini-3.8-flash",
        "fallback_model": None,
        "stt_model": "gemini-3.5-flash",
        "tts_model": "gemini-3.8-flash-tts",
        "tts_enabled": True,
        "structured_output": None,  # library default (works for Gemini)
    },
    GROQ: {
        "model": "openai/gpt-oss-120b",
        "fallback_model": "openai/gpt-oss-20b",
        "stt_model": "whisper-large-v3-turbo",
        "tts_model": None,
        "tts_enabled": False,
        # Tool calling lets gpt-oss reply in plain text (Groq 400 tool_use_failed);
        # strict json_schema constrains decoding to the schema instead.
        "structured_output": "json_schema",
    },
}
_GENERIC_DEFAULTS = {
    "model": None,
    "fallback_model": None,
    "stt_model": None,
    "tts_model": None,
    "tts_enabled": False,
    "structured_output": None,
}

_PROVIDER_KEY_VARS: Dict[str, Tuple[str, ...]] = {
    GOOGLE: ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    GROQ: ("GROQ_API_KEY",),
}


def _env(name: str, *fallbacks: str, default: Optional[str] = None) -> Optional[str]:
    """Return the first non-empty value among ``name`` and its fallback names."""
    for key in (name, *fallbacks):
        value = os.getenv(key)
        if value is not None and value.strip():
            return value.strip()
    return default


def _env_int(name: str, default: int) -> int:
    value = _env(name)
    return int(value) if value is not None else default


def _env_bool(name: str, default: bool) -> bool:
    value = _env(name)
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes", "on")


def _env_list(name: str, default: List[str]) -> List[str]:
    value = _env(name)
    if value is None:
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings:
    """Application configuration loaded from environment variables."""

    PROJECT_NAME: str = "Skin Care AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    MAX_AUDIO_SIZE_BYTES: int = 25 * 1024 * 1024  # 25MB
    MAX_MESSAGE_CHARS: int = 2000

    def __init__(self) -> None:
        provider = _env("LLM_PROVIDER", default=GOOGLE).lower()
        defaults = _PROVIDER_DEFAULTS.get(provider, _GENERIC_DEFAULTS)
        is_google = provider == GOOGLE

        def legacy(name: str) -> Tuple[str, ...]:
            # GEMINI_* names only make sense for the Gemini provider.
            return (name,) if is_google else ()

        key_vars = _PROVIDER_KEY_VARS.get(provider, (f"{provider.upper()}_API_KEY",))

        self.LLM_PROVIDER: str = provider
        self.LLM_API_KEY: Optional[str] = _env("LLM_API_KEY", *key_vars)

        # Models
        self.LLM_MODEL: Optional[str] = _env("LLM_MODEL", *legacy("GEMINI_MODEL"), default=defaults["model"])
        self.LLM_FALLBACK_MODEL: Optional[str] = _env("LLM_FALLBACK_MODEL", default=defaults["fallback_model"])
        self.LLM_STT_MODEL: Optional[str] = _env(
            "LLM_STT_MODEL", *legacy("GEMINI_STT_MODEL"), default=defaults["stt_model"]
        )
        self.LLM_TTS_MODEL: Optional[str] = _env(
            "LLM_TTS_MODEL", *legacy("GEMINI_TTS_MODEL"), default=defaults["tts_model"]
        )
        # How structured output is requested: "json_schema" (strict, constrained
        # decoding), "function_calling", "json_mode", or empty for the library default.
        self.LLM_STRUCTURED_OUTPUT: Optional[str] = _env(
            "LLM_STRUCTURED_OUTPUT", default=defaults["structured_output"]
        )
        self.LLM_TTS_VOICE: str = _env("LLM_TTS_VOICE", *legacy("GEMINI_TTS_VOICE"), default="Kore")

        # Budget controls.
        # LLM_MAX_RETRIES = extra SDK-level retries after the first attempt, for
        # any provider (translated per provider in app/services/llm.py). 0 means
        # one request only; LangChain defaults are 2 (Groq) and 6 (Gemini).
        self.LLM_MAX_RETRIES: int = _env_int("LLM_MAX_RETRIES", 0)
        self.LLM_TIMEOUT_SECONDS: int = _env_int("LLM_TIMEOUT_SECONDS", 60)

        # Overload handling. Only "server busy" errors (500/502/503) are retried,
        # never quota (429) or invalid requests. A rejected 503 produces no tokens.
        self.LLM_OVERLOAD_RETRIES: int = _env_int("LLM_OVERLOAD_RETRIES", 2)
        self.LLM_OVERLOAD_BACKOFF_SECONDS: float = float(_env("LLM_OVERLOAD_BACKOFF_SECONDS", default="2"))

        # Server-side speech synthesis. Off by default for providers without a
        # TTS implementation; the frontend then reads the summary with the
        # browser's built-in voice.
        self.TTS_ENABLED: bool = _env_bool("TTS_ENABLED", defaults["tts_enabled"])
        # When the browser already transcribed the recording (Web Speech API),
        # use that text instead of paying for a server-side transcription call.
        self.USE_CLIENT_TRANSCRIPT: bool = _env_bool("USE_CLIENT_TRANSCRIPT", True)

        # HTTP
        self.CORS_ORIGINS: List[str] = _env_list(
            "CORS_ORIGINS", ["http://localhost:3000", "http://127.0.0.1:3000"]
        )

    def validate_llm_config(self) -> None:
        """Validate that the required LLM credentials are present."""
        if not self.LLM_API_KEY:
            raise ValueError(
                f"No API key for provider '{self.LLM_PROVIDER}'. Set LLM_API_KEY in your .env file."
            )


@lru_cache()
def get_settings() -> Settings:
    """Provide a cached instance of application settings."""
    return Settings()
