"""Comprehensive tests for the IaC version pinning service and API routes.

Covers the version pinning service (singleton, providers, SDKs, API versions,
freshness checks, reports), the Pydantic schemas, and the /api/versions/* routes.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.version_pinning import (
    ApiVersion,
    ArmVersionsResponse,
    BicepVersionsResponse,
    ProviderVersion,
    PulumiVersionsResponse,
    TerraformVersionsResponse,
    VersionFreshnessItem,
    VersionReport,
)
from app.services.version_pinning import (
    STALENESS_THRESHOLD_DAYS,
    VersionPinningService,
    version_pinning,
)

client = TestClient(app)


# ===========================================================================
# Schema unit tests
# ===========================================================================


class TestProviderVersionSchema:
    """Tests for the ProviderVersion Pydantic model."""

    def test_create_with_required_fields(self):
        pv = ProviderVersion(
            name="azurerm",
            version_constraint="~> 3.100",
            release_date="2024-03-15",
        )
        assert pv.name == "azurerm"
        assert pv.version_constraint == "~> 3.100"
        assert pv.release_date == "2024-03-15"

    def test_defaults_for_optional_fields(self):
        pv = ProviderVersion(
            name="azurerm",
            version_constraint="~> 3.100",
            release_date="2024-03-15",
        )
        assert pv.source == ""
        assert pv.notes == ""

    def test_all_fields_populated(self):
        pv = ProviderVersion(
            name="azurerm",
            source="hashicorp/azurerm",
            version_constraint="~> 3.100",
            release_date="2024-03-15",
            notes="Main Azure provider",
        )
        assert pv.source == "hashicorp/azurerm"
        assert pv.notes == "Main Azure provider"

    def test_serialization_round_trip(self):
        pv = ProviderVersion(
            name="random",
            source="hashicorp/random",
            version_constraint="~> 3.6",
            release_date="2024-01-10",
        )
        data = pv.model_dump()
        restored = ProviderVersion(**data)
        assert restored == pv

    def test_json_serialization(self):
        pv = ProviderVersion(
            name="azapi",
            version_constraint="~> 1.12",
            release_date="2024-02-20",
        )
        json_str = pv.model_dump_json()
        assert "azapi" in json_str
        assert "~> 1.12" in json_str


class TestApiVersionSchema:
    """Tests for the ApiVersion Pydantic model."""

    def test_create_with_required_fields(self):
        av = ApiVersion(
            resource_type="Microsoft.Network/virtualNetworks",
            api_version="2023-09-01",
            release_date="2023-09-01",
        )
        assert av.resource_type == "Microsoft.Network/virtualNetworks"
        assert av.api_version == "2023-09-01"

    def test_notes_default_empty(self):
        av = ApiVersion(
            resource_type="Microsoft.Compute/virtualMachines",
            api_version="2024-03-01",
            release_date="2024-03-01",
        )
        assert av.notes == ""

    def test_serialization_round_trip(self):
        av = ApiVersion(
            resource_type="Microsoft.Storage/storageAccounts",
            api_version="2023-05-01",
            release_date="2023-05-01",
            notes="Storage accounts",
        )
        data = av.model_dump()
        restored = ApiVersion(**data)
        assert restored == av


class TestVersionFreshnessItemSchema:
    """Tests for the VersionFreshnessItem model."""

    def test_create_stale_item(self):
        item = VersionFreshnessItem(
            name="azurerm",
            version="~> 3.100",
            release_date="2023-01-01",
            age_days=500,
            is_stale=True,
        )
        assert item.is_stale is True
        assert item.age_days == 500

    def test_create_fresh_item(self):
        item = VersionFreshnessItem(
            name="random",
            version="~> 3.6",
            release_date="2024-03-01",
            age_days=30,
            is_stale=False,
        )
        assert item.is_stale is False


class TestVersionReportSchema:
    """Tests for the VersionReport model."""

    def test_defaults(self):
        report = VersionReport()
        assert report.staleness_threshold_days == 180
        assert report.terraform == []
        assert report.total_entries == 0
        assert report.stale_count == 0

    def test_custom_threshold(self):
        report = VersionReport(staleness_threshold_days=90)
        assert report.staleness_threshold_days == 90


class TestTerraformVersionsResponseSchema:
    """Tests for the TerraformVersionsResponse model."""

    def test_create_response(self):
        resp = TerraformVersionsResponse(
            terraform_version=">= 1.5.0",
            providers=[
                ProviderVersion(
                    name="azurerm",
                    version_constraint="~> 3.100",
                    release_date="2024-03-15",
                ),
            ],
        )
        assert resp.terraform_version == ">= 1.5.0"
        assert len(resp.providers) == 1


class TestPulumiVersionsResponseSchema:
    """Tests for the PulumiVersionsResponse model."""

    def test_create_typescript_response(self):
        resp = PulumiVersionsResponse(
            language="typescript",
            packages=[
                ProviderVersion(
                    name="@pulumi/pulumi",
                    version_constraint="3.110.0",
                    release_date="2024-03-01",
                ),
            ],
        )
        assert resp.language == "typescript"
        assert len(resp.packages) == 1


class TestArmVersionsResponseSchema:
    """Tests for the ArmVersionsResponse model."""

    def test_create_response(self):
        resp = ArmVersionsResponse(
            schema_version="https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            api_versions=[],
        )
        assert "2019-04-01" in resp.schema_version
        assert resp.content_version == "1.0.0.0"


class TestBicepVersionsResponseSchema:
    """Tests for the BicepVersionsResponse model."""

    def test_default_empty(self):
        resp = BicepVersionsResponse(api_versions=[])
        assert resp.api_versions == []


# ===========================================================================
# Service unit tests — Singleton
# ===========================================================================


class TestSingletonPattern:
    """Tests for the VersionPinningService singleton."""

    def test_singleton_identity(self):
        a = VersionPinningService()
        b = VersionPinningService()
        assert a is b

    def test_module_level_instance_is_singleton(self):
        assert version_pinning is VersionPinningService()

    def test_singleton_returns_same_data(self):
        a = VersionPinningService()
        b = VersionPinningService()
        assert a.get_terraform_providers() == b.get_terraform_providers()


# ===========================================================================
# Service unit tests — Terraform
# ===========================================================================


class TestTerraformProviders:
    """Tests for Terraform provider version retrieval."""

    def test_returns_list(self):
        providers = version_pinning.get_terraform_providers()
        assert isinstance(providers, list)

    def test_not_empty(self):
        providers = version_pinning.get_terraform_providers()
        assert len(providers) > 0

    def test_all_are_provider_version(self):
        for p in version_pinning.get_terraform_providers():
            assert isinstance(p, ProviderVersion)

    def test_azurerm_present(self):
        names = [p.name for p in version_pinning.get_terraform_providers()]
        assert "azurerm" in names

    def test_azapi_present(self):
        names = [p.name for p in version_pinning.get_terraform_providers()]
        assert "azapi" in names

    def test_random_present(self):
        names = [p.name for p in version_pinning.get_terraform_providers()]
        assert "random" in names

    def test_azurerm_version_constraint(self):
        p = version_pinning.get_terraform_provider("azurerm")
        assert p is not None
        assert "~>" in p.version_constraint

    def test_azurerm_has_source(self):
        p = version_pinning.get_terraform_provider("azurerm")
        assert p is not None
        assert p.source == "hashicorp/azurerm"

    def test_each_provider_has_release_date(self):
        for p in version_pinning.get_terraform_providers():
            # Should parse as a valid date
            date.fromisoformat(p.release_date)

    def test_terraform_cli_version(self):
        assert version_pinning.terraform_cli_version == ">= 1.5.0"

    def test_get_terraform_provider_not_found(self):
        result = version_pinning.get_terraform_provider("nonexistent-provider")
        assert result is None

    def test_get_terraform_provider_returns_correct_type(self):
        result = version_pinning.get_terraform_provider("azurerm")
        assert isinstance(result, ProviderVersion)


# ===========================================================================
# Service unit tests — Pulumi
# ===========================================================================


class TestPulumiVersions:
    """Tests for Pulumi SDK version retrieval."""

    def test_typescript_returns_list(self):
        pkgs = version_pinning.get_pulumi_versions("typescript")
        assert isinstance(pkgs, list)

    def test_typescript_not_empty(self):
        pkgs = version_pinning.get_pulumi_versions("typescript")
        assert len(pkgs) > 0

    def test_python_returns_list(self):
        pkgs = version_pinning.get_pulumi_versions("python")
        assert isinstance(pkgs, list)

    def test_python_not_empty(self):
        pkgs = version_pinning.get_pulumi_versions("python")
        assert len(pkgs) > 0

    def test_typescript_has_core_sdk(self):
        names = [p.name for p in version_pinning.get_pulumi_versions("typescript")]
        assert "@pulumi/pulumi" in names

    def test_typescript_has_azure_native(self):
        names = [p.name for p in version_pinning.get_pulumi_versions("typescript")]
        assert "@pulumi/azure-native" in names

    def test_python_has_core_sdk(self):
        names = [p.name for p in version_pinning.get_pulumi_versions("python")]
        assert "pulumi" in names

    def test_python_has_azure_native(self):
        names = [p.name for p in version_pinning.get_pulumi_versions("python")]
        assert "pulumi-azure-native" in names

    def test_invalid_language_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported Pulumi language"):
            version_pinning.get_pulumi_versions("rust")  # type: ignore[arg-type]

    def test_typescript_packages_have_npm_source(self):
        for p in version_pinning.get_pulumi_versions("typescript"):
            assert p.source == "npm"

    def test_python_packages_have_pypi_source(self):
        for p in version_pinning.get_pulumi_versions("python"):
            assert p.source == "pypi"

    def test_all_packages_are_provider_version(self):
        for lang in ("typescript", "python"):
            for p in version_pinning.get_pulumi_versions(lang):  # type: ignore[arg-type]
                assert isinstance(p, ProviderVersion)


# ===========================================================================
# Service unit tests — ARM API Versions
# ===========================================================================


class TestArmApiVersions:
    """Tests for ARM API version retrieval."""

    def test_returns_list(self):
        versions = version_pinning.get_arm_api_versions()
        assert isinstance(versions, list)

    def test_not_empty(self):
        versions = version_pinning.get_arm_api_versions()
        assert len(versions) > 0

    def test_all_are_api_version(self):
        for v in version_pinning.get_arm_api_versions():
            assert isinstance(v, ApiVersion)

    def test_virtual_networks_present(self):
        types = [v.resource_type for v in version_pinning.get_arm_api_versions()]
        assert "Microsoft.Network/virtualNetworks" in types

    def test_storage_accounts_present(self):
        types = [v.resource_type for v in version_pinning.get_arm_api_versions()]
        assert "Microsoft.Storage/storageAccounts" in types

    def test_get_arm_api_version_known_type(self):
        ver = version_pinning.get_arm_api_version(
            "Microsoft.Network/virtualNetworks"
        )
        assert ver == "2023-09-01"

    def test_get_arm_api_version_case_insensitive(self):
        ver = version_pinning.get_arm_api_version(
            "microsoft.network/virtualnetworks"
        )
        assert ver == "2023-09-01"

    def test_get_arm_api_version_unknown_type_returns_default(self):
        ver = version_pinning.get_arm_api_version(
            "Microsoft.FakeService/fakeResources"
        )
        assert ver == "2023-09-01"  # default

    def test_each_arm_version_has_valid_date(self):
        for v in version_pinning.get_arm_api_versions():
            # release_date should be parseable
            date.fromisoformat(v.release_date)

    def test_key_vault_api_version(self):
        ver = version_pinning.get_arm_api_version("Microsoft.KeyVault/vaults")
        assert ver == "2023-07-01"

    def test_aks_api_version(self):
        ver = version_pinning.get_arm_api_version(
            "Microsoft.ContainerService/managedClusters"
        )
        assert ver == "2024-02-01"


# ===========================================================================
# Service unit tests — Bicep API Versions
# ===========================================================================


class TestBicepApiVersions:
    """Tests for Bicep API version retrieval."""

    def test_returns_list(self):
        versions = version_pinning.get_bicep_api_versions()
        assert isinstance(versions, list)

    def test_not_empty(self):
        versions = version_pinning.get_bicep_api_versions()
        assert len(versions) > 0

    def test_same_count_as_arm_base(self):
        # Bicep should have at least as many as ARM (could have overrides)
        arm_count = len(version_pinning.get_arm_api_versions())
        bicep_count = len(version_pinning.get_bicep_api_versions())
        assert bicep_count >= arm_count

    def test_get_bicep_api_version_known_type(self):
        ver = version_pinning.get_bicep_api_version(
            "Microsoft.Network/virtualNetworks"
        )
        assert ver == "2023-09-01"

    def test_get_bicep_api_version_unknown_type_returns_default(self):
        ver = version_pinning.get_bicep_api_version(
            "Microsoft.NonExistent/things"
        )
        assert ver == "2023-09-01"

    def test_get_bicep_api_version_case_insensitive(self):
        ver = version_pinning.get_bicep_api_version(
            "MICROSOFT.STORAGE/STORAGEACCOUNTS"
        )
        assert ver == "2023-05-01"


# ===========================================================================
# Service unit tests — Freshness Checks
# ===========================================================================


class TestFreshnessChecks:
    """Tests for version freshness checking logic."""

    def test_recent_date_is_not_stale(self):
        recent = (datetime.now(timezone.utc) - timedelta(days=10)).strftime(
            "%Y-%m-%d"
        )
        age, is_stale = version_pinning.check_freshness(recent)
        assert age <= 11
        assert is_stale is False

    def test_old_date_is_stale(self):
        old = (datetime.now(timezone.utc) - timedelta(days=365)).strftime(
            "%Y-%m-%d"
        )
        age, is_stale = version_pinning.check_freshness(old)
        assert age >= 364
        assert is_stale is True

    def test_custom_threshold(self):
        mid = (datetime.now(timezone.utc) - timedelta(days=100)).strftime(
            "%Y-%m-%d"
        )
        _, stale_at_90 = version_pinning.check_freshness(mid, threshold_days=90)
        _, stale_at_180 = version_pinning.check_freshness(
            mid, threshold_days=180
        )
        assert stale_at_90 is True
        assert stale_at_180 is False

    def test_exactly_at_threshold_is_not_stale(self):
        exact = (
            datetime.now(timezone.utc) - timedelta(days=STALENESS_THRESHOLD_DAYS)
        ).strftime("%Y-%m-%d")
        _, is_stale = version_pinning.check_freshness(exact)
        assert is_stale is False

    def test_one_day_over_threshold_is_stale(self):
        over = (
            datetime.now(timezone.utc)
            - timedelta(days=STALENESS_THRESHOLD_DAYS + 1)
        ).strftime("%Y-%m-%d")
        _, is_stale = version_pinning.check_freshness(over)
        assert is_stale is True

    def test_staleness_threshold_constant(self):
        assert STALENESS_THRESHOLD_DAYS == 180


# ===========================================================================
# Service unit tests — Version Report
# ===========================================================================


class TestVersionReport:
    """Tests for the full version freshness report."""

    def test_report_returns_version_report(self):
        report = version_pinning.get_version_report()
        assert isinstance(report, VersionReport)

    def test_report_has_terraform_section(self):
        report = version_pinning.get_version_report()
        assert isinstance(report.terraform, list)
        assert len(report.terraform) > 0

    def test_report_has_pulumi_typescript_section(self):
        report = version_pinning.get_version_report()
        assert isinstance(report.pulumi_typescript, list)
        assert len(report.pulumi_typescript) > 0

    def test_report_has_pulumi_python_section(self):
        report = version_pinning.get_version_report()
        assert isinstance(report.pulumi_python, list)
        assert len(report.pulumi_python) > 0

    def test_report_has_arm_section(self):
        report = version_pinning.get_version_report()
        assert isinstance(report.arm, list)
        assert len(report.arm) > 0

    def test_report_has_bicep_section(self):
        report = version_pinning.get_version_report()
        assert isinstance(report.bicep, list)
        assert len(report.bicep) > 0

    def test_report_total_entries_matches_sum(self):
        report = version_pinning.get_version_report()
        expected = (
            len(report.terraform)
            + len(report.pulumi_typescript)
            + len(report.pulumi_python)
            + len(report.arm)
            + len(report.bicep)
        )
        assert report.total_entries == expected

    def test_report_stale_count_nonnegative(self):
        report = version_pinning.get_version_report()
        assert report.stale_count >= 0

    def test_report_stale_count_lte_total(self):
        report = version_pinning.get_version_report()
        assert report.stale_count <= report.total_entries

    def test_report_items_are_freshness_items(self):
        report = version_pinning.get_version_report()
        for item in report.terraform:
            assert isinstance(item, VersionFreshnessItem)

    def test_report_custom_threshold(self):
        report = version_pinning.get_version_report(threshold_days=1)
        assert report.staleness_threshold_days == 1
        # With a 1-day threshold, most items should be stale
        assert report.stale_count > 0

    def test_report_high_threshold_no_stale(self):
        report = version_pinning.get_version_report(threshold_days=3650)
        assert report.stale_count == 0

    def test_report_default_threshold(self):
        report = version_pinning.get_version_report()
        assert report.staleness_threshold_days == STALENESS_THRESHOLD_DAYS


# ===========================================================================
# API route tests — GET /api/versions/terraform
# ===========================================================================


class TestTerraformRoute:
    """Tests for GET /api/versions/terraform."""

    def test_status_200(self):
        r = client.get("/api/versions/terraform")
        assert r.status_code == 200

    def test_response_has_terraform_version(self):
        data = client.get("/api/versions/terraform").json()
        assert "terraform_version" in data

    def test_response_has_providers(self):
        data = client.get("/api/versions/terraform").json()
        assert "providers" in data
        assert isinstance(data["providers"], list)

    def test_providers_not_empty(self):
        data = client.get("/api/versions/terraform").json()
        assert len(data["providers"]) > 0

    def test_provider_has_expected_fields(self):
        data = client.get("/api/versions/terraform").json()
        for p in data["providers"]:
            assert "name" in p
            assert "source" in p
            assert "version_constraint" in p
            assert "release_date" in p

    def test_azurerm_in_providers(self):
        data = client.get("/api/versions/terraform").json()
        names = [p["name"] for p in data["providers"]]
        assert "azurerm" in names


# ===========================================================================
# API route tests — GET /api/versions/pulumi/{language}
# ===========================================================================


class TestPulumiRoute:
    """Tests for GET /api/versions/pulumi/{language}."""

    def test_typescript_status_200(self):
        r = client.get("/api/versions/pulumi/typescript")
        assert r.status_code == 200

    def test_python_status_200(self):
        r = client.get("/api/versions/pulumi/python")
        assert r.status_code == 200

    def test_invalid_language_400(self):
        r = client.get("/api/versions/pulumi/rust")
        assert r.status_code == 400

    def test_invalid_language_error_message(self):
        data = client.get("/api/versions/pulumi/rust").json()
        assert "Unsupported language" in data["detail"]

    def test_typescript_response_has_language(self):
        data = client.get("/api/versions/pulumi/typescript").json()
        assert data["language"] == "typescript"

    def test_python_response_has_language(self):
        data = client.get("/api/versions/pulumi/python").json()
        assert data["language"] == "python"

    def test_response_has_packages(self):
        data = client.get("/api/versions/pulumi/typescript").json()
        assert "packages" in data
        assert isinstance(data["packages"], list)

    def test_package_has_expected_fields(self):
        data = client.get("/api/versions/pulumi/typescript").json()
        for p in data["packages"]:
            assert "name" in p
            assert "version_constraint" in p
            assert "release_date" in p

    def test_case_insensitive_language(self):
        r = client.get("/api/versions/pulumi/TypeScript")
        assert r.status_code == 200


# ===========================================================================
# API route tests — GET /api/versions/arm
# ===========================================================================


class TestArmRoute:
    """Tests for GET /api/versions/arm."""

    def test_status_200(self):
        r = client.get("/api/versions/arm")
        assert r.status_code == 200

    def test_response_has_schema_version(self):
        data = client.get("/api/versions/arm").json()
        assert "schema_version" in data

    def test_response_has_content_version(self):
        data = client.get("/api/versions/arm").json()
        assert data["content_version"] == "1.0.0.0"

    def test_response_has_api_versions(self):
        data = client.get("/api/versions/arm").json()
        assert "api_versions" in data
        assert isinstance(data["api_versions"], list)

    def test_api_versions_not_empty(self):
        data = client.get("/api/versions/arm").json()
        assert len(data["api_versions"]) > 0

    def test_api_version_entry_has_expected_fields(self):
        data = client.get("/api/versions/arm").json()
        for v in data["api_versions"]:
            assert "resource_type" in v
            assert "api_version" in v
            assert "release_date" in v


# ===========================================================================
# API route tests — GET /api/versions/bicep
# ===========================================================================


class TestBicepRoute:
    """Tests for GET /api/versions/bicep."""

    def test_status_200(self):
        r = client.get("/api/versions/bicep")
        assert r.status_code == 200

    def test_response_has_api_versions(self):
        data = client.get("/api/versions/bicep").json()
        assert "api_versions" in data
        assert isinstance(data["api_versions"], list)

    def test_api_versions_not_empty(self):
        data = client.get("/api/versions/bicep").json()
        assert len(data["api_versions"]) > 0


# ===========================================================================
# API route tests — GET /api/versions/report
# ===========================================================================


class TestReportRoute:
    """Tests for GET /api/versions/report."""

    def test_status_200(self):
        r = client.get("/api/versions/report")
        assert r.status_code == 200

    def test_response_has_all_sections(self):
        data = client.get("/api/versions/report").json()
        assert "terraform" in data
        assert "pulumi_typescript" in data
        assert "pulumi_python" in data
        assert "arm" in data
        assert "bicep" in data

    def test_response_has_totals(self):
        data = client.get("/api/versions/report").json()
        assert "total_entries" in data
        assert "stale_count" in data

    def test_response_has_threshold(self):
        data = client.get("/api/versions/report").json()
        assert "staleness_threshold_days" in data

    def test_custom_threshold_query_param(self):
        data = client.get("/api/versions/report?threshold_days=30").json()
        assert data["staleness_threshold_days"] == 30

    def test_high_threshold_zero_stale(self):
        data = client.get("/api/versions/report?threshold_days=3650").json()
        assert data["stale_count"] == 0

    def test_low_threshold_some_stale(self):
        data = client.get("/api/versions/report?threshold_days=1").json()
        assert data["stale_count"] > 0

    def test_total_entries_positive(self):
        data = client.get("/api/versions/report").json()
        assert data["total_entries"] > 0

    def test_invalid_threshold_too_low(self):
        r = client.get("/api/versions/report?threshold_days=0")
        assert r.status_code == 422

    def test_invalid_threshold_too_high(self):
        r = client.get("/api/versions/report?threshold_days=9999")
        assert r.status_code == 422

    def test_report_freshness_items_have_fields(self):
        data = client.get("/api/versions/report").json()
        for item in data["terraform"]:
            assert "name" in item
            assert "version" in item
            assert "release_date" in item
            assert "age_days" in item
            assert "is_stale" in item
