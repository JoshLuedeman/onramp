"""Compliance framework API routes."""

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.services.compliance_data import (
    get_all_frameworks,
    get_framework_by_short_name,
    get_controls_for_frameworks,
)

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


@router.get("/frameworks")
async def list_frameworks(user: dict = Depends(get_current_user)):
    """List all available compliance frameworks."""
    return {"frameworks": get_all_frameworks()}


@router.get("/frameworks/{short_name}")
async def get_framework(short_name: str, user: dict = Depends(get_current_user)):
    """Get a specific compliance framework with its controls."""
    framework = get_framework_by_short_name(short_name)
    if framework is None:
        raise HTTPException(status_code=404, detail=f"Framework '{short_name}' not found")
    return framework


@router.post("/controls")
async def get_controls(
    framework_names: list[str], user: dict = Depends(get_current_user)
):
    """Get controls for multiple frameworks."""
    controls = get_controls_for_frameworks(framework_names)
    return {"controls": controls, "total": len(controls)}
