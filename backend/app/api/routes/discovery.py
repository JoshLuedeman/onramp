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
from app.schemas.gap_analysis import (
    BrownfieldContext,
    GapAnalysisRequest,
    GapAnalysisResponse,
)
from app.services.discovery_service import discovery_service
from app.services.gap_analyzer import gap_analyzer

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

    # Validate project belongs to caller's tenant (skip in dev mode without DB)
    if db is not None:
        from sqlalchemy import select

        from app.models.project import Project

        result = await db.execute(
            select(Project).where(
                Project.id == request.project_id,
                Project.tenant_id == tenant_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Project not found")

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


@router.post(
    "/scan/{scan_id}/analyze", response_model=GapAnalysisResponse,
)
async def analyze_scan_gaps(
    scan_id: str,
    request: GapAnalysisRequest | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run gap analysis on discovery scan results.

    Compares discovered Azure environment against CAF best practices.
    Returns categorized findings with severity and remediation guidance.
    """
    # Load scan with tenant isolation
    scan = await discovery_service.get_scan(scan_id, db)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    user_tenant = user.get("tenant_id", "dev-tenant")
    if scan.get("tenant_id") and scan["tenant_id"] != user_tenant:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail="Scan must be completed before analysis",
        )

    # Load both summary and resources
    summary = scan.get("results") or {}
    resources_data = await discovery_service.get_scan_resources(
        scan_id, db,
    )

    result = gap_analyzer.analyze(summary, resources_data)

    return GapAnalysisResponse(
        scan_id=scan_id,
        total_findings=result["total_findings"],
        critical_count=result["critical_count"],
        high_count=result["high_count"],
        medium_count=result["medium_count"],
        low_count=result["low_count"],
        findings=result["findings"],
        areas_checked=result["areas_checked"],
        areas_skipped=result["areas_skipped"],
    )


@router.get(
    "/scan/{scan_id}/brownfield-context",
    response_model=BrownfieldContext,
)
async def get_brownfield_context(
    scan_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get brownfield questionnaire context from discovery scan.

    Returns discovered answer suggestions and gap summary to drive
    the adaptive brownfield questionnaire flow.
    """
    scan = await discovery_service.get_scan(scan_id, db)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    user_tenant = user.get("tenant_id", "dev-tenant")
    if scan.get("tenant_id") and scan["tenant_id"] != user_tenant:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail="Scan must be completed before context generation",
        )

    summary = scan.get("results") or {}
    resources_data = await discovery_service.get_scan_resources(
        scan_id, db,
    )

    context = gap_analyzer.get_brownfield_context(summary, resources_data)
    context["scan_id"] = scan_id

    return context
