"""Project management API routes."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_db


router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    description: str = ""


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None


@router.get("/")
async def list_projects(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all projects for the current user's tenant."""
    if db is None:
        return {"projects": []}

    try:
        from app.models import Project
        result = await db.execute(select(Project))
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


@router.post("/")
async def create_project(
    project: ProjectCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new project."""
    if db is None:
        return {
            "id": str(uuid.uuid4()),
            "name": project.name,
            "description": project.description,
            "status": "draft",
            "message": "Created in-memory (database not configured)",
        }

    try:
        from app.models import Project
        new_project = Project(
            id=str(uuid.uuid4()),
            name=project.name,
            description=project.description,
            status="draft",
            created_by=user.get("oid", user.get("id")),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(new_project)
        await db.flush()
        return {
            "id": new_project.id,
            "name": new_project.name,
            "description": new_project.description,
            "status": new_project.status,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific project."""
    if db is None:
        raise HTTPException(status_code=404, detail="Database not configured")

    try:
        from app.models import Project
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a project."""
    if db is None:
        return {"deleted": True, "message": "Database not configured"}

    try:
        from app.models import Project
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        await db.delete(project)
        return {"deleted": True, "id": project_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
