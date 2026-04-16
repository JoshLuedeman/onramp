"""Pydantic schemas for Azure Government API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── Region Schemas ───────────────────────────────────────────────────────────


class GovernmentRegionResponse(BaseModel):
    """A single Azure Government region."""

    name: str = Field(..., description="Region identifier (e.g. usgovvirginia)")
    display_name: str = Field(..., description="Human-readable region name")
    paired_region: str = Field(..., description="DR-paired region name")
    geography: str = Field(..., description="Geography grouping")
    available_zones: list[str] = Field(
        default_factory=list, description="Availability zones"
    )
    restricted: bool = Field(
        False, description="True for DoD-restricted regions"
    )


class GovernmentRegionListResponse(BaseModel):
    """List of Azure Government regions."""

    regions: list[GovernmentRegionResponse] = Field(default_factory=list)
    total: int = Field(0, description="Total number of regions")


# ── Bicep Schemas ────────────────────────────────────────────────────────────


class GovernmentBicepRequest(BaseModel):
    """Request to customize a Bicep template for Government cloud."""

    bicep_content: str = Field(
        ..., description="Raw Bicep template to customize"
    )
    region: str = Field(..., description="Target Government region")
    compliance_level: str = Field(
        "high", description="FedRAMP level: high, moderate, or low"
    )


class GovernmentBicepResponse(BaseModel):
    """Response from Bicep Government customization."""

    customized_content: str = Field(
        ..., description="Customized Bicep template"
    )
    changes_applied: list[str] = Field(
        default_factory=list,
        description="List of changes applied to the template",
    )


# ── Questionnaire Schemas ───────────────────────────────────────────────────


class GovernmentQuestionResponse(BaseModel):
    """A single Government-specific question."""

    id: str = Field(..., description="Question identifier")
    text: str = Field(..., description="Question text")
    type: str = Field(..., description="Input type (single_choice, etc.)")
    options: list[dict] = Field(default_factory=list, description="Answer options")
    required: bool = Field(True, description="Whether answer is required")
    category: str = Field("government", description="Question category")
    help_text: str = Field("", description="Help text for the question")


class GovernmentConstraintsRequest(BaseModel):
    """Request to apply Government constraints to an architecture."""

    architecture: dict = Field(
        ..., description="Base architecture to constrain"
    )
    gov_answers: dict = Field(
        ..., description="Government questionnaire answers"
    )


class GovernmentConstraintsResponse(BaseModel):
    """Result of applying Government constraints."""

    architecture: dict = Field(
        ..., description="Architecture with Government constraints applied"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Warnings generated during constraint application",
    )
