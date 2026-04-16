"""Pydantic schemas for architecture version endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

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


class PropertyDiff(BaseModel):
    """Property-level difference within a modified component."""

    property_name: str
    old_value: Any = None
    new_value: Any = None
    change_type: str = "modified"  # "added" | "removed" | "modified"


class EnhancedComponentChange(BaseModel):
    """Extended component change with property-level diffs."""

    name: str
    detail: str = ""
    category: str = "general"
    property_diffs: list[PropertyDiff] = Field(default_factory=list)


class CategoryGroup(BaseModel):
    """Changes grouped by architecture category."""

    category: str
    display_name: str
    added: list[EnhancedComponentChange] = Field(default_factory=list)
    removed: list[EnhancedComponentChange] = Field(default_factory=list)
    modified: list[EnhancedComponentChange] = Field(default_factory=list)

    @property
    def total_changes(self) -> int:
        return len(self.added) + len(self.removed) + len(self.modified)


class VersionDiffResponse(BaseModel):
    """Diff between two architecture versions."""

    from_version: int
    to_version: int
    added_components: list[ComponentChange]
    removed_components: list[ComponentChange]
    modified_components: list[ComponentChange]
    summary: str


class EnhancedVersionDiffResponse(BaseModel):
    """Enhanced diff with property-level detail and category grouping."""

    from_version: int
    to_version: int
    added_components: list[EnhancedComponentChange]
    removed_components: list[EnhancedComponentChange]
    modified_components: list[EnhancedComponentChange]
    summary: str
    change_counts: dict[str, int] = Field(default_factory=dict)
    category_groups: list[CategoryGroup] = Field(default_factory=list)


class ConflictResponse(BaseModel):
    """Structured 409 Conflict response for optimistic concurrency."""

    current_version: int
    submitted_version: int
    current_data: dict[str, Any] = Field(default_factory=dict)
    message: str


class RestoreVersionRequest(BaseModel):
    """Request body for restoring a historical version."""

    change_summary: str | None = Field(
        default=None,
        max_length=500,
        description="Optional note describing the restore.",
    )
