# Skin Care AI: Frontend

Next.js interface for Skin Care AI. Users type or record a description of a skin concern and get a structured, non-diagnostic analysis from the FastAPI backend.

## Stack

- Next.js 16 (App Router) and React 19
- Tailwind CSS 4 with design tokens and shared component classes in `app/globals.css`
- IBM Plex Sans and Source Serif 4 via `next/font`
- Lucide icons

## Getting started

```bash
npm install
cp .env.example .env.local   # optional
npm run dev
```

Runs at http://localhost:3000. The backend must be running (default `http://localhost:8000`, configurable with `NEXT_PUBLIC_API_URL`).

## Structure

```text
frontend/
├── app/
│   ├── layout.jsx              # Fonts, header, footer
│   ├── page.jsx                # Request state and orchestration
│   └── globals.css             # Tokens, buttons, panels, fields
├── components/
│   ├── chat/
│   │   ├── ChatInput.jsx       # Description form with character limit
│   │   ├── VoiceRecorder.jsx   # Recording + live browser transcription
│   │   ├── ChatContainer.jsx   # Result panel: errors, loading, empty state
│   │   ├── ChatMessage.jsx     # The submitted description
│   │   └── AnalysisResponse.jsx# Analysis card and "Listen to summary"
│   ├── layout/                 # Header, Footer, SplitLayout
│   └── ui/                     # Button, LoadingState
└── lib/api.js                  # Backend client
```

## Voice

- **Transcription:** while recording, the browser's Web Speech API transcribes live. The transcript is sent with the audio, so the backend can skip a server transcription call.
- **Playback:** if the backend returns no audio (TTS disabled, unsupported by the provider, or failed), "Listen to summary" falls back to the browser's speech synthesis.
- **Limits:** recordings stop automatically at 2 minutes. The backend accepts up to 2,000 characters of text.

## Scripts

| Command | Purpose |
|---|---|
| `npm run dev` | Development server |
| `npm run build` | Production build |
| `npm start` | Serve the production build |
| `npm run lint` | ESLint |
