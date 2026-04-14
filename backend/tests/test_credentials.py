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


def test_is_configured_false_in_dev(cred_manager):
    """is_configured returns False when no tenant is set."""
    assert cred_manager.is_configured is False


def test_get_credential_returns_none_in_dev(cred_manager):
    """_get_credential returns None in dev mode."""
    result = cred_manager._get_credential()
    assert result is None


def test_get_resource_client_returns_none_in_dev(cred_manager):
    """get_resource_client returns None when not configured."""
    result = cred_manager.get_resource_client("test-sub-id")
    assert result is None


def test_credential_info_dataclass():
    """AzureCredentialInfo stores data correctly."""
    info = AzureCredentialInfo(
        subscription_id="sub-1",
        tenant_id="tenant-1",
        credential_type="service_principal",
        is_valid=True,
        permissions=["Contributor"],
    )
    assert info.subscription_id == "sub-1"
    assert info.tenant_id == "tenant-1"
    assert info.credential_type == "service_principal"
    assert info.is_valid is True
    assert info.permissions == ["Contributor"]
    assert info.error is None


def test_credential_info_with_error():
    """AzureCredentialInfo with error."""
    info = AzureCredentialInfo(
        subscription_id="sub-2",
        tenant_id="t2",
        credential_type="managed_identity",
        is_valid=False,
        error="Not configured",
    )
    assert info.is_valid is False
    assert info.error == "Not configured"
    assert info.permissions == []


@pytest.mark.asyncio
async def test_validate_credentials_with_custom_tenant(cred_manager):
    """Validate with explicit tenant_id in dev mode."""
    info = await cred_manager.validate_credentials("sub-x", tenant_id="custom-tenant")
    assert isinstance(info, AzureCredentialInfo)
    assert info.is_valid is False


@pytest.mark.asyncio
async def test_check_quotas_different_region(cred_manager):
    """Quota check with different region."""
    result = await cred_manager.check_subscription_quotas("sub-1", "westus2")
    assert "quotas_sufficient" in result
