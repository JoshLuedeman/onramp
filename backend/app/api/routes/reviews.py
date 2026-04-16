"""Architecture review API routes — submit, review, status, and config."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_db
from app.schemas.review import (
    ReviewActionRequest,
    ReviewConfigurationRequest,
    ReviewConfigurationResponse,
    ReviewHistoryResponse,
    ReviewResponse,
    ReviewStatusResponse,
    SubmitForReviewRequest,
)
from app.services.review_service import review_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/architectures/{arch_id}/reviews",
    tags=["architecture-reviews"],
)

config_router = APIRouter(
    prefix="/api/projects/{project_id}",
    tags=["architecture-reviews"],
)


# ── Submit / Withdraw ────────────────────────────────────────────────────


@router.post("/submit")
async def submit_for_review(
    arch_id: str,
    body: SubmitForReviewRequest | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit an architecture for review, locking edits."""
    user_id = user.get("oid", user.get("sub", "dev-user"))
    try:
        result = await review_service.submit_for_review(
            db=db,
            architecture_id=arch_id,
            submitter_id=user_id,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception(
            "Failed to submit architecture %s for review", arch_id
        )
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/withdraw")
async def withdraw_review(
    arch_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Withdraw an architecture from review, returning to draft."""
    user_id = user.get("oid", user.get("sub", "dev-user"))
    try:
        result = await review_service.withdraw_review(
            db=db,
            architecture_id=arch_id,
            submitter_id=user_id,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception(
            "Failed to withdraw review for architecture %s", arch_id
        )
        raise HTTPException(status_code=500, detail=str(exc))


# ── Review Actions ───────────────────────────────────────────────────────


@router.post("", response_model=ReviewResponse)
async def perform_review(
    arch_id: str,
    body: ReviewActionRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Perform a review action (approve, request changes, reject)."""
    user_id = user.get("oid", user.get("sub", "dev-user"))
    try:
        result = await review_service.perform_review(
            db=db,
            architecture_id=arch_id,
            reviewer_id=user_id,
            action=body.action.value,
            comments=body.comments,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception(
            "Failed to perform review on architecture %s", arch_id
        )
        raise HTTPException(status_code=500, detail=str(exc))


# ── Queries ──────────────────────────────────────────────────────────────


@router.get("", response_model=ReviewHistoryResponse)
async def get_review_history(
    arch_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the full review history for an architecture."""
    try:
        return await review_service.get_review_history(
            db=db, architecture_id=arch_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception(
            "Failed to get review history for architecture %s", arch_id
        )
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/status", response_model=ReviewStatusResponse)
async def get_review_status(
    arch_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current review status with approval counts."""
    try:
        return await review_service.get_review_status(
            db=db, architecture_id=arch_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception(
            "Failed to get review status for architecture %s", arch_id
        )
        raise HTTPException(status_code=500, detail=str(exc))


# ── Configuration ────────────────────────────────────────────────────────


@config_router.put(
    "/review-config",
    response_model=ReviewConfigurationResponse,
)
async def configure_review_requirements(
    project_id: str,
    body: ReviewConfigurationRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set the review approval requirements for a project."""
    try:
        result = await review_service.configure_requirements(
            db=db,
            project_id=project_id,
            required_approvals=body.required_approvals,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception(
            "Failed to configure review for project %s", project_id
        )
        raise HTTPException(status_code=500, detail=str(exc))
