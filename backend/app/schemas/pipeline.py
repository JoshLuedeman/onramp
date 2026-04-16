"""Pydantic schemas for CI/CD pipeline generation request/response models."""

from enum import Enum

from pydantic import BaseModel, Field


class PipelineFormat(str, Enum):
    """Supported CI/CD pipeline formats."""

    github_actions = "github_actions"
    azure_devops = "azure_devops"


class IaCFormat(str, Enum):
    """Supported Infrastructure-as-Code formats."""

    bicep = "bicep"
    terraform = "terraform"
    arm = "arm"
    pulumi = "pulumi"


class GeneratePipelineRequest(BaseModel):
    """Request body for pipeline generation."""

    architecture: dict = Field(..., description="Architecture definition JSON")
    iac_format: IaCFormat = Field(..., description="IaC format to generate pipeline for")
    pipeline_format: PipelineFormat = Field(
        default=PipelineFormat.github_actions,
        description="CI/CD pipeline format",
    )
    environments: list[str] = Field(
        default_factory=lambda: ["dev", "staging", "prod"],
        description="Target deployment environments",
    )
    include_approval_gates: bool = Field(
        default=True, description="Include approval gates between environments"
    )
    project_name: str = Field(
        default="onramp-landing-zone", description="Project name for workflow naming"
    )
    service_connection: str = Field(
        default="azure-service-connection",
        description="Azure DevOps service connection name (Azure DevOps only)",
    )
    variable_group: str = Field(
        default="landing-zone-secrets",
        description="Variable group name for secrets (Azure DevOps only)",
    )


class PipelineFile(BaseModel):
    """A single generated pipeline file."""

    name: str = Field(..., description="File name (e.g. deploy-bicep.yml)")
    content: str = Field(..., description="Pipeline YAML content")
    size_bytes: int = Field(..., description="Content size in bytes")
    environment: str = Field(default="all", description="Target environment for this file")


class GeneratePipelineResponse(BaseModel):
    """Response from pipeline generation."""

    files: list[PipelineFile] = Field(default_factory=list)
    total_files: int = Field(default=0)
    iac_format: str = Field(default="")
    pipeline_format: str = Field(default="")
    environments: list[str] = Field(default_factory=list)


class PipelineTemplateInfo(BaseModel):
    """Metadata for an available pipeline template."""

    name: str = Field(..., description="Template name")
    description: str = Field(default="", description="Template description")
    iac_format: str = Field(..., description="IaC format this template targets")
    pipeline_format: str = Field(..., description="CI/CD platform this template targets")


class PipelineTemplateListResponse(BaseModel):
    """Response for listing available pipeline templates."""

    templates: list[PipelineTemplateInfo] = Field(default_factory=list)


class PipelineDownloadRequest(BaseModel):
    """Request body for downloading pipeline files as a zip."""

    architecture: dict = Field(..., description="Architecture definition JSON")
    iac_format: IaCFormat = Field(..., description="IaC format to generate pipeline for")
    pipeline_format: PipelineFormat = Field(
        default=PipelineFormat.github_actions,
        description="CI/CD pipeline format",
    )
    environments: list[str] = Field(
        default_factory=lambda: ["dev", "staging", "prod"],
        description="Target deployment environments",
    )
    include_approval_gates: bool = Field(
        default=True, description="Include approval gates between environments"
    )
    project_name: str = Field(
        default="onramp-landing-zone", description="Project name for workflow naming"
    )
    service_connection: str = Field(
        default="azure-service-connection",
        description="Azure DevOps service connection name (Azure DevOps only)",
    )
    variable_group: str = Field(
        default="landing-zone-secrets",
        description="Variable group name for secrets (Azure DevOps only)",
    )
