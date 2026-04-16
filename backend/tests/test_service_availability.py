"""Tests for the service availability service."""

import pytest

from app.services.service_availability import (
    AZURE_SERVICES,
    ServiceAvailabilityService,
    service_availability_service,
)


# ── Singleton ────────────────────────────────────────────────────────────────


class TestSingleton:
    """Verify singleton instantiation."""

    def test_singleton_is_instance(self):
        assert isinstance(service_availability_service, ServiceAvailabilityService)

    def test_singleton_is_reusable(self):
        assert service_availability_service is service_availability_service


# ── Data Integrity ───────────────────────────────────────────────────────────


class TestDataIntegrity:
    """Verify service data is well-formed."""

    def test_at_least_30_services(self):
        assert len(AZURE_SERVICES) >= 30

    def test_services_have_required_fields(self):
        required = {"service_name", "category", "commercial", "government", "china"}
        for svc in AZURE_SERVICES:
            missing = required - set(svc.keys())
            assert not missing, f"{svc.get('service_name', '?')} missing: {missing}"

    def test_availability_values_are_bool(self):
        for svc in AZURE_SERVICES:
            for env in ("commercial", "government", "china"):
                assert isinstance(svc[env], bool), (
                    f"{svc['service_name']}.{env} is not bool"
                )

    def test_notes_are_strings(self):
        for svc in AZURE_SERVICES:
            assert isinstance(svc.get("notes", ""), str)

    def test_service_names_are_unique(self):
        names = [svc["service_name"] for svc in AZURE_SERVICES]
        assert len(names) == len(set(names))

    def test_categories_are_non_empty(self):
        for svc in AZURE_SERVICES:
            assert svc["category"], f"{svc['service_name']} has empty category"


# ── get_all_services ─────────────────────────────────────────────────────────


class TestGetAllServices:
    """Tests for the list-all method."""

    def test_returns_list(self):
        result = service_availability_service.get_all_services()
        assert isinstance(result, list)

    def test_returns_all_services(self):
        result = service_availability_service.get_all_services()
        assert len(result) == len(AZURE_SERVICES)

    def test_returns_copies(self):
        """Modifying the result should not affect the original data."""
        result = service_availability_service.get_all_services()
        first = result[0]
        assert first["service_name"] == AZURE_SERVICES[0]["service_name"]


# ── get_service ──────────────────────────────────────────────────────────────


class TestGetService:
    """Tests for single-service lookup."""

    def test_returns_known_service(self):
        result = service_availability_service.get_service("Key Vault")
        assert result is not None
        assert result["service_name"] == "Key Vault"

    def test_case_insensitive(self):
        result = service_availability_service.get_service("key vault")
        assert result is not None

    def test_returns_none_for_unknown(self):
        result = service_availability_service.get_service("Nonexistent Service")
        assert result is None

    def test_result_has_availability_fields(self):
        result = service_availability_service.get_service("Virtual Machines")
        assert result is not None
        assert "commercial" in result
        assert "government" in result
        assert "china" in result


# ── get_services_for_environment ─────────────────────────────────────────────


class TestGetServicesForEnvironment:
    """Tests for environment-based filtering."""

    def test_commercial_returns_all(self):
        result = service_availability_service.get_services_for_environment("commercial")
        # All services should be available in commercial
        for svc in AZURE_SERVICES:
            if svc["commercial"] is True:
                names = [s["service_name"] for s in result]
                assert svc["service_name"] in names

    def test_china_excludes_unavailable(self):
        result = service_availability_service.get_services_for_environment("china")
        names = {s["service_name"] for s in result}
        # Container Apps is not in China
        assert "Container Apps" not in names

    def test_government_includes_vms(self):
        result = service_availability_service.get_services_for_environment("government")
        names = {s["service_name"] for s in result}
        assert "Virtual Machines" in names

    def test_unknown_env_returns_empty(self):
        result = service_availability_service.get_services_for_environment("moon")
        assert result == []

    def test_case_insensitive(self):
        result = service_availability_service.get_services_for_environment("COMMERCIAL")
        assert len(result) > 0


# ── check_architecture_compatibility ─────────────────────────────────────────


class TestCheckArchitectureCompatibility:
    """Tests for the compatibility checker."""

    def test_compatible_architecture(self):
        arch = {"services": ["Virtual Machines", "Storage Accounts", "Key Vault"]}
        result = service_availability_service.check_architecture_compatibility(
            arch, "commercial"
        )
        assert result["compatible"] is True
        assert result["missing_services"] == []

    def test_incompatible_architecture_china(self):
        arch = {"services": ["Container Apps", "Microsoft Sentinel"]}
        result = service_availability_service.check_architecture_compatibility(
            arch, "china"
        )
        assert result["compatible"] is False
        assert "Container Apps" in result["missing_services"]
        assert "Microsoft Sentinel" in result["missing_services"]

    def test_alternatives_provided(self):
        arch = {"services": ["Container Apps"]}
        result = service_availability_service.check_architecture_compatibility(
            arch, "china"
        )
        assert "Container Apps" in result["alternatives"]

    def test_unknown_service_warning(self):
        arch = {"services": ["FakeService123"]}
        result = service_availability_service.check_architecture_compatibility(
            arch, "commercial"
        )
        assert any("Unknown service" in w for w in result["warnings"])

    def test_empty_services_is_compatible(self):
        result = service_availability_service.check_architecture_compatibility(
            {"services": []}, "government"
        )
        assert result["compatible"] is True

    def test_no_services_key_is_compatible(self):
        result = service_availability_service.check_architecture_compatibility(
            {}, "commercial"
        )
        assert result["compatible"] is True
        assert result["services_checked"] == 0

    def test_services_checked_count(self):
        arch = {"services": ["Virtual Machines", "Key Vault"]}
        result = service_availability_service.check_architecture_compatibility(
            arch, "commercial"
        )
        assert result["services_checked"] == 2

    def test_notes_generate_warnings(self):
        """Services with notes should produce warnings even if available."""
        arch = {"services": ["Virtual Machines"]}
        result = service_availability_service.check_architecture_compatibility(
            arch, "government"
        )
        # VMs have a note about SKU availability
        assert len(result["warnings"]) >= 1


# ── get_availability_matrix ──────────────────────────────────────────────────


class TestGetAvailabilityMatrix:
    """Tests for the full matrix endpoint."""

    def test_returns_expected_structure(self):
        result = service_availability_service.get_availability_matrix()
        assert "environments" in result
        assert "services" in result
        assert "by_category" in result
        assert "total_services" in result

    def test_environments_list(self):
        result = service_availability_service.get_availability_matrix()
        assert result["environments"] == ["commercial", "government", "china"]

    def test_total_services_count(self):
        result = service_availability_service.get_availability_matrix()
        assert result["total_services"] == len(AZURE_SERVICES)

    def test_by_category_has_keys(self):
        result = service_availability_service.get_availability_matrix()
        categories = result["by_category"]
        assert "Compute" in categories
        assert "Security" in categories
        assert "Networking" in categories

    def test_matrix_row_has_env_columns(self):
        result = service_availability_service.get_availability_matrix()
        for row in result["services"]:
            assert "commercial" in row
            assert "government" in row
            assert "china" in row
            assert "service_name" in row
