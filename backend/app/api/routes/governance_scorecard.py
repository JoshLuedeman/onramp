"""Governance scorecard API routes — real-time aggregated governance health."""

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.schemas.governance_scorecard import (
    GovernanceScoreResponse,
    ScoreTrendResponse,
)
from app.services.governance_scorer import governance_scorer

router = APIRouter(
    prefix="/api/governance/scorecard",
    tags=["governance-scorecard"],
)


# ── Current scorecard ────────────────────────────────────────────────────────


@router.get("/{project_id}", response_model=GovernanceScoreResponse)
async def get_scorecard(
    project_id: str,
    user: dict = Depends(get_current_user),
):
    """Get the current governance scorecard for a project."""
    result = await governance_scorer.calculate_overall_score(project_id)
    return GovernanceScoreResponse(**result)


# ── Score trend ──────────────────────────────────────────────────────────────


@router.get("/{project_id}/trend", response_model=ScoreTrendResponse)
async def get_score_trend(
    project_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of days of trend data"),
    user: dict = Depends(get_current_user),
):
    """Get the governance score trend over time."""
    result = await governance_scorer.get_score_trend(project_id, days=days)
    return ScoreTrendResponse(**result)


# ── Refresh ──────────────────────────────────────────────────────────────────


@router.post("/{project_id}/refresh", response_model=GovernanceScoreResponse)
async def refresh_scorecard(
    project_id: str,
    user: dict = Depends(get_current_user),
):
    """Trigger a recalculation of the governance scorecard.

    Forces all governance monitors to re-evaluate and publishes an
    SSE event with the updated scores.
    """
    result = await governance_scorer.calculate_overall_score(project_id)
    return GovernanceScoreResponse(**result)


# ── Executive summary ────────────────────────────────────────────────────────


@router.get("/{project_id}/summary")
async def get_executive_summary(
    project_id: str,
    user: dict = Depends(get_current_user),
):
    """Get the executive summary for the governance scorecard."""
    categories = await governance_scorer.get_category_scores(project_id)
    summary = governance_scorer.generate_executive_summary(categories)
    return {"executive_summary": summary}
