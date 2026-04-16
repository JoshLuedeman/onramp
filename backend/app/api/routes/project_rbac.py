"""Project-level RBAC API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_db
from app.models.project_member import ProjectMember
from app.services.project_rbac_service import project_rbac

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["project-rbac"])


@router.get("/{project_id}/permissions")
async def get_project_permissions(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's effective role on a project."""
    if db is None:
        return {
            "project_id": project_id,
            "user_id": user.get("sub", "dev-user-id"),
            "effective_role": "admin",
        }

    user_id = user.get("sub", "")
    effective = await project_rbac.get_effective_role(
        db, project_id, user_id,
    )
    if effective is None:
        raise HTTPException(
            status_code=403, detail="No access to this project",
        )
    return {
        "project_id": project_id,
        "user_id": user_id,
        "effective_role": effective,
    }


@router.get("/{project_id}/roles")
async def list_project_roles(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all member roles for a project."""
    if db is None:
        return {"project_id": project_id, "members": []}

    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
        )
    )
    members = list(result.scalars().all())
    return {
        "project_id": project_id,
        "members": [
            {
                "user_id": m.user_id,
                "role": m.role,
                "invited_at": (
                    m.invited_at.isoformat() if m.invited_at else None
                ),
                "accepted_at": (
                    m.accepted_at.isoformat() if m.accepted_at else None
                ),
            }
            for m in members
        ],
    }
