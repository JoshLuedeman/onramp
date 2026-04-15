"""Pydantic schemas for workload-to-subscription mapping."""

from pydantic import BaseModel, Field


class WorkloadMapping(BaseModel):
    """Represents a recommended mapping of a workload to a target subscription."""

    workload_id: str
    workload_name: str
    recommended_subscription_id: str
    recommended_subscription_name: str
    reasoning: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)


class MappingRequest(BaseModel):
    """Request body for generating workload-to-subscription mappings."""

    project_id: str
    architecture_id: str = ""
    use_ai: bool = True


class MappingResponse(BaseModel):
    """Response containing generated mappings and validation warnings."""

    mappings: list[WorkloadMapping] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MappingOverride(BaseModel):
    """Manual override of an AI-generated mapping recommendation."""

    target_subscription_id: str
    target_subscription_name: str = ""
    reasoning: str = "Manual override"
