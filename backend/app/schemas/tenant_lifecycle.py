"""Schemas for tenant lifecycle management (provision / settings / offboard)."""

from datetime import datetime

from pydantic import BaseModel, Field


class ResourceLimits(BaseModel):
    """Configurable resource caps for a tenant."""

    max_projects: int = Field(default=50, ge=1, le=10000)
    max_users: int = Field(default=100, ge=1, le=100000)
    ai_budget: float = Field(
        default=1000.0,
        ge=0,
        description="Monthly AI-token budget in USD",
    )


class TenantProvisionRequest(BaseModel):
    """Payload for provisioning a brand-new tenant."""

    name: str = Field(..., min_length=1, max_length=255)
    admin_email: str = Field(
        ..., min_length=5, max_length=255,
        description="E-mail of the initial tenant administrator",
    )
    resource_limits: ResourceLimits = Field(default_factory=ResourceLimits)


class TenantSettingsResponse(BaseModel):
    """Read-only view of a tenant's operational settings."""

    tenant_id: str
    name: str
    is_active: bool
    resource_limits: ResourceLimits
    feature_flags: dict[str, bool] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantSettingsUpdate(BaseModel):
    """Mutable subset of tenant settings."""

    resource_limits: ResourceLimits | None = None
    feature_flags: dict[str, bool] | None = None


class TenantOffboardRequest(BaseModel):
    """Payload for offboarding (deactivating) a tenant."""

    archive: bool = Field(
        default=True,
        description="Whether to archive tenant data before deactivation",
    )
    retention_days: int = Field(
        default=90, ge=0, le=3650,
        description="Days to retain archived data",
    )


class TenantOffboardResponse(BaseModel):
    """Confirmation returned after offboarding."""

    tenant_id: str
    is_active: bool
    archive: bool
    retention_days: int
    message: str
