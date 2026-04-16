"""Remediation approval workflow API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_db
from app.schemas.approval import (
    ApprovalDecision,
    ApprovalRequestCreate,
    ApprovalRequestListResponse,
    ApprovalRequestResponse,
    PendingCountResponse,
)
from app.services.approval_service import approval_service

router = APIRouter(
    prefix="/api/governance/approvals", tags=["approvals"]
)


@router.post("/", response_model=ApprovalRequestResponse)
async def create_approval_request(
    payload: ApprovalRequestCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new approval request."""
    requester = user.get("email", user.get("sub", "unknown"))
    tenant_id = user.get("tenant_id")

    result = await approval_service.create_request(
        request_type=payload.request_type.value,
        resource_id=payload.resource_id,
        details=payload.details,
        requester=requester,
        project_id=payload.project_id,
        tenant_id=tenant_id,
        db=db,
    )

    if db is None:
        # Dev mode: return the dict directly as a response
        return ApprovalRequestResponse(**result)

    return ApprovalRequestResponse(**result)


@router.get("/", response_model=ApprovalRequestListResponse)
async def list_approval_requests(
    status: str | None = Query(None, description="Filter by status"),
    project_id: str | None = Query(None, description="Filter by project"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List approval requests with optional filters."""
    tenant_id = user.get("tenant_id")
    requests = await approval_service.get_requests(
        status=status,
        project_id=project_id,
        tenant_id=tenant_id,
        db=db,
    )
    return ApprovalRequestListResponse(requests=requests, total=len(requests))


@router.get("/pending/count", response_model=PendingCountResponse)
async def get_pending_count(
    project_id: str | None = Query(None, description="Filter by project"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the count of pending approval requests."""
    tenant_id = user.get("tenant_id")
    count = await approval_service.get_pending_count(
        project_id=project_id,
        tenant_id=tenant_id,
        db=db,
    )
    return PendingCountResponse(pending_count=count)


@router.get("/{request_id}", response_model=ApprovalRequestResponse)
async def get_approval_request(
    request_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single approval request."""
    result = await approval_service.get_request(request_id, db=db)
    if result is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return ApprovalRequestResponse(**result)


@router.post("/{request_id}/review", response_model=ApprovalRequestResponse)
async def review_approval_request(
    request_id: str,
    decision: ApprovalDecision,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject an approval request."""
    if decision.status.value not in ("approved", "rejected"):
        raise HTTPException(
            status_code=400,
            detail="Decision must be 'approved' or 'rejected'",
        )

    reviewer = user.get("email", user.get("sub", "unknown"))
    result = await approval_service.review_request(
        request_id=request_id,
        decision=decision.status.value,
        reviewer=reviewer,
        reason=decision.reason,
        db=db,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return ApprovalRequestResponse(**result)
