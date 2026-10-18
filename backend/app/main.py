"""Main application entrypoint for AI Skin Care Issue Analysis Chatbot."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.chat import router as chat_router
from app.api.routes.voice import router as voice_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.schemas.chat import HealthResponse

settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "AI-powered skin care issue analysis assistant. "
        "Provides structured, cautious skincare guidance and preliminary analysis "
        "based on user-described concerns without replacing professional medical advice."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Register centralized custom exception handlers
register_exception_handlers(app)

# CORS middleware allowing Next.js frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register chat and voice routes under API version prefix
app.include_router(chat_router, prefix=settings.API_V1_STR)
app.include_router(voice_router, prefix=settings.API_V1_STR)


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns the operational status of the service.",
    tags=["Health"],
)
async def health_check() -> HealthResponse:
    """Basic health check endpoint returning status ok."""
    return HealthResponse(status="ok")
