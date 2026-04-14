"""Pydantic schemas for the discovery API."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ScanStatus(str, Enum):
    PENDING = "pending"
    SCANNING = "scanning"
    COMPLETED = "completed"
    FAILED = "failed"


class ResourceCategory(str, Enum):
    RESOURCE = "resource"
    POLICY = "policy"
    RBAC = "rbac"
    NETWORK = "network"


class DiscoveryScanCreate(BaseModel):
    """Request to start a discovery scan."""

    project_id: str
    subscription_id: str
    scan_config: dict | None = Field(
        default=None,
        description="Optional scan configuration (scope filters, include/exclude types)",
    )


class DiscoveryScanResponse(BaseModel):
    """Response for a discovery scan."""

    id: str
    project_id: str
    subscription_id: str
    status: str
    scan_config: dict | None = None
    results: dict | None = None
    error_message: str | None = None
    resource_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DiscoveredResourceResponse(BaseModel):
    """Response for a single discovered resource."""

    id: str
    scan_id: str
    category: str
    resource_type: str
    resource_id: str
    resource_group: str | None = None
    name: str
    properties: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DiscoveredResourceList(BaseModel):
    """Paginated list of discovered resources."""

    resources: list[DiscoveredResourceResponse]
    total: int
    scan_id: str
