import os
from functools import lru_cache
from typing import Optional
from dotenv import load_dotenv

# Load variables from .env file into environment
load_dotenv()


class Settings:
    """Application configuration loaded from environment variables."""

    PROJECT_NAME: str = "Skin Care AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Gemini Configuration
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    GEMINI_STT_MODEL: str = os.getenv("GEMINI_STT_MODEL", "gemini-3.5-flash")
    GEMINI_TTS_MODEL: str = os.getenv("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
    GEMINI_TTS_VOICE: str = os.getenv("GEMINI_TTS_VOICE", "Kore")
    MAX_AUDIO_SIZE_BYTES: int = 25 * 1024 * 1024  # 25MB

    def validate_gemini_config(self) -> None:
        """Validate that the required Gemini credentials are present."""
        if not self.GEMINI_API_KEY or not self.GEMINI_API_KEY.strip():
            raise ValueError(
                "GEMINI_API_KEY is missing or empty. Please set GEMINI_API_KEY in your .env file."
            )


@lru_cache()
def get_settings() -> Settings:
    """Provide a cached instance of application settings."""
    return Settings()
