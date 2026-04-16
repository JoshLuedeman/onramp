"""Pydantic schemas for governance task execution API."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    DRIFT_DETECTION = "drift_detection"
    POLICY_COMPLIANCE = "policy_compliance"
    RBAC_HEALTH = "rbac_health"
    TAGGING_COMPLIANCE = "tagging_compliance"


class TaskExecutionResponse(BaseModel):
    """Response for a single task execution."""

    id: str
    task_type: str
    tenant_id: str | None = None
    project_id: str | None = None
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result_summary: dict | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    """Paginated list of task executions."""

    tasks: list[TaskExecutionResponse]
    total: int


class TaskScheduleRequest(BaseModel):
    """Request to manually trigger a governance scan task."""

    project_id: str | None = Field(
        default=None,
        description="Optional project to scope the scan to",
    )
    tenant_id: str | None = Field(
        default=None,
        description="Optional tenant to scope the scan to",
    )
