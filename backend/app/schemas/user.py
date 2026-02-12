"""User schemas."""

from pydantic import BaseModel
from datetime import datetime


class UserBase(BaseModel):
    email: str
    display_name: str
    role: str = "viewer"


class UserCreate(UserBase):
    entra_object_id: str
    tenant_id: str


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
