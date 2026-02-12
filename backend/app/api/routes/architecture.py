"""Architecture generation API routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import get_current_user, require_architect
from app.services.archetypes import get_archetype_for_answers, list_archetypes

router = APIRouter(prefix="/api/architecture", tags=["architecture"])


class GenerateRequest(BaseModel):
    answers: dict[str, str | list[str]]
    use_ai: bool = False


@router.get("/archetypes")
async def get_archetypes(user: dict = Depends(get_current_user)):
    """List available landing zone archetypes."""
    return {"archetypes": list_archetypes()}


@router.post("/generate")
async def generate_architecture(
    request: GenerateRequest, user: dict = Depends(require_architect)
):
    """Generate a landing zone architecture from questionnaire answers."""
    if request.use_ai:
        from app.services.ai_foundry import ai_client
        architecture = await ai_client.generate_architecture(request.answers)
    else:
        architecture = get_archetype_for_answers(request.answers)

    return {"architecture": architecture}
