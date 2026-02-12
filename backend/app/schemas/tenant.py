"""Tenant schemas."""

from pydantic import BaseModel
from datetime import datetime


class TenantBase(BaseModel):
    name: str
    azure_tenant_id: str | None = None


class TenantCreate(TenantBase):
    pass


class TenantResponse(TenantBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
