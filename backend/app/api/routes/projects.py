"""Project management API routes."""

from fastapi import APIRouter, Depends

from app.auth import get_current_user, require_admin, require_architect

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
async def list_projects(user: dict = Depends(get_current_user)):
    """List projects for the current user's tenant."""
    # TODO: Query database
    return {"projects": [], "total": 0}


@router.post("", status_code=201)
async def create_project(
    name: str,
    description: str | None = None,
    user: dict = Depends(require_architect),
):
    """Create a new landing zone project. Requires architect role."""
    # TODO: Create in database
    return {
        "id": "placeholder",
        "name": name,
        "description": description,
        "status": "draft",
        "created_by": user["sub"],
    }


@router.get("/{project_id}")
async def get_project(project_id: str, user: dict = Depends(get_current_user)):
    """Get a specific project."""
    # TODO: Query database
    return {"id": project_id, "status": "draft"}


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, user: dict = Depends(require_admin)):
    """Delete a project. Requires admin role."""
    # TODO: Delete from database
    return None
