"""Pydantic schemas for the right-sizing recommendation API."""

from enum import Enum

from pydantic import BaseModel, Field

# ── Enums ────────────────────────────────────────────────────────────────────


class WorkloadType(str, Enum):
    WEB_APP = "web_app"
    DATABASE = "database"
    ANALYTICS = "analytics"
    BATCH = "batch"
    API = "api"
    MICROSERVICES = "microservices"


class CostPriority(str, Enum):
    COST_OPTIMIZED = "cost_optimized"
    BALANCED = "balanced"
    PERFORMANCE_FIRST = "performance_first"


class AvailabilitySLA(str, Enum):
    SLA_999 = "sla_999"
    SLA_9995 = "sla_9995"
    SLA_9999 = "sla_9999"


# ── Request models ───────────────────────────────────────────────────────────


class WorkloadProfile(BaseModel):
    """Input describing a workload for right-sizing."""

    workload_type: WorkloadType
    peak_concurrent_users: int = Field(100, ge=0, description="Peak concurrent users")
    availability: AvailabilitySLA = AvailabilitySLA.SLA_999
    cost_priority: CostPriority = CostPriority.BALANCED
    data_size_gb: float | None = Field(None, ge=0, description="Data volume in GB")


class CostEstimateRequest(BaseModel):
    """Request for estimating costs given a list of SKUs."""

    skus: list[str] = Field(..., min_length=1, description="List of Azure SKU strings")
    region: str = Field("eastus", description="Azure region for pricing")


# ── Recommendation models ────────────────────────────────────────────────────


class SKURecommendation(BaseModel):
    """A single right-sizing recommendation for one resource."""

    resource_type: str
    recommended_sku: str
    reasoning: str = ""
    monthly_cost_estimate: float = 0.0
    alternatives: list[str] = Field(default_factory=list)


class VMRecommendation(BaseModel):
    """VM-specific recommendation."""

    sku: str
    series: str
    vcpus: int
    memory_gb: float
    reasoning: str = ""
    monthly_cost_estimate: float = 0.0


class AppServiceRecommendation(BaseModel):
    """App Service plan recommendation."""

    sku: str
    tier: str
    reasoning: str = ""
    monthly_cost_estimate: float = 0.0


class DatabaseRecommendation(BaseModel):
    """Azure SQL Database recommendation."""

    sku: str
    tier: str
    max_size_gb: int
    reasoning: str = ""
    monthly_cost_estimate: float = 0.0


class StorageRecommendation(BaseModel):
    """Storage account recommendation."""

    sku: str
    redundancy: str
    tier: str
    reasoning: str = ""
    monthly_cost_estimate: float = 0.0


# ── Cost estimate models ─────────────────────────────────────────────────────


class CostLineItem(BaseModel):
    """A single line item in a cost breakdown."""

    resource_type: str
    sku: str
    monthly_cost: float


class CostEstimate(BaseModel):
    """Aggregated monthly cost estimate."""

    total_monthly: float
    breakdown: list[CostLineItem] = Field(default_factory=list)
    currency: str = "USD"


# ── Response models ──────────────────────────────────────────────────────────


class SizingResponse(BaseModel):
    """Full response from the sizing recommendation endpoint."""

    recommendations: list[SKURecommendation] = Field(default_factory=list)
    total_estimate: CostEstimate


class SKUListItem(BaseModel):
    """A single SKU entry for the catalog listing."""

    sku: str
    resource_type: str
    monthly_cost: float
    region: str = "eastus"


class SKUListResponse(BaseModel):
    """Response listing available SKUs with pricing."""

    skus: list[SKUListItem] = Field(default_factory=list)
    total: int = 0


class WorkloadTypeInfo(BaseModel):
    """Metadata about a supported workload type."""

    name: str
    description: str
    typical_resources: list[str] = Field(default_factory=list)


class WorkloadTypesResponse(BaseModel):
    """Response listing supported workload types."""

    workload_types: list[WorkloadTypeInfo] = Field(default_factory=list)
