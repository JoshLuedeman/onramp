"""User management API routes."""


from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_db

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me")
async def get_current_user_profile(user: dict = Depends(get_current_user)):
    """Get the current authenticated user's profile."""
    return user


@router.get("/me/projects")
async def get_user_projects(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get projects for the current user."""
    if db is None:
        return {"projects": [], "message": "Database not configured"}

    try:
        from app.models import Project
        tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
        result = await db.execute(
            select(Project).where(
                Project.created_by == user.get("oid", user.get("sub", "unknown")),
                Project.tenant_id == tenant_id,
            )
        )
        projects = result.scalars().all()
        return {
            "projects": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "status": p.status,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in projects
            ]
        }
    except Exception as e:
        return {"projects": [], "error": str(e)}
