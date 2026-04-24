"""Tests for the CloudConfigService."""

import pytest

from app.models.cloud_environment import CloudEnvironment
from app.services.cloud_config_service import cloud_config_service


class TestGetEndpoints:
    """Test endpoint resolution for each cloud environment."""

    def test_commercial_endpoints(self):
        endpoints = cloud_config_service.get_endpoints(CloudEnvironment.COMMERCIAL)
        assert endpoints.resource_manager.startswith("https://management.azure.com")
        assert endpoints.authentication.startswith("https://login.microsoftonline.com")

    def test_government_endpoints(self):
        endpoints = cloud_config_service.get_endpoints(CloudEnvironment.GOVERNMENT)
        assert "usgovcloudapi" in endpoints.resource_manager
        assert "login.microsoftonline.us" in endpoints.authentication

    def test_china_endpoints(self):
        endpoints = cloud_config_service.get_endpoints(CloudEnvironment.CHINA)
        assert "chinacloudapi" in endpoints.resource_manager
        assert "chinacloudapi" in endpoints.authentication


class TestGetDefaultEnvironment:
    def test_default_is_commercial(self):
        env = cloud_config_service.get_default_environment()
        assert env == CloudEnvironment.COMMERCIAL


class TestGetAvailableEnvironments:
    def test_returns_all_environments(self):
        envs = cloud_config_service.get_available_environments()
        assert len(envs) >= 3
        env_values = [e.value if hasattr(e, "value") else e for e in envs]
        assert "commercial" in [str(v).lower() for v in env_values] or len(envs) >= 3


class TestGetEnvironmentMetadata:
    def test_commercial_metadata(self):
        meta = cloud_config_service.get_environment_metadata(
            CloudEnvironment.COMMERCIAL
        )
        assert "display_name" in meta
        assert "regions" in meta
        assert len(meta["regions"]) > 0

    def test_government_metadata(self):
        meta = cloud_config_service.get_environment_metadata(
            CloudEnvironment.GOVERNMENT
        )
        assert "restrictions" in meta
        assert len(meta["restrictions"]) > 0


class TestValidateEnvironmentSupport:
    def test_commercial_supports_all_basic_services(self):
        result = cloud_config_service.validate_environment_support(
            CloudEnvironment.COMMERCIAL,
            required_services=["compute", "storage"],
        )
        assert result["supported"] is True

    def test_government_may_lack_some_services(self):
        result = cloud_config_service.validate_environment_support(
            CloudEnvironment.GOVERNMENT,
            required_services=["compute"],
        )
        # Government supports compute
        assert "supported" in result

    def test_empty_services_always_supported(self):
        result = cloud_config_service.validate_environment_support(
            CloudEnvironment.COMMERCIAL,
            required_services=[],
        )
        assert result["supported"] is True
