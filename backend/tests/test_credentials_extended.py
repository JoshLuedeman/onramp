"""Extended tests for credential management service."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.credentials import CredentialManager, AzureCredentialInfo, credential_manager


@pytest.fixture
def cred_mgr():
    return CredentialManager()


def test_credential_manager_instantiation():
    mgr = CredentialManager()
    assert mgr._credential is None


def test_is_configured_false_by_default(cred_mgr):
    assert cred_mgr.is_configured is False


def test_is_configured_true_when_tenant_set(cred_mgr):
    with patch("app.services.credentials.settings") as mock_settings:
        mock_settings.azure_tenant_id = "some-tenant-id"
        assert cred_mgr.is_configured is True


def test_get_credential_returns_none_when_not_configured(cred_mgr):
    assert cred_mgr._get_credential() is None


def test_get_credential_returns_none_on_import_error(cred_mgr):
    with patch("app.services.credentials.settings") as mock_settings:
        mock_settings.azure_tenant_id = "tenant-id"
        with patch("builtins.__import__", side_effect=ImportError("no azure")):
            result = cred_mgr._get_credential()
            assert result is None


def test_get_credential_caches_result(cred_mgr):
    mock_cred = MagicMock()
    cred_mgr._credential = mock_cred
    assert cred_mgr._get_credential() is mock_cred


def test_azure_credential_info_defaults():
    info = AzureCredentialInfo(
        subscription_id="sub-1",
        tenant_id="tenant-1",
        credential_type="service_principal",
    )
    assert info.is_valid is False
    assert info.permissions == []
    assert info.error is None


def test_azure_credential_info_with_values():
    info = AzureCredentialInfo(
        subscription_id="sub-1",
        tenant_id="tenant-1",
        credential_type="managed_identity",
        is_valid=True,
        permissions=["Reader", "Contributor"],
        error=None,
    )
    assert info.is_valid is True
    assert len(info.permissions) == 2


@pytest.mark.asyncio
async def test_validate_credentials_not_configured(cred_mgr):
    info = await cred_mgr.validate_credentials("sub-123", "tenant-abc")
    assert info.is_valid is False
    assert "not configured" in info.error
    assert info.subscription_id == "sub-123"
    assert info.tenant_id == "tenant-abc"


@pytest.mark.asyncio
async def test_validate_credentials_default_tenant(cred_mgr):
    info = await cred_mgr.validate_credentials("sub-123")
    assert info.is_valid is False
    assert info.credential_type == "service_principal"


@pytest.mark.asyncio
async def test_validate_credentials_credential_init_failure():
    mgr = CredentialManager()
    with patch("app.services.credentials.settings") as mock_settings:
        mock_settings.azure_tenant_id = "tenant-id"
        mgr._get_credential = lambda: None
        info = await mgr.validate_credentials("sub-1")
        assert info.is_valid is False
        assert "Failed to initialize" in info.error


@pytest.mark.asyncio
async def test_validate_credentials_subscription_client_error():
    mgr = CredentialManager()
    mock_cred = MagicMock()
    mgr._credential = mock_cred
    with patch("app.services.credentials.settings") as mock_settings:
        mock_settings.azure_tenant_id = "tenant-id"
        with patch(
            "app.services.credentials.CredentialManager._get_credential",
            return_value=mock_cred,
        ):
            # The import of SubscriptionClient inside the method will fail
            with patch.dict("sys.modules", {"azure.mgmt.resource": None}):
                info = await mgr.validate_credentials("sub-1")
                assert info.is_valid is False
                assert info.error is not None


@pytest.mark.asyncio
async def test_check_deployment_permissions_not_configured(cred_mgr):
    result = await cred_mgr.check_deployment_permissions("sub-1")
    assert result["has_permissions"] is False
    assert "development mode" in result["error"]
    assert len(result["missing_permissions"]) == 6


@pytest.mark.asyncio
async def test_check_deployment_permissions_credential_failure():
    mgr = CredentialManager()
    with patch("app.services.credentials.settings") as mock_settings:
        mock_settings.azure_tenant_id = "tenant-id"
        mgr._get_credential = lambda: None
        result = await mgr.check_deployment_permissions("sub-1")
        assert result["has_permissions"] is False
        assert "Failed to initialize" in result["error"]


@pytest.mark.asyncio
async def test_check_subscription_quotas_not_configured(cred_mgr):
    result = await cred_mgr.check_subscription_quotas("sub-1", "eastus2")
    assert result["quotas_sufficient"] is True
    assert any("dev mode" in w for w in result["warnings"])


@pytest.mark.asyncio
async def test_check_subscription_quotas_credential_failure():
    mgr = CredentialManager()
    with patch("app.services.credentials.settings") as mock_settings:
        mock_settings.azure_tenant_id = "tenant-id"
        mgr._get_credential = lambda: None
        result = await mgr.check_subscription_quotas("sub-1", "eastus2")
        assert result["quotas_sufficient"] is False
        assert any("Failed to initialize" in w for w in result["warnings"])


def test_get_resource_client_not_configured(cred_mgr):
    assert cred_mgr.get_resource_client("sub-1") is None


def test_get_resource_client_credential_failure():
    mgr = CredentialManager()
    with patch("app.services.credentials.settings") as mock_settings:
        mock_settings.azure_tenant_id = "tenant-id"
        mgr._get_credential = lambda: None
        assert mgr.get_resource_client("sub-1") is None


def test_get_resource_client_import_error():
    mgr = CredentialManager()
    mock_cred = MagicMock()
    mgr._credential = mock_cred
    with patch("app.services.credentials.settings") as mock_settings:
        mock_settings.azure_tenant_id = "tenant-id"
        with patch.dict("sys.modules", {"azure.mgmt.resource": None}):
            result = mgr.get_resource_client("sub-1")
            assert result is None


def test_singleton_exists():
    assert credential_manager is not None
    assert isinstance(credential_manager, CredentialManager)


@pytest.mark.asyncio
async def test_check_deployment_permissions_import_error():
    """When Azure is configured but AuthorizationManagementClient import fails."""
    mgr = CredentialManager()
    mock_cred = MagicMock()
    mgr._credential = mock_cred
    with patch("app.services.credentials.settings") as mock_settings:
        mock_settings.azure_tenant_id = "tenant-id"
        with patch.dict("sys.modules", {"azure.mgmt.authorization": None}):
            result = await mgr.check_deployment_permissions("sub-1")
            assert result["has_permissions"] is False
            assert result["error"] is not None


@pytest.mark.asyncio
async def test_check_quotas_import_error():
    """When Azure is configured but compute/network client import fails."""
    mgr = CredentialManager()
    mock_cred = MagicMock()
    mgr._credential = mock_cred
    with patch("app.services.credentials.settings") as mock_settings:
        mock_settings.azure_tenant_id = "tenant-id"
        with patch.dict("sys.modules", {"azure.mgmt.compute": None, "azure.mgmt.network": None}):
            result = await mgr.check_subscription_quotas("sub-1", "eastus2")
            assert "quotas_sufficient" in result
