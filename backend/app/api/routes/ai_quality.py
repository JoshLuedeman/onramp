"""API routes for AI quality infrastructure.

Provides endpoints for:
- Human feedback on AI outputs (submit, list, stats)
- Token usage tracking (summary, by-feature breakdown)
- Prompt version management (list, get by name/version)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user
from app.schemas.ai_quality import (
    AIFeedbackCreate,
    AIFeedbackResponse,
    FeedbackRating,
    FeedbackStatsItem,
    FeedbackStatsResponse,
    PromptListResponse,
    PromptVersionResponse,
    TokenUsageByFeature,
    TokenUsageSummary,
)
from app.services.prompt_registry import prompt_registry
from app.services.token_tracker import token_tracker

router = APIRouter(prefix="/api/ai", tags=["ai-quality"])

# ---------------------------------------------------------------------------
# In-memory feedback store (dev mode — no DB required)
# ---------------------------------------------------------------------------
_feedback_store: list[dict] = []

# ---------------------------------------------------------------------------
# Feedback endpoints
# ---------------------------------------------------------------------------


@router.post("/feedback", response_model=AIFeedbackResponse)
async def submit_feedback(
    body: AIFeedbackCreate,
    user: dict = Depends(get_current_user),
):
    """Submit human feedback on an AI output."""
    user_id = user.get("oid", user.get("sub", "dev-user-id"))
    tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))

    # Determine prompt version that produced this output
    pv = prompt_registry.get_latest_version(body.feature)
    prompt_version_str = f"{body.feature}_v{pv}" if pv else f"{body.feature}_v1"

    record = {
        "id": str(uuid.uuid4()),
        "feature": body.feature,
        "output_id": body.output_id,
        "rating": body.rating.value,
        "comment": body.comment,
        "prompt_version": prompt_version_str,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "created_at": datetime.now(timezone.utc),
    }
    _feedback_store.append(record)
    return AIFeedbackResponse(**record)


@router.get("/feedback", response_model=list[AIFeedbackResponse])
async def list_feedback(
    feature: str | None = Query(None),
    rating: FeedbackRating | None = Query(None),
    user: dict = Depends(get_current_user),
):
    """List feedback records with optional filters."""
    tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
    results = [f for f in _feedback_store if f["tenant_id"] == tenant_id]
    if feature:
        results = [f for f in results if f["feature"] == feature]
    if rating:
        results = [f for f in results if f["rating"] == rating.value]
    return [AIFeedbackResponse(**f) for f in results]


@router.get("/feedback/stats", response_model=FeedbackStatsResponse)
async def feedback_stats(
    user: dict = Depends(get_current_user),
):
    """Return per-feature feedback statistics."""
    tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
    records = [f for f in _feedback_store if f["tenant_id"] == tenant_id]

    # Group by feature
    by_feature: dict[str, list[dict]] = {}
    for r in records:
        by_feature.setdefault(r["feature"], []).append(r)

    stats: list[FeedbackStatsItem] = []
    for feat, recs in sorted(by_feature.items()):
        pos = sum(1 for r in recs if r["rating"] == "positive")
        neg = sum(1 for r in recs if r["rating"] == "negative")
        total = pos + neg
        stats.append(
            FeedbackStatsItem(
                feature=feat,
                total=total,
                positive=pos,
                negative=neg,
                positive_rate=round(pos / total, 4) if total > 0 else 0.0,
            )
        )
    return FeedbackStatsResponse(stats=stats)


# ---------------------------------------------------------------------------
# Token usage endpoints
# ---------------------------------------------------------------------------


@router.get("/tokens/usage", response_model=TokenUsageSummary)
async def token_usage_summary(
    feature: str | None = Query(None),
    days: int = Query(30, ge=1, le=365),
    user: dict = Depends(get_current_user),
):
    """Return aggregate token usage summary."""
    tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
    user_id = user.get("oid", user.get("sub", "dev-user-id"))
    summary = token_tracker.get_usage_summary(
        tenant_id=tenant_id, user_id=user_id, feature=feature, days=days
    )
    return TokenUsageSummary(**summary)


@router.get("/tokens/usage/by-feature", response_model=TokenUsageByFeature)
async def token_usage_by_feature(
    days: int = Query(30, ge=1, le=365),
    user: dict = Depends(get_current_user),
):
    """Return token usage breakdown by AI feature."""
    tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
    summaries = token_tracker.get_usage_by_feature(tenant_id=tenant_id, days=days)
    return TokenUsageByFeature(
        summaries=[TokenUsageSummary(**s) for s in summaries]
    )


# ---------------------------------------------------------------------------
# Prompt version endpoints
# ---------------------------------------------------------------------------


@router.get("/prompts", response_model=PromptListResponse)
async def list_prompts(
    user: dict = Depends(get_current_user),
):
    """List all registered prompt versions."""
    entries = prompt_registry.list_prompts()
    return PromptListResponse(
        prompts=[
            PromptVersionResponse(
                id=str(uuid.uuid4()),
                name=e.name,
                version=e.version,
                template=e.template,
                metadata_json=e.metadata,
                is_active=e.is_active,
                created_at=e.created_at,
            )
            for e in entries
        ]
    )


@router.get("/prompts/{name}")
async def get_prompt_latest(
    name: str,
    user: dict = Depends(get_current_user),
):
    """Get the latest version of a prompt by name."""
    entry = prompt_registry.get_prompt(name)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Prompt '{name}' not found")
    return PromptVersionResponse(
        id=str(uuid.uuid4()),
        name=entry.name,
        version=entry.version,
        template=entry.template,
        metadata_json=entry.metadata,
        is_active=entry.is_active,
        created_at=entry.created_at,
    )


@router.get("/prompts/{name}/{version}")
async def get_prompt_version(
    name: str,
    version: int,
    user: dict = Depends(get_current_user),
):
    """Get a specific version of a prompt."""
    entry = prompt_registry.get_prompt(name, version=version)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"Prompt '{name}' version {version} not found",
        )
    return PromptVersionResponse(
        id=str(uuid.uuid4()),
        name=entry.name,
        version=entry.version,
        template=entry.template,
        metadata_json=entry.metadata,
        is_active=entry.is_active,
        created_at=entry.created_at,
    )
