"""Pydantic schemas for workload API."""

from datetime import datetime

from pydantic import BaseModel, Field


class WorkloadCreate(BaseModel):
    """Schema for creating a workload."""

    project_id: str
    name: str
    type: str = "other"
    source_platform: str = "other"
    cpu_cores: int | None = None
    memory_gb: float | None = None
    storage_gb: float | None = None
    os_type: str | None = None
    os_version: str | None = None
    criticality: str = "standard"
    compliance_requirements: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    migration_strategy: str = "unknown"
    notes: str | None = None


class WorkloadUpdate(BaseModel):
    """Schema for updating a workload — all fields optional."""

    name: str | None = None
    type: str | None = None
    source_platform: str | None = None
    cpu_cores: int | None = None
    memory_gb: float | None = None
    storage_gb: float | None = None
    os_type: str | None = None
    os_version: str | None = None
    criticality: str | None = None
    compliance_requirements: list[str] | None = None
    dependencies: list[str] | None = None
    migration_strategy: str | None = None
    notes: str | None = None


class WorkloadResponse(BaseModel):
    """Schema for returning a workload."""

    id: str
    project_id: str
    name: str
    type: str
    source_platform: str
    cpu_cores: int | None = None
    memory_gb: float | None = None
    storage_gb: float | None = None
    os_type: str | None = None
    os_version: str | None = None
    criticality: str
    compliance_requirements: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    migration_strategy: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkloadImportResult(BaseModel):
    """Schema for the result of a bulk workload import."""

    imported_count: int
    failed_count: int
    errors: list[str] = Field(default_factory=list)
    workloads: list[WorkloadResponse] = Field(default_factory=list)
