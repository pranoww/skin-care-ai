# Skin Care AI — Frontend

A modern, responsive Next.js application for the Skin Care AI analysis system.

## Tech Stack
- **Framework**: Next.js 16 (App Router)
- **Language**: JavaScript (React 19)
- **Styling**: Tailwind CSS v4 with custom tokens and typography
- **Icons & Fonts**: Inter & Material Symbols Outlined

## Directory Structure
```text
frontend/
├── app/
│   ├── layout.jsx          # Root layout
│   ├── page.jsx            # Main consultation interface
│   └── globals.css         # Theme tokens and typography
├── components/
│   ├── chat/
│   │   ├── ChatContainer.jsx    # Consultation analysis panel
│   │   ├── ChatInput.jsx        # Clinical description input form
│   │   ├── ChatMessage.jsx      # User inquiry card
│   │   ├── VoiceRecorder.jsx    # Voice recording component
│   │   └── AnalysisResponse.jsx # Structured AI diagnostic assessment card
│   ├── layout/
│   │   ├── Header.jsx           # Application header
│   │   ├── Footer.jsx           # Application footer
│   │   └── SplitLayout.jsx      # Responsive 40/60 split layout
│   └── ui/
│       ├── Button.jsx           # Action button component
│       └── LoadingState.jsx     # Loading skeleton for AI analysis
├── lib/
│   └── api.js                   # Client module for FastAPI backend
├── .env.example                 # Example environment template
└── package.json
```

## Getting Started

### 1. Install Dependencies
```bash
npm install
```

### 2. Configure Environment
Create `.env.local` using `.env.example`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Run Development Server
```bash
npm run dev
```

Available at: `http://localhost:3000`
