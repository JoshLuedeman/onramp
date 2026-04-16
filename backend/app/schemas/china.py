"""Azure China (21Vianet) request / response schemas."""

from pydantic import BaseModel, Field

# ── Region Schemas ───────────────────────────────────────────────────────────


class ChinaRegionResponse(BaseModel):
    """Response schema for a single Azure China region."""

    name: str = Field(..., description="Region identifier")
    display_name: str = Field(..., description="Human-readable region name")
    paired_region: str = Field(..., description="DR-paired region name")
    geography: str = Field(..., description="Geographic area")
    available_zones: list[str] = Field(
        default_factory=list,
        description="Availability zones in this region",
    )


class ChinaRegionListResponse(BaseModel):
    """Response schema for listing all China regions."""

    regions: list[ChinaRegionResponse] = Field(
        default_factory=list,
        description="All Azure China regions",
    )
    total: int = Field(..., description="Total number of regions")


# ── Bicep Schemas ────────────────────────────────────────────────────────────


class ChinaBicepRequest(BaseModel):
    """Request schema for customizing a Bicep template for China."""

    bicep_content: str = Field(
        ..., description="Original Bicep template content"
    )
    region: str = Field(
        ..., description="Target Azure China region"
    )
    compliance_level: str = Field(
        default="mlps3",
        description="MLPS compliance level (mlps2, mlps3, mlps4)",
    )


class ChinaBicepResponse(BaseModel):
    """Response schema for a China-customized Bicep template."""

    customized_content: str = Field(
        ..., description="Bicep content customized for Azure China"
    )
    region: str = Field(..., description="Target region applied")
    compliance_level: str = Field(
        ..., description="MLPS level applied"
    )
    endpoints_replaced: int = Field(
        ..., description="Number of endpoint replacements made"
    )


# ── Questionnaire Schemas ────────────────────────────────────────────────────


class ChinaQuestionResponse(BaseModel):
    """Response schema for a single China questionnaire question."""

    id: str = Field(..., description="Question identifier")
    text: str = Field(..., description="Question text")
    description: str = Field(..., description="Detailed help text")
    type: str = Field(..., description="Input type (e.g. single_choice)")
    options: list[dict] = Field(
        default_factory=list, description="Available answer options"
    )
    required: bool = Field(..., description="Whether the question is required")
    category: str = Field(..., description="Question category")


class ChinaConstraintsRequest(BaseModel):
    """Request schema for applying China constraints to an architecture."""

    architecture: dict = Field(
        ..., description="Architecture dict to apply constraints to"
    )
    china_answers: dict = Field(
        ..., description="User's China-specific questionnaire answers"
    )


class ChinaConstraintsResponse(BaseModel):
    """Response schema after applying China constraints."""

    architecture: dict = Field(
        ..., description="Architecture with China constraints applied"
    )
    region: str = Field(..., description="Selected China region")
    compliance_level: str = Field(
        ..., description="Applied MLPS level"
    )
    cloud_environment: str = Field(
        default="china", description="Cloud environment identifier"
    )


# ── Data Residency Schemas ───────────────────────────────────────────────────


class DataResidencyRequirements(BaseModel):
    """Response schema for China data residency requirements."""

    jurisdiction: str = Field(
        ..., description="Legal jurisdiction for data"
    )
    data_boundary: str = Field(
        ..., description="Geographic data boundary"
    )
    cross_border_transfer: bool = Field(
        ..., description="Whether cross-border transfer is allowed"
    )
    regulations: list[str] = Field(
        default_factory=list,
        description="Applicable regulations",
    )
    requirements: list[str] = Field(
        default_factory=list,
        description="Specific data residency requirements",
    )
    operator: str = Field(
        ..., description="Cloud operator name"
    )
    operator_relationship: str = Field(
        ..., description="Relationship between Microsoft and operator"
    )


# ── ICP Schemas ──────────────────────────────────────────────────────────────


class ICPRequirements(BaseModel):
    """Response schema for ICP license requirements."""

    requires_icp: bool = Field(
        ..., description="Whether an ICP license is needed"
    )
    affected_resources: list[str] = Field(
        default_factory=list,
        description="Resource types requiring ICP",
    )
    resource_types_checked: int = Field(
        ..., description="Total resources checked"
    )
    guidance: str = Field(
        ..., description="Guidance text on ICP requirements"
    )
    icp_types: list[dict] = Field(
        default_factory=list,
        description="Types of ICP licenses",
    )
