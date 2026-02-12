"""Tests for credential management service."""

import pytest
from app.services.credentials import CredentialManager, AzureCredentialInfo


@pytest.fixture
def cred_manager():
    return CredentialManager()


@pytest.mark.asyncio
async def test_validate_credentials_dev_mode(cred_manager):
    """In dev mode (no tenant configured), validation fails gracefully."""
    info = await cred_manager.validate_credentials("test-sub-id")
    assert isinstance(info, AzureCredentialInfo)
    assert info.is_valid is False
    assert info.subscription_id == "test-sub-id"


@pytest.mark.asyncio
async def test_check_deployment_permissions_dev_mode(cred_manager):
    """In dev mode, returns missing permissions."""
    result = await cred_manager.check_deployment_permissions("test-sub-id")
    assert result["has_permissions"] is False
    assert len(result["missing_permissions"]) > 0


@pytest.mark.asyncio
async def test_check_quotas_dev_mode(cred_manager):
    """In dev mode, quota check returns success."""
    result = await cred_manager.check_subscription_quotas("test-sub-id", "eastus2")
    assert result["quotas_sufficient"] is True
