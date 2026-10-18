# Skin Care AI

A modern, safety-first web application for analyzing user-described skin concerns using Google Gemini. Supports natural-language text input and voice interaction with real-time Speech-to-Text and Text-to-Speech synthesis.

## Features

- Skin concern analysis from text
- Voice input
- Speech-to-text
- Voice responses
- Medical safety guardrails
- Prompt injection protection

## Tech Stack

Backend:
- Python
- FastAPI
- Google Gemini
- Pydantic
- uv

Frontend:
- Next.js
- React
- Tailwind CSS

## Project Structure

```text
skin-care-ai/
├── backend/
│   ├── app/
│   │   ├── api/routes/          # API endpoints (chat, voice)
│   │   ├── core/                # Config, exceptions, guardrails, prompts
│   │   ├── schemas/             # Pydantic request & response models
│   │   └── services/            # Gemini AI, STT, and TTS services
│   ├── tests/                   # Automated pytest suite
│   ├── pyproject.toml           # Backend dependencies and configuration
│   └── .env.example             # Backend environment template
├── frontend/
│   ├── app/                     # Next.js App Router (pages, layout, styles)
│   ├── components/              # UI, layout, and chat consultation components
│   ├── lib/                     # API client module
│   ├── package.json             # Frontend dependencies
│   └── .env.example             # Frontend environment template
└── README.md
```

## Setup

Backend:

```bash
cd backend
uv sync
```

Frontend:

```bash
cd frontend
npm install
```

## Environment Variables

Backend environment variables are required. Copy the example file and configure your Google Gemini API key:

```bash
cp backend/.env.example backend/.env
```

Example:

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.8-flash
GEMINI_TTS_MODEL=gemini-3.8-flash-tts
GEMINI_TTS_VOICE=Kore
```

Frontend environment variables (optional, defaults to `http://localhost:8000`):

```bash
cp frontend/.env.example frontend/.env.local
```

## Running

Backend:

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm run dev
```

API documentation:

http://localhost:8000/docs

## Testing

```bash
cd backend
uv run pytest
```
