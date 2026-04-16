"""Pydantic schemas for Terraform generation request/response models."""

from pydantic import BaseModel, Field


class TerraformGenerateRequest(BaseModel):
    """Request body for Terraform HCL generation."""

    architecture: dict = Field(..., description="Architecture definition JSON")
    use_ai: bool = Field(default=True, description="Use AI for generation")
    project_id: str = Field(default="", description="Optional project ID for persistence")


class TerraformFile(BaseModel):
    """A single generated Terraform file."""

    name: str = Field(..., description="File name (e.g. main.tf)")
    content: str = Field(..., description="HCL file content")
    size_bytes: int = Field(..., description="Content size in bytes")


class TerraformGenerateResponse(BaseModel):
    """Response from Terraform generation."""

    files: list[TerraformFile] = Field(default_factory=list)
    total_files: int = Field(default=0)
    ai_generated: bool = Field(default=False)


class TerraformTemplateInfo(BaseModel):
    """Metadata for an available Terraform module/template."""

    name: str = Field(..., description="Module name")
    description: str = Field(default="", description="Module description")
    category: str = Field(default="general", description="Module category")


class TerraformTemplateListResponse(BaseModel):
    """Response for listing available Terraform modules."""

    templates: list[TerraformTemplateInfo] = Field(default_factory=list)


class TerraformDownloadRequest(BaseModel):
    """Request body for downloading Terraform as a zip."""

    architecture: dict = Field(..., description="Architecture definition JSON")
    use_ai: bool = Field(default=True, description="Use AI for generation")
