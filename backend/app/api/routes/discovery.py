"""Discovery API routes — scan Azure subscriptions for existing resources."""

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_db
from app.schemas.discovery import (
    DiscoveredResourceList,
    DiscoveryScanCreate,
    DiscoveryScanResponse,
)
from app.services.discovery_service import discovery_service

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


@router.post("/scan", response_model=DiscoveryScanResponse)
async def start_discovery_scan(
    request: DiscoveryScanCreate,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a discovery scan of an Azure subscription.

    Creates a scan record and runs the actual scanning in the background.
    Returns immediately with the scan ID and status.
    """
    tenant_id = user.get("tenant_id", "dev-tenant")

    result = await discovery_service.start_scan(
        project_id=request.project_id,
        tenant_id=tenant_id,
        subscription_id=request.subscription_id,
        scan_config=request.scan_config,
    )

    now = datetime.now(timezone.utc)

    # If we got immediate results (dev mode without DB), return them
    if result.get("status") == "completed":
        return DiscoveryScanResponse(
            id=result["id"],
            project_id=result["project_id"],
            subscription_id=result["subscription_id"],
            status="completed",
            results=result.get("results"),
            resource_count=result.get("resource_count", 0),
            created_at=now,
            updated_at=now,
        )

    # Enqueue background scan execution
    background_tasks.add_task(discovery_service.execute_scan, result["id"])

    return DiscoveryScanResponse(
        id=result["id"],
        project_id=result["project_id"],
        subscription_id=result["subscription_id"],
        status="pending",
        created_at=now,
        updated_at=now,
    )


@router.get("/scan/{scan_id}", response_model=DiscoveryScanResponse)
async def get_scan_status(
    scan_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the status and results of a discovery scan."""
    scan = await discovery_service.get_scan(scan_id, db)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Tenant isolation: verify the scan belongs to the user's tenant
    user_tenant = user.get("tenant_id", "dev-tenant")
    if scan.get("tenant_id") and scan["tenant_id"] != user_tenant:
        raise HTTPException(status_code=404, detail="Scan not found")

    return scan


@router.get("/scan/{scan_id}/resources", response_model=DiscoveredResourceList)
async def get_scan_resources(
    scan_id: str,
    category: str | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the discovered resources for a scan, optionally filtered by category."""
    # Verify scan exists and belongs to user's tenant
    scan = await discovery_service.get_scan(scan_id, db)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    user_tenant = user.get("tenant_id", "dev-tenant")
    if scan.get("tenant_id") and scan["tenant_id"] != user_tenant:
        raise HTTPException(status_code=404, detail="Scan not found")

    resources = await discovery_service.get_scan_resources(scan_id, db, category)

    return DiscoveredResourceList(
        resources=resources,
        total=len(resources),
        scan_id=scan_id,
    )
