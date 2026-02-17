"""Compliance scoring API routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import get_current_user
from app.services.compliance_scoring import compliance_scorer

router = APIRouter(prefix="/api/scoring", tags=["scoring"])


class ScoreRequest(BaseModel):
    architecture: dict
    frameworks: list[str]
    use_ai: bool = True


@router.post("/evaluate")
async def evaluate_compliance(
    request: ScoreRequest, user: dict = Depends(get_current_user)
):
    """Evaluate an architecture against compliance frameworks."""
    if request.use_ai:
        result = await compliance_scorer.score_architecture_with_ai(
            request.architecture, request.frameworks
        )
    else:
        result = compliance_scorer.score_architecture(request.architecture, request.frameworks)
    return result
