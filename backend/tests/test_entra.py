"""Tests for Entra ID authentication."""
import logging

import pytest
from unittest.mock import patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.entra import get_current_user, _get_jwks
from app.config import settings


@pytest.mark.asyncio
async def test_dev_mode_returns_mock_user():
    """When debug=True, return dev user (mock auth)."""
    original_debug = settings.debug
    original_tenant = settings.azure_tenant_id
    settings.debug = True
    settings.azure_tenant_id = ""
    try:
        user = await get_current_user(credentials=None)
        assert user["name"] == "Development User"
        assert user["email"] == "dev@onramp.local"
        assert "admin" in user["roles"]
    finally:
        settings.debug = original_debug
        settings.azure_tenant_id = original_tenant


@pytest.mark.asyncio
async def test_mock_auth_only_when_debug_true():
    """When tenant is empty but debug=False, mock auth must NOT activate."""
    original_debug = settings.debug
    original_tenant = settings.azure_tenant_id
    settings.debug = False
    settings.azure_tenant_id = ""
    try:
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=None)
        assert exc_info.value.status_code == 401
    finally:
        settings.debug = original_debug
        settings.azure_tenant_id = original_tenant


@pytest.mark.asyncio
async def test_mock_auth_logs_warning(caplog):
    """Mock auth mode should log a warning."""
    original_debug = settings.debug
    original_tenant = settings.azure_tenant_id
    settings.debug = True
    settings.azure_tenant_id = ""
    try:
        with caplog.at_level(logging.WARNING, logger="app.auth.entra"):
            await get_current_user(credentials=None)
        assert any("Mock auth active" in r.message for r in caplog.records)
    finally:
        settings.debug = original_debug
        settings.azure_tenant_id = original_tenant


@pytest.mark.asyncio
async def test_missing_credentials_with_tenant():
    """When tenant is configured but no credentials, raise 401."""
    original_debug = settings.debug
    original_tenant = settings.azure_tenant_id
    settings.debug = False
    settings.azure_tenant_id = "fake-tenant-id"
    try:
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=None)
        assert exc_info.value.status_code == 401
    finally:
        settings.debug = original_debug
        settings.azure_tenant_id = original_tenant


@pytest.mark.asyncio
async def test_invalid_token():
    """Invalid token should raise 401."""
    original_debug = settings.debug
    original_tenant = settings.azure_tenant_id
    settings.debug = False
    settings.azure_tenant_id = "fake-tenant-id"
    try:
        creds = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid.token.here"
        )
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=creds)
        assert exc_info.value.status_code == 401
    finally:
        settings.debug = original_debug
        settings.azure_tenant_id = original_tenant
