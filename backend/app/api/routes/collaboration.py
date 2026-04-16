"""Collaboration API routes — members, comments, and activity feed."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_db
from app.schemas.collaboration import (
    CommentCreate,
    CommentListResponse,
    CommentResponse,
    ProjectMemberCreate,
    ProjectMemberListResponse,
    ProjectMemberResponse,
)
from app.services.collaboration_service import collaboration_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/projects/{project_id}",
    tags=["collaboration"],
)


# ── Members ──────────────────────────────────────────────────────────────


@router.post("/members", response_model=ProjectMemberResponse)
async def add_member(
    project_id: str,
    body: ProjectMemberCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Invite a user to a project."""
    try:
        result = await collaboration_service.add_member(
            db=db,
            project_id=project_id,
            email=body.email,
            role=body.role,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Failed to add member to project %s", project_id)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/members", response_model=ProjectMemberListResponse)
async def list_members(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all members of a project."""
    try:
        return await collaboration_service.list_members(
            db=db, project_id=project_id
        )
    except Exception as exc:
        logger.exception(
            "Failed to list members for project %s", project_id
        )
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/members/{user_id}")
async def remove_member(
    project_id: str,
    user_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from a project."""
    try:
        removed = await collaboration_service.remove_member(
            db=db, project_id=project_id, user_id=user_id
        )
        if not removed:
            raise HTTPException(
                status_code=404, detail="Member not found"
            )
        return {"removed": True, "user_id": user_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Failed to remove member from project %s", project_id
        )
        raise HTTPException(status_code=500, detail=str(exc))


# ── Comments ─────────────────────────────────────────────────────────────


@router.post("/comments", response_model=CommentResponse)
async def add_comment(
    project_id: str,
    body: CommentCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a comment to a project."""
    user_id = user.get("oid", user.get("sub", "dev-user"))
    try:
        result = await collaboration_service.add_comment(
            db=db,
            project_id=project_id,
            user_id=user_id,
            content=body.content,
            component_ref=body.component_ref,
        )
        return result
    except Exception as exc:
        logger.exception(
            "Failed to add comment to project %s", project_id
        )
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/comments", response_model=CommentListResponse)
async def list_comments(
    project_id: str,
    component_ref: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List comments for a project, optionally filtered by component."""
    try:
        return await collaboration_service.list_comments(
            db=db,
            project_id=project_id,
            component_ref=component_ref,
        )
    except Exception as exc:
        logger.exception(
            "Failed to list comments for project %s", project_id
        )
        raise HTTPException(status_code=500, detail=str(exc))


# ── Activity Feed ────────────────────────────────────────────────────────


@router.get("/activity")
async def get_activity_feed(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the activity feed for a project."""
    try:
        return await collaboration_service.get_activity_feed(
            db=db, project_id=project_id
        )
    except Exception as exc:
        logger.exception(
            "Failed to get activity feed for project %s", project_id
        )
        raise HTTPException(status_code=500, detail=str(exc))
