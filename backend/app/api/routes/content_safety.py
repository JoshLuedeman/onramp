"""Content safety API routes — input/output checking, rate limits, config."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.schemas.content_safety import (
    CheckInputRequest,
    CheckOutputRequest,
    ContentSafetyConfig,
)
from app.services.content_safety import content_safety_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/safety", tags=["content-safety"])


@router.post("/check-input")
async def check_input(
    body: CheckInputRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    """Check text for prompt injection patterns."""
    result = content_safety_service.check_input(
        text=body.text,
        strictness=body.strictness,
    )
    return result.model_dump()


@router.post("/check-output")
async def check_output(
    body: CheckOutputRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    """Check AI output for harmful or off-topic content."""
    result = content_safety_service.check_output(
        text=body.text,
        feature=body.feature,
    )
    return result.model_dump()


@router.get("/rate-limit")
async def get_rate_limit(
    user: dict = Depends(get_current_user),
) -> dict:
    """Get current rate limit status for the authenticated user."""
    user_id = user.get("sub", "dev-user-id")
    tenant_id = user.get("tid", user.get("tenant_id"))
    status = content_safety_service.get_rate_limit_status(user_id, tenant_id)
    return status.model_dump()


@router.get("/config")
async def get_config(
    user: dict = Depends(get_current_user),
) -> dict:
    """Get the current content safety configuration."""
    return content_safety_service.config.model_dump()


@router.put("/config")
async def update_config(
    body: ContentSafetyConfig,
    user: dict = Depends(get_current_user),
) -> dict:
    """Update content safety configuration (admin only)."""
    # In a full RBAC system this would check roles; for now the
    # endpoint is protected by auth and can be locked down later.
    user_roles = user.get("roles", [])
    if user_roles and "admin" not in user_roles and "GlobalAdmin" not in user_roles:
        raise HTTPException(status_code=403, detail="Admin access required")

    content_safety_service.update_config(body)
    return {"status": "updated", "config": body.model_dump()}
