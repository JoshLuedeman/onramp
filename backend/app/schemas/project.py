"""Project schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    QUESTIONNAIRE_COMPLETE = "questionnaire_complete"
    ARCHITECTURE_GENERATED = "architecture_generated"
    COMPLIANCE_SCORED = "compliance_scored"
    BICEP_READY = "bicep_ready"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"


class ProjectBase(BaseModel):
    name: str
    description: str | None = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: ProjectStatus | None = None


class ProjectResponse(ProjectBase):
    id: str
    status: str
    tenant_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectStatsResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    avg_compliance_score: float | None = None
    deployment_success_rate: float | None = None
    recent_projects: list[ProjectResponse] = Field(default_factory=list)
