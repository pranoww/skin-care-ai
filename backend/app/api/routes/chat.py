"""API routes for skin care chat analysis."""

from fastapi import APIRouter, Depends, status

from app.core.exceptions import CHAT_RESPONSES
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai_service import AIService, BaseAIService

router = APIRouter(prefix="", tags=["Chat"])


def get_ai_service() -> BaseAIService:
    """Dependency provider for the AI service abstraction."""
    return AIService()


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Skin Care Concern",
    description="Accepts a natural language description of a skin concern and returns structured analysis with recommendations and safety guidance.",
    responses=CHAT_RESPONSES,
)
async def analyze_chat(
    request: ChatRequest,
    ai_service: BaseAIService = Depends(get_ai_service),
) -> ChatResponse:
    """Process user message and return structured skin concern analysis."""
    return await ai_service.analyze_skin_concern(request.message)
