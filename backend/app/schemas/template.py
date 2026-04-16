"""Template marketplace schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TemplateVisibility(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"
    CURATED = "curated"


class TemplateRatingValue(str, Enum):
    UP = "up"
    DOWN = "down"


class TemplateCreate(BaseModel):
    name: str = Field(..., description="Template name")
    description: str | None = Field(
        None, description="Template description"
    )
    industry: str = Field(..., description="Target industry")
    tags: list[str] = Field(
        default_factory=list, description="Searchable tags"
    )
    architecture_json: str = Field(
        ..., description="Architecture definition as JSON string"
    )
    visibility: TemplateVisibility = Field(
        default=TemplateVisibility.PRIVATE,
        description="Template visibility",
    )


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    industry: str
    tags: list[str] = Field(default_factory=list)
    architecture_json: str | None = None
    author_tenant_id: str | None = None
    visibility: str
    download_count: int = 0
    rating_up: int = 0
    rating_down: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TemplateListResponse(BaseModel):
    templates: list[TemplateResponse]
    total: int
    page: int
    page_size: int


class TemplateUseRequest(BaseModel):
    project_id: str = Field(
        ..., description="Project to apply the template to"
    )


class TemplateRatingRequest(BaseModel):
    rating: TemplateRatingValue = Field(
        ..., description="Thumbs up or down"
    )
