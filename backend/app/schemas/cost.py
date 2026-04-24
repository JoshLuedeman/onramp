"""Pydantic schemas for the cost management API."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# ── Enums ────────────────────────────────────────────────────────────────────


class AnomalySeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AnomalyType(str, Enum):
    SPIKE = "spike"
    UNUSUAL_SERVICE = "unusual_service"
    NEW_RESOURCE = "new_resource"


class CostGranularity(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# ── Cost summary ─────────────────────────────────────────────────────────────


class ServiceCost(BaseModel):
    """Cost breakdown for a single Azure service."""

    service_name: str
    cost: float
    percentage: float


class ResourceGroupCost(BaseModel):
    """Cost breakdown for a single resource group."""

    resource_group: str
    cost: float
    percentage: float


class CostSummaryResponse(BaseModel):
    """Aggregated cost summary for a subscription."""

    project_id: str
    subscription_id: str
    period_start: datetime
    period_end: datetime
    total_cost: float
    currency: str = "USD"
    cost_by_service: list[ServiceCost] = Field(default_factory=list)
    cost_by_resource_group: list[ResourceGroupCost] = Field(default_factory=list)


# ── Cost trend ───────────────────────────────────────────────────────────────


class CostDataPoint(BaseModel):
    """A single data point in a cost trend."""

    date: str
    cost: float
    currency: str = "USD"


class CostTrendResponse(BaseModel):
    """Cost trend over time."""

    project_id: str
    subscription_id: str
    granularity: str
    days: int
    data_points: list[CostDataPoint] = Field(default_factory=list)
    total_cost: float = 0.0
    average_daily_cost: float = 0.0


# ── Budget ───────────────────────────────────────────────────────────────────


class CostBudgetCreate(BaseModel):
    """Request to create or update a cost budget."""

    project_id: str = Field(..., min_length=1)
    budget_name: str = Field(..., min_length=1, max_length=255)
    budget_amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    threshold_percentage: float = Field(default=80.0, ge=0, le=100)
    alert_enabled: bool = True


class CostBudgetUpdate(BaseModel):
    """Request to update an existing cost budget."""

    budget_name: str | None = None
    budget_amount: float | None = None
    currency: str | None = None
    threshold_percentage: float | None = None
    alert_enabled: bool | None = None


class BudgetStatusResponse(BaseModel):
    """Budget status with utilisation metrics."""

    project_id: str
    budget_name: str
    budget_amount: float
    current_spend: float
    currency: str = "USD"
    utilization_percentage: float
    threshold_percentage: float = 80.0
    alert_enabled: bool = True
    is_over_threshold: bool = False
    is_over_budget: bool = False


# ── Anomaly ──────────────────────────────────────────────────────────────────


class CostAnomalyResponse(BaseModel):
    """A detected cost anomaly."""

    id: str
    project_id: str
    cost_snapshot_id: str
    anomaly_type: str
    description: str
    previous_cost: float
    current_cost: float
    percentage_change: float
    severity: str
    detected_at: datetime

    model_config = {"from_attributes": True}


class CostAnomalyList(BaseModel):
    """List of cost anomalies."""

    anomalies: list[CostAnomalyResponse] = Field(default_factory=list)
    total: int = 0


# ── Scan trigger ─────────────────────────────────────────────────────────────


class CostScanResponse(BaseModel):
    """Response from triggering a cost analysis scan."""

    status: str
    message: str
    project_id: str
    scan_id: str | None = None
