"""Pydantic schemas for scan performance and progress tracking."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ScanProgressStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class ScanProgress(BaseModel):
    """Progress report for a running or completed scan."""

    scan_id: str
    scan_type: str = ""
    total_resources: int = 0
    scanned_resources: int = 0
    percentage: float = 0.0
    status: str = ScanProgressStatus.RUNNING.value
    started_at: datetime | None = None
    updated_at: datetime | None = None
    project_id: str | None = None
    error_message: str | None = None


class PaginatedScanResults(BaseModel):
    """Paginated scan results container."""

    items: list[dict] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50
    has_more: bool = False


class StartScanRequest(BaseModel):
    """Request to start a governance scan."""

    project_id: str
    incremental: bool = False


class ScanTypeEnum(str, Enum):
    DRIFT = "drift"
    POLICY = "policy"
    RBAC = "rbac"
    TAGGING = "tagging"
    COST = "cost"
