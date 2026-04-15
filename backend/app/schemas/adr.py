"""Pydantic schemas for ADR generation and export."""

from typing import Literal

from pydantic import BaseModel, Field


class ADRRecord(BaseModel):
    """A single Architecture Decision Record."""

    id: str
    title: str
    status: str = "Accepted"
    context: str
    decision: str
    consequences: str
    category: str  # e.g., "networking", "identity", "compliance"
    created_at: str


class ADRGenerateRequest(BaseModel):
    """Request to generate ADRs from architecture data."""

    architecture: dict
    answers: dict[str, str | list[str]] = Field(default_factory=dict)
    use_ai: bool = False
    project_id: str | None = None


class ADRGenerateResponse(BaseModel):
    """Response containing generated ADRs."""

    adrs: list[ADRRecord]
    project_id: str | None = None


class ADRExportRequest(BaseModel):
    """Request to export ADRs as Markdown."""

    adrs: list[ADRRecord]
    format: Literal["individual", "combined"] = "combined"
