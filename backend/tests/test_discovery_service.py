"""Tests for the DiscoveryService — mock data and dev-mode scan."""

import pytest

from app.services.discovery_service import (
    CATEGORY_NETWORK,
    CATEGORY_POLICY,
    CATEGORY_RBAC,
    CATEGORY_RESOURCE,
    _mock_discovered_resources,
    _mock_discovery_results,
    discovery_service,
)


class TestCategoryConstants:
    """Test category constants are defined."""

    def test_all_categories_present(self):
        assert CATEGORY_RESOURCE == "resource"
        assert CATEGORY_POLICY == "policy"
        assert CATEGORY_RBAC == "rbac"
        assert CATEGORY_NETWORK == "network"


class TestMockDiscoveryResults:
    """Test the mock discovery result generator."""

    def test_returns_subscription_info(self):
        results = _mock_discovery_results()
        assert "subscription" in results
        assert results["subscription"]["state"] == "Enabled"

    def test_returns_resource_groups(self):
        results = _mock_discovery_results()
        assert len(results["resource_groups"]) == 3

    def test_returns_summary(self):
        results = _mock_discovery_results()
        summary = results["summary"]
        assert summary["total_resource_groups"] == 3
        assert summary["total_resources"] == 16

    def test_includes_timestamp(self):
        results = _mock_discovery_results()
        assert "scanned_at" in results


class TestMockDiscoveredResources:
    """Test the mock resource list."""

    def test_returns_list(self):
        resources = _mock_discovered_resources()
        assert isinstance(resources, list)
        assert len(resources) > 0

    def test_each_resource_has_required_fields(self):
        resources = _mock_discovered_resources()
        for r in resources:
            assert "id" in r
            assert "category" in r
            assert "resource_type" in r
            assert "name" in r

    def test_contains_all_categories(self):
        resources = _mock_discovered_resources()
        categories = {r["category"] for r in resources}
        assert CATEGORY_RESOURCE in categories
        assert CATEGORY_POLICY in categories
        assert CATEGORY_RBAC in categories
        assert CATEGORY_NETWORK in categories

    def test_resource_types_are_azure_format(self):
        resources = _mock_discovered_resources()
        for r in resources:
            assert "Microsoft." in r["resource_type"] or "/" in r["resource_type"]


class TestDevModeScan:
    """Test start_scan in dev mode (no DB)."""

    @pytest.mark.asyncio
    async def test_returns_completed_immediately(self):
        result = await discovery_service.start_scan(
            project_id="proj-1",
            tenant_id="tenant-1",
            subscription_id="sub-1",
        )
        assert result["status"] == "completed"
        assert result["project_id"] == "proj-1"
        assert "results" in result
        assert "resources" in result
        assert result["resource_count"] > 0
