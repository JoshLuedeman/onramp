"""Pydantic schemas for architecture version endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class ArchitectureVersionResponse(BaseModel):
    """Single architecture version detail."""

    id: str
    version_number: int
    architecture_json: str
    change_summary: str | None = None
    created_by: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VersionListResponse(BaseModel):
    """Paginated list of architecture versions."""

    versions: list[ArchitectureVersionResponse]
    total: int


class ComponentChange(BaseModel):
    """Describes a single component difference between two versions."""

    name: str
    detail: str = ""


class VersionDiffResponse(BaseModel):
    """Diff between two architecture versions."""

    from_version: int
    to_version: int
    added_components: list[ComponentChange]
    removed_components: list[ComponentChange]
    modified_components: list[ComponentChange]
    summary: str


class RestoreVersionRequest(BaseModel):
    """Request body for restoring a historical version."""

    change_summary: str | None = Field(
        default=None, max_length=500, description="Optional note describing the restore."
    )
