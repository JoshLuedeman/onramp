"""User schemas."""

from datetime import datetime

from pydantic import BaseModel


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
