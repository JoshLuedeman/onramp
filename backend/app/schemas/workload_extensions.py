"""Pydantic schemas for workload extensions, SKU database and architecture validation."""

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Workload extensions
# ---------------------------------------------------------------------------


class WorkloadExtensionResponse(BaseModel):
    """Single workload extension metadata."""

    workload_type: str
    display_name: str
    description: str
    questions: list[dict] = Field(default_factory=list)
    best_practices: list[dict] = Field(default_factory=list)


class WorkloadExtensionListResponse(BaseModel):
    """List of registered workload extensions."""

    extensions: list[dict] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# SKU database
# ---------------------------------------------------------------------------


class SkuResponse(BaseModel):
    """Single SKU record."""

    id: str
    name: str
    family: str | None = None
    price_tier: str | None = None
    use_case: str | None = None


class SkuListResponse(BaseModel):
    """List of SKU records."""

    skus: list[dict] = Field(default_factory=list)
    count: int = 0


class SkuComparisonResponse(BaseModel):
    """Side-by-side SKU comparison."""

    skus: list[dict] = Field(default_factory=list)


class SkuRecommendRequest(BaseModel):
    """Request body for SKU recommendation."""

    workload_type: str
    requirements: dict = Field(default_factory=dict)


class SkuRecommendResponse(BaseModel):
    """SKU recommendation result."""

    recommended_sku: dict
    reason: str
    alternatives: list[dict] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Architecture validation
# ---------------------------------------------------------------------------


class ArchitectureValidationRequest(BaseModel):
    """Request body for architecture validation."""

    architecture: dict
    workload_type: str | None = None
    cloud_env: str = "commercial"
    region: str = "eastus"
    framework: str | None = None


class ArchitectureValidationResponse(BaseModel):
    """Architecture validation result."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class ValidationRuleResponse(BaseModel):
    """Single validation rule."""

    id: str
    category: str
    description: str
    severity: str
