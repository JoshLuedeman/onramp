"""Template safety / review workflow API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.auth.rbac import RoleChecker
from app.db.session import get_db
from app.services.template_safety_service import template_safety_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["template-safety"])

_require_admin = RoleChecker(["admin"])


class _ScanRequest(BaseModel):
    template_json: str | None = Field(
        None, description="Raw JSON payload to scan",
    )


class _RejectRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)


@router.post("/{template_id}/scan")
async def scan_template(
    template_id: str,
    body: _ScanRequest | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Scan a template for dangerous patterns."""
    json_payload: str | None = None
    if body and body.template_json:
        json_payload = body.template_json
    elif db is not None:
        tpl = await template_safety_service._get_template(
            db, template_id,
        )
        if tpl is None:
            raise HTTPException(
                status_code=404, detail="Template not found",
            )
        json_payload = tpl.architecture_json

    result = template_safety_service.scan_template(json_payload)
    result["template_id"] = template_id
    return result


@router.post("/{template_id}/submit-review")
async def submit_for_review(
    template_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a template for review."""
    if db is None:
        raise HTTPException(
            status_code=503, detail="Database not configured",
        )

    result = await template_safety_service.submit_for_review(
        db, template_id,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{template_id}/approve")
async def approve_template(
    template_id: str,
    user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Approve a template after review (admin only)."""
    if db is None:
        raise HTTPException(
            status_code=503, detail="Database not configured",
        )

    reviewer_id = user.get("sub", "unknown")
    result = await template_safety_service.approve_template(
        db, template_id, reviewer_id,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{template_id}/reject")
async def reject_template(
    template_id: str,
    body: _RejectRequest,
    user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Reject a template with reason (admin only)."""
    if db is None:
        raise HTTPException(
            status_code=503, detail="Database not configured",
        )

    reviewer_id = user.get("sub", "unknown")
    result = await template_safety_service.reject_template(
        db, template_id, reviewer_id, body.reason,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/pending-review")
async def list_pending_review(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List templates pending review (admin only)."""
    if db is None:
        return {"templates": [], "page": page, "page_size": page_size}

    return await template_safety_service.list_pending_review(
        db, page=page, page_size=page_size,
    )
