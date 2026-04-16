"""Cloud configuration request / response schemas."""

from pydantic import BaseModel, Field


class CloudEnvironmentResponse(BaseModel):
    """Response schema for a single cloud environment."""

    name: str = Field(..., description="Environment enum value")
    display_name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Short description of the environment")
    available_regions: list[str] = Field(
        default_factory=list,
        description="Azure regions available in this environment",
    )


class CloudEndpointsResponse(BaseModel):
    """Response schema exposing all service endpoints for an environment."""

    resource_manager: str
    authentication: str
    portal: str
    graph: str
    storage_suffix: str
    sql_suffix: str
    keyvault_suffix: str
    ai_foundry: str | None = None


class EnvironmentValidationRequest(BaseModel):
    """Request schema for validating service support in an environment."""

    environment: str = Field(
        ...,
        description="Cloud environment name (commercial, government, china)",
    )
    required_services: list[str] = Field(
        default_factory=list,
        description="List of Azure service names to validate",
    )


class EnvironmentValidationResponse(BaseModel):
    """Response schema for environment validation results."""

    supported: bool = Field(
        ...,
        description="True when all required services are available",
    )
    missing_services: list[str] = Field(
        default_factory=list,
        description="Services not available in the environment",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Advisory notes about limited availability",
    )
