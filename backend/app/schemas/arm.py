"""Pydantic schemas for ARM template generation request and response models."""

from pydantic import BaseModel, Field


class GenerateARMRequest(BaseModel):
    """Request body for ARM template generation."""

    architecture: dict = Field(..., description="Architecture definition JSON")
    use_ai: bool = Field(default=True, description="Use AI for generation")
    project_id: str = Field(default="", description="Optional project ID for persistence")


class ValidateARMRequest(BaseModel):
    """Request body for ARM template validation."""

    template: str = Field(..., description="ARM template JSON content as a string")


class DownloadARMRequest(BaseModel):
    """Request body for ARM template download."""

    architecture: dict = Field(..., description="Architecture definition JSON")
    use_ai: bool = Field(default=True, description="Use AI for generation")


class ARMFileResponse(BaseModel):
    """Single ARM template file in a response."""

    name: str
    content: str
    size_bytes: int


class GenerateARMResponse(BaseModel):
    """Response body for ARM template generation."""

    files: list[ARMFileResponse]
    total_files: int
    ai_generated: bool


class ValidateARMResponse(BaseModel):
    """Response body for ARM template validation."""

    valid: bool
    errors: list[str]
    warnings: list[str]
