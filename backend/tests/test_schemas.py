"""Tests for Pydantic schemas."""
import pytest
from pydantic import ValidationError
from app.schemas.user import UserBase, UserCreate, UserResponse
from app.schemas.project import ProjectBase, ProjectCreate, ProjectResponse
from app.schemas.tenant import TenantBase, TenantCreate, TenantResponse

def test_user_base_defaults():
    u = UserBase(email="test@example.com", display_name="Test")
    assert u.role == "viewer"

def test_user_create_requires_fields():
    u = UserCreate(email="a@b.com", display_name="A", entra_object_id="oid", tenant_id="tid")
    assert u.entra_object_id == "oid"

def test_user_create_missing_field():
    with pytest.raises(ValidationError):
        UserCreate(email="a@b.com", display_name="A")

def test_project_base_optional_description():
    p = ProjectBase(name="Test")
    assert p.description is None

def test_project_create_inherits():
    p = ProjectCreate(name="My Project", description="desc")
    assert p.name == "My Project"

def test_tenant_base():
    t = TenantBase(name="Contoso")
    assert t.azure_tenant_id is None

def test_tenant_create():
    t = TenantCreate(name="Contoso", azure_tenant_id="tid-123")
    assert t.azure_tenant_id == "tid-123"

def test_user_response_from_attributes():
    assert UserResponse.model_config.get("from_attributes") is True

def test_project_response_from_attributes():
    assert ProjectResponse.model_config.get("from_attributes") is True

def test_tenant_response_from_attributes():
    assert TenantResponse.model_config.get("from_attributes") is True
