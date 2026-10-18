# Skin Care AI — Backend

FastAPI backend service for Skin Care AI, providing structured skin concern analysis and voice interaction using Google Gemini.

## Features

- **Text & Voice Consultation**: Supports structured text analysis (`POST /api/v1/chat`) and voice audio analysis (`POST /api/v1/voice/chat`).
- **Google Gemini Integration**: 
  - Skin analysis powered by `gemini-3.8-flash`.
  - Speech-to-Text powered by multimodal Gemini audio understanding.
  - Text-to-Speech powered by `gemini-3.8-flash-tts` (configurable to `gemini-3.8-flash-lite-tts`).
- **Medical Safety Guardrails**: Input triage for emergency symptoms, prompt injection defense, and non-prescriptive output softening.
- **Automated Validation**: Pydantic v2 schemas and centralized domain exception handling.

## Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv)
- Google Gemini API Key

## Setup

```bash
# Sync virtual environment and install dependencies
uv sync

# Configure environment variables
cp .env.example .env
```

Set your API key in `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.8-flash
GEMINI_TTS_MODEL=gemini-3.8-flash-tts
GEMINI_TTS_VOICE=Kore
```

## Running the Server

```bash
uv run uvicorn app.main:app --reload --port 8000
```

- **Interactive API Docs**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

## Running Tests

```bash
uv run pytest
```
