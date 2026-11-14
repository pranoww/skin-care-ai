# Skin Care AI — Backend

FastAPI service that turns a described (typed or spoken) skin concern into a cautious, structured, non-diagnostic analysis. Model access goes through LangChain, so the AI provider is a configuration choice.

## Endpoints

- `POST /api/v1/chat`: text in, structured analysis out.
- `POST /api/v1/voice/chat`: audio in (plus an optional browser transcript), returns the transcription, the analysis, a spoken summary, and optional WAV audio.
- `GET /health`: liveness check.

Interactive docs: `http://localhost:8000/docs`

## How a request flows

1. **Input guardrail** (`app/core/guardrails.py`): emergencies, hazardous self-treatment, prompt injection and secret-extraction attempts get a canned safe reply. No model call is made.
2. **Analysis** (`app/services/ai_service.py`): LangChain chat model with structured output validated against `ChatResponse`.
3. **Output guardrail**: softens diagnostic wording, flags prescription drugs, and escalates non-negated red-flag symptoms (fever, pus, bleeding…).

Voice adds transcription before step 1 (skipped when the browser already sent a transcript) and text-to-speech after step 3. If TTS fails, the analysis is still returned, with `audio_error` explaining why.

## Changing the AI provider

Set `LLM_PROVIDER` in `.env`; model defaults follow the provider (see `.env.example`).

| | Groq (free tier) | Gemini |
|---|---|---|
| Analysis | `openai/gpt-oss-120b`, fallback `openai/gpt-oss-20b` | `gemini-3.8-flash` |
| Transcription | Groq Whisper (`whisper-large-v3-turbo`) | Gemini multimodal (`gemini-3.5-flash`) |
| Spoken reply | Browser voice (frontend) | Gemini TTS |

Provider-specific code is limited to `app/services/llm.py` (model factory, error mapping), the Groq Whisper and Gemini TTS classes, and the `build_*_service` selectors. Any other LangChain provider works for analysis after `uv add langchain-<provider>`.

## Keeping API costs down

- `LLM_MAX_RETRIES=0`: no SDK-level retries (LangChain defaults are 2 for Groq, 6 attempts for Gemini). Overload (5xx) retries are separate and bounded by `LLM_OVERLOAD_RETRIES`; quota errors are never retried.
- `USE_CLIENT_TRANSCRIPT=true`: voice requests that include the browser's transcript skip the paid transcription call.
- `TTS_ENABLED=false`: skip the paid speech-synthesis call.
- Guardrail-blocked messages never reach the provider.
- **Tests never call the provider.** `tests/conftest.py` sets a fake key and blocks all non-loopback network connections.

## Setup

```bash
uv sync
cp .env.example .env   # then set GROQ_API_KEY (or LLM_API_KEY)
uv run uvicorn app.main:app --reload --port 8000
```

## Tests

```bash
uv run pytest
```
