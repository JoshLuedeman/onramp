"""Tenant schemas for multi-tenant CRUD operations."""

from datetime import datetime

from pydantic import BaseModel, Field


class TenantBase(BaseModel):
    """Base schema with shared tenant fields."""

    name: str = Field(..., min_length=1, max_length=255)
    azure_tenant_id: str | None = Field(default=None, max_length=36)


class TenantCreate(TenantBase):
    """Schema for creating a new tenant."""


class TenantUpdate(BaseModel):
    """Schema for updating an existing tenant (all fields optional)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None


class TenantResponse(TenantBase):
    """Schema for tenant API responses."""

    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TenantListResponse(BaseModel):
    """Schema for paginated tenant list responses."""

    tenants: list[TenantResponse]
    total: int
