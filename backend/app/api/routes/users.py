"""User management API routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me")
async def get_current_user_profile(user: dict = Depends(get_current_user)):
    """Get the current authenticated user's profile."""
    return {
        "id": user["sub"],
        "name": user["name"],
        "email": user["email"],
        "roles": user.get("roles", []),
    }


@router.get("/me/projects")
async def get_user_projects(user: dict = Depends(get_current_user)):
    """Get projects for the current user."""
    # TODO: Query database for user's projects
    return {"projects": [], "total": 0}


@router.get("/me/configurations")
async def get_saved_configurations(user: dict = Depends(get_current_user)):
    """Get saved landing zone configurations for the current user."""
    # TODO: Query database for saved configurations
    return {"configurations": [], "total": 0}
