"""SKU database API routes."""

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.services.sku_database import sku_database_service

router = APIRouter(prefix="/api/skus", tags=["skus"])


class SkuRecommendRequest(BaseModel):
    workload_type: str
    requirements: dict = Field(default_factory=dict)


class SkuCompareRequest(BaseModel):
    sku_ids: list[str]


class SkuValidateRequest(BaseModel):
    sku: str
    region: str
    cloud_env: str = "commercial"


@router.get("/compute")
async def list_compute_skus(
    family: str | None = Query(None, description="Filter by VM family"),
    min_vcpus: int | None = Query(None, description="Minimum vCPUs"),
    min_ram: int | None = Query(None, description="Minimum RAM in GB"),
    gpu: bool | None = Query(None, description="Require GPU"),
    price_tier: str | None = Query(None, description="Price tier filter"),
):
    """List compute SKUs with optional filters."""
    filters: dict = {}
    if family:
        filters["family"] = family
    if min_vcpus is not None:
        filters["min_vcpus"] = min_vcpus
    if min_ram is not None:
        filters["min_ram"] = min_ram
    if gpu:
        filters["gpu"] = True
    if price_tier:
        filters["price_tier"] = price_tier

    skus = sku_database_service.get_compute_skus(filters if filters else None)
    return {"skus": skus, "count": len(skus)}


@router.get("/storage")
async def list_storage_skus(
    tier: str | None = Query(None, description="Filter by storage tier"),
    media: str | None = Query(None, description="Filter by media type (hdd/ssd)"),
):
    """List storage SKUs with optional filters."""
    filters: dict = {}
    if tier:
        filters["tier"] = tier
    if media:
        filters["media"] = media

    skus = sku_database_service.get_storage_skus(filters if filters else None)
    return {"skus": skus, "count": len(skus)}


@router.get("/database")
async def list_database_skus(
    service: str | None = Query(None, description="Filter by DB service"),
    tier: str | None = Query(None, description="Filter by tier"),
):
    """List database SKUs with optional filters."""
    filters: dict = {}
    if service:
        filters["service"] = service
    if tier:
        filters["tier"] = tier

    skus = sku_database_service.get_database_skus(filters if filters else None)
    return {"skus": skus, "count": len(skus)}


@router.get("/networking")
async def list_networking_skus(
    service: str | None = Query(None, description="Filter by networking service"),
    tier: str | None = Query(None, description="Filter by tier"),
):
    """List networking SKUs with optional filters."""
    filters: dict = {}
    if service:
        filters["service"] = service
    if tier:
        filters["tier"] = tier

    skus = sku_database_service.get_networking_skus(filters if filters else None)
    return {"skus": skus, "count": len(skus)}


@router.post("/recommend")
async def recommend_sku(body: SkuRecommendRequest):
    """Recommend the best SKU for a workload type and requirements."""
    result = sku_database_service.recommend_sku(body.workload_type, body.requirements)
    return result


@router.post("/compare")
async def compare_skus(body: SkuCompareRequest):
    """Compare SKUs side by side."""
    skus = sku_database_service.get_sku_comparison(body.sku_ids)
    return {"skus": skus}


@router.post("/validate")
async def validate_sku_availability(body: SkuValidateRequest):
    """Validate SKU availability in a region and cloud environment."""
    return sku_database_service.validate_sku_availability(
        body.sku, body.region, body.cloud_env
    )
