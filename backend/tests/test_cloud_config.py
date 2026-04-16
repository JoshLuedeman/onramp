"""Tests for sovereign cloud configuration models, service, and routes."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.cloud_environment import (
    CLOUD_ENDPOINTS,
    CloudEndpoints,
    CloudEnvironment,
)
from app.schemas.cloud_config import (
    CloudEndpointsResponse,
    CloudEnvironmentResponse,
    EnvironmentValidationRequest,
    EnvironmentValidationResponse,
)
from app.services.cloud_config_service import CloudConfigService, cloud_config_service

client = TestClient(app)

AUTH_HEADERS = {"Authorization": "Bearer dev-token"}


# ---------------------------------------------------------------------------
# Model / enum tests
# ---------------------------------------------------------------------------


class TestCloudEnvironmentEnum:
    """CloudEnvironment enum value and membership checks."""

    def test_commercial_value(self):
        assert CloudEnvironment.COMMERCIAL.value == "commercial"

    def test_government_value(self):
        assert CloudEnvironment.GOVERNMENT.value == "government"

    def test_china_value(self):
        assert CloudEnvironment.CHINA.value == "china"

    def test_enum_has_three_members(self):
        assert len(CloudEnvironment) == 3

    def test_enum_lookup_by_value(self):
        assert CloudEnvironment("commercial") is CloudEnvironment.COMMERCIAL


# ---------------------------------------------------------------------------
# Endpoint mapping tests
# ---------------------------------------------------------------------------


class TestCloudEndpointsMapping:
    """Verify CLOUD_ENDPOINTS contains correct URLs for every environment."""

    def test_all_environments_have_endpoints(self):
        for env in CloudEnvironment:
            assert env in CLOUD_ENDPOINTS

    def test_commercial_resource_manager(self):
        ep = CLOUD_ENDPOINTS[CloudEnvironment.COMMERCIAL]
        assert ep.resource_manager == "https://management.azure.com"

    def test_commercial_authentication(self):
        ep = CLOUD_ENDPOINTS[CloudEnvironment.COMMERCIAL]
        assert ep.authentication == "https://login.microsoftonline.com"

    def test_commercial_portal(self):
        ep = CLOUD_ENDPOINTS[CloudEnvironment.COMMERCIAL]
        assert ep.portal == "https://portal.azure.com"

    def test_commercial_graph(self):
        ep = CLOUD_ENDPOINTS[CloudEnvironment.COMMERCIAL]
        assert ep.graph == "https://graph.microsoft.com"

    def test_commercial_ai_foundry_available(self):
        ep = CLOUD_ENDPOINTS[CloudEnvironment.COMMERCIAL]
        assert ep.ai_foundry is not None

    def test_government_resource_manager(self):
        ep = CLOUD_ENDPOINTS[CloudEnvironment.GOVERNMENT]
        assert ep.resource_manager == "https://management.usgovcloudapi.net"

    def test_government_authentication(self):
        ep = CLOUD_ENDPOINTS[CloudEnvironment.GOVERNMENT]
        assert ep.authentication == "https://login.microsoftonline.us"

    def test_government_ai_foundry_unavailable(self):
        ep = CLOUD_ENDPOINTS[CloudEnvironment.GOVERNMENT]
        assert ep.ai_foundry is None

    def test_china_resource_manager(self):
        ep = CLOUD_ENDPOINTS[CloudEnvironment.CHINA]
        assert ep.resource_manager == "https://management.chinacloudapi.cn"

    def test_china_authentication(self):
        ep = CLOUD_ENDPOINTS[CloudEnvironment.CHINA]
        assert ep.authentication == "https://login.chinacloudapi.cn"

    def test_china_ai_foundry_unavailable(self):
        ep = CLOUD_ENDPOINTS[CloudEnvironment.CHINA]
        assert ep.ai_foundry is None

    def test_cloud_endpoints_is_pydantic_model(self):
        ep = CLOUD_ENDPOINTS[CloudEnvironment.COMMERCIAL]
        assert isinstance(ep, CloudEndpoints)

    def test_storage_suffix_differs_per_cloud(self):
        suffixes = {
            CLOUD_ENDPOINTS[env].storage_suffix for env in CloudEnvironment
        }
        assert len(suffixes) == 3


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def service():
    return CloudConfigService()


class TestCloudConfigServiceEndpoints:
    def test_get_endpoints_commercial(self, service):
        ep = service.get_endpoints(CloudEnvironment.COMMERCIAL)
        assert ep.resource_manager == "https://management.azure.com"

    def test_get_endpoints_government(self, service):
        ep = service.get_endpoints(CloudEnvironment.GOVERNMENT)
        assert "usgovcloudapi" in ep.resource_manager

    def test_get_endpoints_china(self, service):
        ep = service.get_endpoints(CloudEnvironment.CHINA)
        assert "chinacloudapi" in ep.resource_manager


class TestCloudConfigServiceDefaults:
    def test_default_environment_is_commercial(self, service):
        assert service.get_default_environment() == CloudEnvironment.COMMERCIAL

    def test_available_environments_returns_all(self, service):
        envs = service.get_available_environments()
        assert len(envs) == 3
        assert CloudEnvironment.COMMERCIAL in envs
        assert CloudEnvironment.GOVERNMENT in envs
        assert CloudEnvironment.CHINA in envs


class TestCloudConfigServiceMetadata:
    def test_metadata_has_display_name(self, service):
        meta = service.get_environment_metadata(CloudEnvironment.COMMERCIAL)
        assert meta["display_name"] == "Azure Commercial"

    def test_metadata_has_regions(self, service):
        meta = service.get_environment_metadata(CloudEnvironment.GOVERNMENT)
        assert "usgovvirginia" in meta["regions"]

    def test_metadata_has_restrictions_for_government(self, service):
        meta = service.get_environment_metadata(CloudEnvironment.GOVERNMENT)
        assert len(meta["restrictions"]) > 0

    def test_metadata_commercial_no_restrictions(self, service):
        meta = service.get_environment_metadata(CloudEnvironment.COMMERCIAL)
        assert meta["restrictions"] == []


class TestCloudConfigServiceValidation:
    def test_validate_all_services_available(self, service):
        result = service.validate_environment_support(
            CloudEnvironment.COMMERCIAL,
            ["compute", "storage", "sql"],
        )
        assert result["supported"] is True
        assert result["missing_services"] == []

    def test_validate_missing_service_in_government(self, service):
        result = service.validate_environment_support(
            CloudEnvironment.GOVERNMENT,
            ["compute", "ai_foundry"],
        )
        assert result["supported"] is False
        assert "ai_foundry" in result["missing_services"]

    def test_validate_missing_service_in_china(self, service):
        result = service.validate_environment_support(
            CloudEnvironment.CHINA,
            ["container_apps"],
        )
        assert result["supported"] is False
        assert "container_apps" in result["missing_services"]

    def test_validate_empty_services_is_supported(self, service):
        result = service.validate_environment_support(
            CloudEnvironment.CHINA, [],
        )
        assert result["supported"] is True

    def test_validate_warning_for_non_commercial(self, service):
        result = service.validate_environment_support(
            CloudEnvironment.GOVERNMENT,
            ["compute"],
        )
        assert len(result["warnings"]) > 0

    def test_validate_no_warning_for_commercial(self, service):
        result = service.validate_environment_support(
            CloudEnvironment.COMMERCIAL,
            ["compute"],
        )
        assert result["warnings"] == []


class TestCloudConfigSingleton:
    def test_singleton_exists(self):
        assert cloud_config_service is not None
        assert isinstance(cloud_config_service, CloudConfigService)


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestSchemas:
    def test_cloud_environment_response_roundtrip(self):
        resp = CloudEnvironmentResponse(
            name="commercial",
            display_name="Azure Commercial",
            description="Global public cloud",
            available_regions=["eastus"],
        )
        assert resp.name == "commercial"
        assert resp.available_regions == ["eastus"]

    def test_cloud_endpoints_response_roundtrip(self):
        resp = CloudEndpointsResponse(
            resource_manager="https://management.azure.com",
            authentication="https://login.microsoftonline.com",
            portal="https://portal.azure.com",
            graph="https://graph.microsoft.com",
            storage_suffix=".blob.core.windows.net",
            sql_suffix=".database.windows.net",
            keyvault_suffix=".vault.azure.net",
            ai_foundry="https://ai.azure.com",
        )
        assert resp.resource_manager == "https://management.azure.com"

    def test_validation_request_schema(self):
        req = EnvironmentValidationRequest(
            environment="government",
            required_services=["compute", "storage"],
        )
        assert req.environment == "government"
        assert len(req.required_services) == 2

    def test_validation_response_schema(self):
        resp = EnvironmentValidationResponse(
            supported=False,
            missing_services=["ai_foundry"],
            warnings=["Limited availability"],
        )
        assert resp.supported is False
        assert "ai_foundry" in resp.missing_services


# ---------------------------------------------------------------------------
# Route tests
# ---------------------------------------------------------------------------


class TestListEnvironmentsRoute:
    def test_list_returns_200(self):
        resp = client.get("/api/cloud/environments", headers=AUTH_HEADERS)
        assert resp.status_code == 200

    def test_list_returns_three_environments(self):
        resp = client.get("/api/cloud/environments", headers=AUTH_HEADERS)
        data = resp.json()
        assert len(data) == 3

    def test_list_contains_commercial(self):
        resp = client.get("/api/cloud/environments", headers=AUTH_HEADERS)
        names = [e["name"] for e in resp.json()]
        assert "commercial" in names

    def test_list_contains_government(self):
        resp = client.get("/api/cloud/environments", headers=AUTH_HEADERS)
        names = [e["name"] for e in resp.json()]
        assert "government" in names

    def test_list_contains_china(self):
        resp = client.get("/api/cloud/environments", headers=AUTH_HEADERS)
        names = [e["name"] for e in resp.json()]
        assert "china" in names

    def test_list_items_have_required_fields(self):
        resp = client.get("/api/cloud/environments", headers=AUTH_HEADERS)
        for item in resp.json():
            assert "name" in item
            assert "display_name" in item
            assert "description" in item
            assert "available_regions" in item


class TestGetEnvironmentRoute:
    def test_get_commercial(self):
        resp = client.get(
            "/api/cloud/environments/commercial", headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "commercial"

    def test_get_government(self):
        resp = client.get(
            "/api/cloud/environments/government", headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Azure Government"

    def test_get_invalid_returns_404(self):
        resp = client.get(
            "/api/cloud/environments/invalid", headers=AUTH_HEADERS,
        )
        assert resp.status_code == 404


class TestGetEndpointsRoute:
    def test_commercial_endpoints(self):
        resp = client.get(
            "/api/cloud/environments/commercial/endpoints",
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["resource_manager"] == "https://management.azure.com"

    def test_government_endpoints(self):
        resp = client.get(
            "/api/cloud/environments/government/endpoints",
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert "usgovcloudapi" in resp.json()["resource_manager"]

    def test_china_endpoints(self):
        resp = client.get(
            "/api/cloud/environments/china/endpoints",
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert "chinacloudapi" in resp.json()["resource_manager"]

    def test_invalid_env_returns_404(self):
        resp = client.get(
            "/api/cloud/environments/invalid/endpoints",
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 404


class TestValidateRoute:
    def test_validate_supported(self):
        resp = client.post(
            "/api/cloud/environments/validate",
            json={
                "environment": "commercial",
                "required_services": ["compute", "storage"],
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["supported"] is True

    def test_validate_unsupported_service(self):
        resp = client.post(
            "/api/cloud/environments/validate",
            json={
                "environment": "government",
                "required_services": ["ai_foundry"],
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["supported"] is False
        assert "ai_foundry" in data["missing_services"]

    def test_validate_invalid_environment(self):
        resp = client.post(
            "/api/cloud/environments/validate",
            json={
                "environment": "mars",
                "required_services": ["compute"],
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 404

    def test_validate_empty_services(self):
        resp = client.post(
            "/api/cloud/environments/validate",
            json={
                "environment": "china",
                "required_services": [],
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["supported"] is True

    def test_validate_response_has_warnings(self):
        resp = client.post(
            "/api/cloud/environments/validate",
            json={
                "environment": "government",
                "required_services": ["compute"],
            },
            headers=AUTH_HEADERS,
        )
        assert resp.status_code == 200
        assert len(resp.json()["warnings"]) > 0
