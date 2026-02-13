"""Tests for Entra ID authentication."""
import pytest
from unittest.mock import patch, AsyncMock
from app.auth.entra import get_current_user, _get_jwks
from app.config import settings

@pytest.mark.asyncio
async def test_dev_mode_returns_mock_user():
    """When no tenant is configured, return dev user."""
    original = settings.azure_tenant_id
    settings.azure_tenant_id = ""
    try:
        user = await get_current_user(credentials=None)
        assert user["name"] == "Development User"
        assert user["email"] == "dev@onramp.local"
        assert "admin" in user["roles"]
    finally:
        settings.azure_tenant_id = original

@pytest.mark.asyncio
async def test_missing_credentials_with_tenant():
    """When tenant is configured but no credentials, raise 401."""
    from fastapi import HTTPException
    original = settings.azure_tenant_id
    settings.azure_tenant_id = "fake-tenant-id"
    try:
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=None)
        assert exc_info.value.status_code == 401
    finally:
        settings.azure_tenant_id = original

@pytest.mark.asyncio
async def test_invalid_token():
    """Invalid token should raise 401."""
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials
    original = settings.azure_tenant_id
    settings.azure_tenant_id = "fake-tenant-id"
    try:
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.token.here")
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds)
        assert exc_info.value.status_code == 401
    finally:
        settings.azure_tenant_id = original
