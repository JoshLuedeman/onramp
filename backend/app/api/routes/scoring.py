"""Compliance scoring API routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import get_current_user
from app.services.compliance_scoring import compliance_scorer


router = APIRouter(prefix="/api/scoring", tags=["scoring"])


class ScoreRequest(BaseModel):
    architecture: dict
    frameworks: list[str]


@router.post("/evaluate")
async def evaluate_compliance(
    request: ScoreRequest, user: dict = Depends(get_current_user)
):
    """Evaluate an architecture against compliance frameworks."""
    result = compliance_scorer.score_architecture(request.architecture, request.frameworks)
    return result
