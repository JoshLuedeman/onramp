"""Pydantic schemas for IaC provider and API version pinning."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProviderVersion(BaseModel):
    """A pinned IaC provider or SDK version."""

    name: str = Field(..., description="Provider or SDK package name")
    source: str = Field(default="", description="Registry source (e.g. hashicorp/azurerm)")
    version_constraint: str = Field(
        ..., description="Version constraint (e.g. ~> 3.100)"
    )
    release_date: str = Field(
        ..., description="ISO-8601 date of the pinned release (YYYY-MM-DD)"
    )
    notes: str = Field(default="", description="Optional notes about this version")


class ApiVersion(BaseModel):
    """A pinned ARM/Bicep API version for a specific resource type."""

    resource_type: str = Field(
        ..., description="Azure resource type (e.g. Microsoft.Network/virtualNetworks)"
    )
    api_version: str = Field(
        ..., description="API version date string (e.g. 2023-09-01)"
    )
    release_date: str = Field(
        ..., description="ISO-8601 date when this API version was released"
    )
    notes: str = Field(default="", description="Optional notes")


class TerraformVersionsResponse(BaseModel):
    """Response for recommended Terraform provider versions."""

    terraform_version: str = Field(
        ..., description="Minimum required Terraform CLI version"
    )
    providers: list[ProviderVersion] = Field(default_factory=list)


class PulumiVersionsResponse(BaseModel):
    """Response for recommended Pulumi SDK versions."""

    language: str = Field(..., description="Target language (typescript or python)")
    packages: list[ProviderVersion] = Field(default_factory=list)


class ArmVersionsResponse(BaseModel):
    """Response for recommended ARM API versions."""

    schema_version: str = Field(
        ..., description="ARM deployment template schema version"
    )
    content_version: str = Field(default="1.0.0.0")
    api_versions: list[ApiVersion] = Field(default_factory=list)


class BicepVersionsResponse(BaseModel):
    """Response for recommended Bicep API versions."""

    api_versions: list[ApiVersion] = Field(default_factory=list)


class VersionFreshnessItem(BaseModel):
    """Freshness status for a single version entry."""

    name: str = Field(..., description="Provider, SDK, or resource-type name")
    version: str = Field(..., description="Pinned version or constraint")
    release_date: str = Field(..., description="ISO-8601 release date")
    age_days: int = Field(..., description="Days since release_date")
    is_stale: bool = Field(
        ..., description="True if older than the staleness threshold"
    )


class VersionReport(BaseModel):
    """Full version freshness report across all IaC formats."""

    staleness_threshold_days: int = Field(
        default=180, description="Versions older than this are flagged stale"
    )
    terraform: list[VersionFreshnessItem] = Field(default_factory=list)
    pulumi_typescript: list[VersionFreshnessItem] = Field(default_factory=list)
    pulumi_python: list[VersionFreshnessItem] = Field(default_factory=list)
    arm: list[VersionFreshnessItem] = Field(default_factory=list)
    bicep: list[VersionFreshnessItem] = Field(default_factory=list)
    total_entries: int = Field(default=0)
    stale_count: int = Field(default=0)
