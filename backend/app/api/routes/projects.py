"""Project management API routes."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_db
from app.schemas.project import (
    ProjectCreate,
    ProjectStatsResponse,
    ProjectUpdate,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


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

        tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
        result = await db.execute(select(Project).where(Project.tenant_id == tenant_id))
        projects = result.scalars().all()
        return {
            "projects": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "status": p.status,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
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
    now = datetime.now(timezone.utc)
    if db is None:
        return {
            "id": str(uuid.uuid4()),
            "name": project.name,
            "description": project.description,
            "status": "draft",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "message": "Created in-memory (database not configured)",
        }

    try:
        from app.models import Project

        tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))
        new_project = Project(
            id=str(uuid.uuid4()),
            name=project.name,
            description=project.description,
            status="draft",
            tenant_id=tenant_id,
            created_by=user.get("oid", user.get("id")),
            created_at=now,
            updated_at=now,
        )
        db.add(new_project)
        await db.flush()
        return {
            "id": new_project.id,
            "name": new_project.name,
            "description": new_project.description,
            "status": new_project.status,
            "created_at": new_project.created_at.isoformat() if new_project.created_at else None,
            "updated_at": new_project.updated_at.isoformat() if new_project.updated_at else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_project_stats(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get project statistics for the current user's tenant."""
    if db is None:
        return ProjectStatsResponse(
            total=0,
            by_status={},
            avg_compliance_score=None,
            deployment_success_rate=None,
            recent_projects=[],
        )

    try:
        from app.models import Project

        tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))

        # Count by status
        result = await db.execute(
            select(Project.status, func.count(Project.id))
            .where(Project.tenant_id == tenant_id)
            .group_by(Project.status)
        )
        by_status = {row[0]: row[1] for row in result.all()}
        total = sum(by_status.values())

        # Recent projects
        result = await db.execute(
            select(Project)
            .where(Project.tenant_id == tenant_id)
            .order_by(Project.updated_at.desc())
            .limit(5)
        )
        recent = result.scalars().all()
        recent_projects = [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "status": p.status,
                "tenant_id": p.tenant_id,
                "created_by": p.created_by,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in recent
        ]

        return ProjectStatsResponse(
            total=total,
            by_status=by_status,
            avg_compliance_score=None,
            deployment_success_rate=None,
            recent_projects=recent_projects,
        )
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
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}")
async def update_project(
    project_id: str,
    updates: ProjectUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a project's name, description, and/or status."""
    if db is None:
        now = datetime.now(timezone.utc)
        return {
            "id": project_id,
            "name": updates.name or "Mock Project",
            "description": updates.description,
            "status": updates.status.value if updates.status else "draft",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "message": "Updated in-memory (database not configured)",
        }

    try:
        from app.models import Project

        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if updates.name is not None:
            project.name = updates.name
        if updates.description is not None:
            project.description = updates.description
        if updates.status is not None:
            project.status = updates.status.value
        project.updated_at = datetime.now(timezone.utc)

        await db.flush()
        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
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
