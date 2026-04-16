"""Scan operations API routes — progress tracking, cancellation, pagination."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_db
from app.schemas.scan_performance import (
    PaginatedScanResults,
    ScanProgress,
    StartScanRequest,
)
from app.services.scan_coordinator import scan_coordinator

router = APIRouter(
    prefix="/api/governance/scans", tags=["scan-operations"]
)


@router.post("/{scan_type}/start", response_model=ScanProgress, status_code=202)
async def start_scan(
    scan_type: str,
    request: StartScanRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a governance scan with progress tracking.

    Returns 202 Accepted with initial scan progress.
    """
    tenant_id = user.get("tenant_id")
    progress = await scan_coordinator.start_scan(
        scan_type=scan_type,
        project_id=request.project_id,
        incremental=request.incremental,
        tenant_id=tenant_id,
    )
    return ScanProgress(**progress)


@router.get("/{scan_id}/progress", response_model=ScanProgress)
async def get_scan_progress(
    scan_id: str,
    user: dict = Depends(get_current_user),
):
    """Get progress of a running or completed scan."""
    progress = await scan_coordinator.get_progress(scan_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return ScanProgress(**progress)


@router.post("/{scan_id}/cancel", response_model=ScanProgress)
async def cancel_scan(
    scan_id: str,
    user: dict = Depends(get_current_user),
):
    """Cancel a running scan."""
    progress = await scan_coordinator.cancel_scan(scan_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return ScanProgress(**progress)


@router.get("/{scan_type}/results", response_model=PaginatedScanResults)
async def get_scan_results(
    scan_type: str,
    project_id: str = Query(..., description="Project ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Page size"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated scan results for a project."""
    result = await scan_coordinator.get_paginated_results(
        scan_type=scan_type,
        project_id=project_id,
        page=page,
        page_size=page_size,
        db=db,
    )
    return PaginatedScanResults(**result)
