"""Right-sizing recommendation API routes."""

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.schemas.sizing import (
    CostEstimate,
    CostEstimateRequest,
    SizingResponse,
    SKUListItem,
    SKUListResponse,
    WorkloadProfile,
    WorkloadTypeInfo,
    WorkloadTypesResponse,
)
from app.services.pricing import pricing_service
from app.services.sizing import sizing_engine

router = APIRouter(prefix="/api/sizing", tags=["sizing"])


# ── Workload types ───────────────────────────────────────────────────────────

WORKLOAD_TYPE_INFO: list[WorkloadTypeInfo] = [
    WorkloadTypeInfo(
        name="web_app",
        description="Web applications and frontends",
        typical_resources=["App Service", "VM", "SQL Database", "Storage"],
    ),
    WorkloadTypeInfo(
        name="database",
        description="Database-centric workloads",
        typical_resources=["SQL Database", "VM (memory-optimized)", "Storage"],
    ),
    WorkloadTypeInfo(
        name="analytics",
        description="Data analytics and processing",
        typical_resources=["VM (memory/GPU)", "SQL Database", "Storage"],
    ),
    WorkloadTypeInfo(
        name="batch",
        description="Batch processing and scheduled jobs",
        typical_resources=["VM (compute-optimized)", "Storage", "SQL Database"],
    ),
    WorkloadTypeInfo(
        name="api",
        description="REST/GraphQL API services",
        typical_resources=["App Service", "VM", "SQL Database", "Storage"],
    ),
    WorkloadTypeInfo(
        name="microservices",
        description="Microservice-based architectures",
        typical_resources=["Container Apps", "VM", "SQL Database", "Storage"],
    ),
]


# ── Routes ───────────────────────────────────────────────────────────────────


@router.post("/recommend", response_model=SizingResponse)
async def recommend_skus(
    profile: WorkloadProfile,
    user: dict = Depends(get_current_user),
):
    """Get right-sizing SKU recommendations for a workload profile."""
    recommendations = sizing_engine.recommend_skus(profile)
    total_estimate = sizing_engine.estimate_monthly_cost(recommendations)
    return SizingResponse(
        recommendations=recommendations,
        total_estimate=total_estimate,
    )


@router.post("/estimate", response_model=CostEstimate)
async def estimate_costs(
    payload: CostEstimateRequest,
    user: dict = Depends(get_current_user),
):
    """Get a cost estimate for a set of Azure SKUs."""
    recs = [{"recommended_sku": sku, "resource_type": "unknown"} for sku in payload.skus]
    estimate = pricing_service.estimate_total(recs, region=payload.region)
    return estimate


@router.get("/skus", response_model=SKUListResponse)
async def list_skus(
    region: str = Query("eastus", description="Azure region for pricing"),
    user: dict = Depends(get_current_user),
):
    """List all available SKUs with embedded pricing."""
    items = pricing_service.list_all_skus(region)
    sku_list = [SKUListItem(**item) for item in items]
    return SKUListResponse(skus=sku_list, total=len(sku_list))


@router.get("/workload-types", response_model=WorkloadTypesResponse)
async def list_workload_types(
    user: dict = Depends(get_current_user),
):
    """List supported workload types with descriptions."""
    return WorkloadTypesResponse(workload_types=WORKLOAD_TYPE_INFO)
