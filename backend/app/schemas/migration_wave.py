"""Pydantic schemas for migration wave planning."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class WaveGenerateRequest(BaseModel):
    """Request to auto-generate a migration wave plan."""

    project_id: str
    strategy: str = "complexity_first"
    max_wave_size: int | None = None
    plan_name: str = "Migration Plan"


class WaveWorkloadResponse(BaseModel):
    """A workload within a wave."""

    id: str
    workload_id: str
    name: str
    type: str
    criticality: str
    migration_strategy: str
    position: int
    dependencies: list[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class WaveResponse(BaseModel):
    """A single migration wave."""

    id: str
    name: str
    order: int
    status: str
    notes: str | None = None
    workloads: list[WaveWorkloadResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WaveUpdateRequest(BaseModel):
    """Request to update a wave."""

    name: str | None = None
    status: str | None = None
    notes: str | None = None


class MoveWorkloadRequest(BaseModel):
    """Request to move a workload between waves."""

    workload_id: str
    target_wave_id: str
    position: int = 0


class ValidationWarning(BaseModel):
    """A warning about the wave plan."""

    type: str
    message: str
    wave_id: str | None = None
    workload_id: str | None = None


class WavePlanResponse(BaseModel):
    """Full wave plan with validation."""

    id: str
    project_id: str
    name: str
    strategy: str
    is_active: bool
    waves: list[WaveResponse] = Field(default_factory=list)
    warnings: list[ValidationWarning] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WaveExportRequest(BaseModel):
    """Request to export wave plan."""

    project_id: str
    format: Literal["csv", "markdown"] = "markdown"


class WaveValidateRequest(BaseModel):
    """Request to validate a wave plan."""

    project_id: str
