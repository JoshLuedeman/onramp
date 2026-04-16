"""Pydantic models for Pulumi code generation requests and responses."""

from typing import Literal

from pydantic import BaseModel, Field


class GeneratePulumiRequest(BaseModel):
    """Request body for generating Pulumi code from an architecture definition."""

    architecture: dict
    language: Literal["typescript", "python"] = Field(
        default="typescript",
        description="Target Pulumi language — 'typescript' or 'python'.",
    )
    use_ai: bool = True
    project_id: str = ""


class PulumiFileResponse(BaseModel):
    """A single generated Pulumi file."""

    name: str
    content: str
    size_bytes: int


class GeneratePulumiResponse(BaseModel):
    """Response from the Pulumi generation endpoint."""

    files: list[PulumiFileResponse]
    total_files: int
    language: str
    ai_generated: bool


class PulumiTemplateResponse(BaseModel):
    """A single Pulumi template descriptor."""

    name: str
    description: str
    languages: list[str]


class PulumiTemplateListResponse(BaseModel):
    """Response from the templates listing endpoint."""

    templates: list[PulumiTemplateResponse]
