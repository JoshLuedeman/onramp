"""MSP (Managed Service Provider) dashboard schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class TenantOverview(BaseModel):
    """Summary of a single managed tenant."""

    tenant_id: str
    name: str
    status: str = Field(
        ..., description="active | inactive | warning"
    )
    last_activity: datetime | None = None
    compliance_score: float = Field(
        ..., ge=0.0, le=100.0
    )
    project_count: int = Field(..., ge=0)
    deployment_count: int = Field(..., ge=0)
    active_deployments: int = Field(..., ge=0)


class MSPOverviewResponse(BaseModel):
    """Aggregated overview across all managed tenants."""

    tenants: list[TenantOverview]
    total_tenants: int = Field(..., ge=0)
    total_projects: int = Field(..., ge=0)
    avg_compliance_score: float = Field(
        ..., ge=0.0, le=100.0
    )


class DeploymentSummary(BaseModel):
    """Brief deployment record for health responses."""

    id: str
    project_name: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TenantHealthResponse(BaseModel):
    """Detailed health information for a single tenant."""

    tenant_id: str
    name: str
    compliance_score: float = Field(
        ..., ge=0.0, le=100.0
    )
    compliance_status: str = Field(
        ..., description="passing | warning | failing"
    )
    recent_deployments: list[DeploymentSummary] = []
    active_alerts: int = Field(..., ge=0)
    resource_count: int = Field(..., ge=0)


class TenantComplianceScore(BaseModel):
    """Per-tenant compliance score entry."""

    tenant_id: str
    name: str
    score: float = Field(..., ge=0.0, le=100.0)
    status: str = Field(
        ..., description="passing | warning | failing"
    )


class ComplianceSummaryResponse(BaseModel):
    """Aggregated compliance scores across all tenants."""

    total_tenants: int = Field(..., ge=0)
    passing: int = Field(..., ge=0)
    warning: int = Field(..., ge=0)
    failing: int = Field(..., ge=0)
    scores_by_tenant: list[TenantComplianceScore] = []
