"""User schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    email: str = Field(
        ...,
        min_length=3,
        max_length=320,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    display_name: str = Field(..., min_length=1, max_length=255)
    role: Literal["admin", "architect", "viewer"] = "viewer"


class UserCreate(UserBase):
    entra_object_id: str = Field(..., min_length=1, max_length=255)
    tenant_id: str = Field(..., min_length=1, max_length=255)


class UserResponse(UserBase):
    id: str
    entra_object_id: str
    tenant_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserProfile(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    tenant_id: str
