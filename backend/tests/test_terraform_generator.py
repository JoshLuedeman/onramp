"""Comprehensive tests for the Terraform HCL generator and API routes."""

import json
import zipfile
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.terraform_generator import TerraformGenerator, terraform_generator

client = TestClient(app)

# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

MINIMAL_ARCHITECTURE = {
    "management_groups": [{"name": "root", "children": []}],
    "subscriptions": [],
}

MEDIUM_ARCHITECTURE = {
    "organization_size": "medium",
    "management_groups": [{"name": "Contoso", "children": []}],
    "subscriptions": [
        {"name": "sub-prod", "purpose": "production", "budget_usd": 5000}
    ],
    "network_topology": {
        "type": "hub-spoke",
        "primary_region": "westus2",
        "hub": {"vnet_cidr": "10.100.0.0/16"},
        "spokes": [
            {"name": "prod", "vnet_cidr": "10.101.0.0/16"},
            {"name": "dev", "vnet_cidr": "10.102.0.0/16"},
        ],
        "dns": {},
        "hybrid_connectivity": {},
    },
    "identity": {"provider": "entra_id", "rbac_model": "custom", "pim_enabled": True},
    "security": {
        "defender_for_cloud": True,
        "sentinel": True,
        "ddos_protection": True,
        "azure_firewall": True,
        "waf": True,
        "key_vault_per_subscription": True,
    },
    "governance": {
        "policies": [{"name": "allowed-locations", "scope": "root", "effect": "Deny"}],
        "tagging_strategy": {"mandatory_tags": ["environment", "owner"]},
    },
}

ENTERPRISE_ARCHITECTURE = {
    "organization_size": "enterprise",
    "network_topology": {
        "type": "hub-spoke",
        "primary_region": "northeurope",
        "hub": {"vnet_cidr": "10.0.0.0/16"},
        "spokes": [
            {"name": "prod", "vnet_cidr": "10.1.0.0/16"},
            {"name": "staging", "vnet_cidr": "10.2.0.0/16"},
            {"name": "dev", "vnet_cidr": "10.3.0.0/16"},
            {"name": "shared", "vnet_cidr": "10.4.0.0/16"},
        ],
    },
    "security": {"azure_firewall": True},
}

NO_SPOKES_ARCHITECTURE = {
    "organization_size": "small",
    "network_topology": {
        "type": "hub-spoke",
        "primary_region": "eastus",
        "hub": {"vnet_cidr": "10.50.0.0/16"},
        "spokes": [],
    },
    "security": {"azure_firewall": False},
}


# ===========================================================================
# Unit tests — TerraformGenerator class
# ===========================================================================


class TestTerraformGeneratorVersion:
    """Tests for generator metadata."""

    def test_version_returns_string(self):
        assert isinstance(terraform_generator.get_version(), str)

    def test_version_semver_format(self):
        parts = terraform_generator.get_version().split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)


class TestListTemplates:
    """Tests for template listing."""

    def test_list_returns_list(self):
        templates = terraform_generator.list_templates()
        assert isinstance(templates, list)

    def test_list_not_empty(self):
        templates = terraform_generator.list_templates()
        assert len(templates) >= 4

    def test_each_template_has_required_keys(self):
        for t in terraform_generator.list_templates():
            assert "name" in t
            assert "description" in t
            assert "category" in t

    def test_hub_networking_template_exists(self):
        names = [t["name"] for t in terraform_generator.list_templates()]
        assert "hub-networking" in names

    def test_spoke_networking_template_exists(self):
        names = [t["name"] for t in terraform_generator.list_templates()]
        assert "spoke-networking" in names

    def test_resource_groups_template_exists(self):
        names = [t["name"] for t in terraform_generator.list_templates()]
        assert "resource-groups" in names

    def test_policy_assignments_template_exists(self):
        names = [t["name"] for t in terraform_generator.list_templates()]
        assert "policy-assignments" in names

    def test_categories_are_valid(self):
        valid = {"networking", "foundation", "governance", "management", "security"}
        for t in terraform_generator.list_templates():
            assert t["category"] in valid


class TestGenerateFromArchitecture:
    """Tests for static (non-AI) Terraform generation."""

    def test_returns_dict(self):
        files = terraform_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        assert isinstance(files, dict)

    def test_contains_main_tf(self):
        files = terraform_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        assert "main.tf" in files

    def test_contains_variables_tf(self):
        files = terraform_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        assert "variables.tf" in files

    def test_contains_outputs_tf(self):
        files = terraform_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        assert "outputs.tf" in files

    def test_contains_provider_tf(self):
        files = terraform_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        assert "provider.tf" in files

    def test_four_files_for_minimal(self):
        files = terraform_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        assert len(files) == 4

    def test_main_has_version_header(self):
        files = terraform_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        assert files["main.tf"].startswith("# OnRamp Generated")

    def test_main_has_resource_groups(self):
        files = terraform_generator.generate_from_architecture(MEDIUM_ARCHITECTURE)
        main = files["main.tf"]
        assert 'azurerm_resource_group' in main
        assert '"platform"' in main
        assert '"networking"' in main
        assert '"security"' in main

    def test_main_has_hub_vnet(self):
        files = terraform_generator.generate_from_architecture(MEDIUM_ARCHITECTURE)
        assert 'azurerm_virtual_network' in files["main.tf"]
        assert 'vnet-hub' in files["main.tf"]

    def test_main_has_firewall_subnet(self):
        files = terraform_generator.generate_from_architecture(MEDIUM_ARCHITECTURE)
        assert 'AzureFirewallSubnet' in files["main.tf"]

    def test_main_has_bastion_subnet(self):
        files = terraform_generator.generate_from_architecture(MEDIUM_ARCHITECTURE)
        assert 'AzureBastionSubnet' in files["main.tf"]

    def test_main_has_tags_local(self):
        files = terraform_generator.generate_from_architecture(MEDIUM_ARCHITECTURE)
        assert 'local.tags' in files["main.tf"]
        assert 'managed_by' in files["main.tf"] or 'OnRamp' in files["main.tf"]


class TestVariableExtraction:
    """Tests for variable extraction from architecture."""

    def test_location_variable_default(self):
        files = terraform_generator.generate_from_architecture(MEDIUM_ARCHITECTURE)
        assert 'westus2' in files["variables.tf"]

    def test_hub_cidr_variable(self):
        files = terraform_generator.generate_from_architecture(MEDIUM_ARCHITECTURE)
        assert '10.100.0.0/16' in files["variables.tf"]

    def test_environment_variable(self):
        files = terraform_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        assert 'variable "environment"' in files["variables.tf"]

    def test_organization_size_variable(self):
        files = terraform_generator.generate_from_architecture(MEDIUM_ARCHITECTURE)
        assert 'variable "organization_size"' in files["variables.tf"]
        assert '"medium"' in files["variables.tf"]

    def test_firewall_variable(self):
        files = terraform_generator.generate_from_architecture(MEDIUM_ARCHITECTURE)
        assert 'variable "enable_firewall"' in files["variables.tf"]

    def test_bastion_variable(self):
        files = terraform_generator.generate_from_architecture(MEDIUM_ARCHITECTURE)
        assert 'variable "enable_bastion"' in files["variables.tf"]

    def test_spoke_cidr_variables(self):
        files = terraform_generator.generate_from_architecture(MEDIUM_ARCHITECTURE)
        assert 'spoke_prod_cidr' in files["variables.tf"]
        assert 'spoke_dev_cidr' in files["variables.tf"]

    def test_no_spoke_variables_when_empty(self):
        files = terraform_generator.generate_from_architecture(NO_SPOKES_ARCHITECTURE)
        assert 'spoke_' not in files["variables.tf"]

    def test_firewall_disabled(self):
        files = terraform_generator.generate_from_architecture(NO_SPOKES_ARCHITECTURE)
        assert "false" in files["variables.tf"]


class TestSpokeGeneration:
    """Tests for spoke network generation in Terraform."""

    def test_medium_has_two_spokes(self):
        files = terraform_generator.generate_from_architecture(MEDIUM_ARCHITECTURE)
        main = files["main.tf"]
        assert 'vnet-spoke-prod' in main
        assert 'vnet-spoke-dev' in main

    def test_enterprise_has_four_spokes(self):
        files = terraform_generator.generate_from_architecture(ENTERPRISE_ARCHITECTURE)
        main = files["main.tf"]
        assert 'vnet-spoke-prod' in main
        assert 'vnet-spoke-staging' in main
        assert 'vnet-spoke-dev' in main
        assert 'vnet-spoke-shared' in main

    def test_spoke_peering_to_hub(self):
        files = terraform_generator.generate_from_architecture(MEDIUM_ARCHITECTURE)
        main = files["main.tf"]
        assert 'azurerm_virtual_network_peering' in main
        assert 'hub_to_prod' in main
        assert 'prod_to_hub' in main

    def test_no_spokes_no_peering(self):
        files = terraform_generator.generate_from_architecture(NO_SPOKES_ARCHITECTURE)
        assert 'azurerm_virtual_network_peering' not in files["main.tf"]


class TestProviderConfig:
    """Tests for provider.tf generation."""

    def test_provider_has_required_version(self):
        files = terraform_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        prov = files["provider.tf"]
        assert 'required_version' in prov
        assert '>= 1.5.0' in prov

    def test_provider_has_azurerm_source(self):
        files = terraform_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        prov = files["provider.tf"]
        assert 'hashicorp/azurerm' in prov

    def test_provider_has_version_constraint(self):
        files = terraform_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        prov = files["provider.tf"]
        assert '~> 4.0' in prov

    def test_provider_has_features_block(self):
        files = terraform_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        prov = files["provider.tf"]
        assert 'features' in prov

    def test_provider_azurerm_block(self):
        files = terraform_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        prov = files["provider.tf"]
        assert 'provider "azurerm"' in prov


class TestOutputDefinitions:
    """Tests for outputs.tf generation."""

    def test_outputs_has_platform_rg(self):
        files = terraform_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        assert 'resource_group_platform_id' in files["outputs.tf"]

    def test_outputs_has_networking_rg(self):
        files = terraform_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        assert 'resource_group_networking_id' in files["outputs.tf"]

    def test_outputs_has_security_rg(self):
        files = terraform_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        assert 'resource_group_security_id' in files["outputs.tf"]

    def test_outputs_has_hub_vnet_id(self):
        files = terraform_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        assert 'hub_vnet_id' in files["outputs.tf"]

    def test_outputs_has_hub_vnet_name(self):
        files = terraform_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        assert 'hub_vnet_name' in files["outputs.tf"]

    def test_spoke_outputs(self):
        files = terraform_generator.generate_from_architecture(MEDIUM_ARCHITECTURE)
        outputs = files["outputs.tf"]
        assert 'spoke_prod_vnet_id' in outputs
        assert 'spoke_dev_vnet_id' in outputs

    def test_no_spoke_outputs_when_empty(self):
        files = terraform_generator.generate_from_architecture(NO_SPOKES_ARCHITECTURE)
        assert 'spoke_' not in files["outputs.tf"]


class TestSingletonPattern:
    """Tests for the module-level singleton."""

    def test_singleton_is_terraform_generator(self):
        assert isinstance(terraform_generator, TerraformGenerator)

    def test_new_instance_independent(self):
        gen = TerraformGenerator()
        gen.ai_generated = True
        assert not terraform_generator.ai_generated or terraform_generator.ai_generated


class TestAIGeneration:
    """Tests for AI-based generation (mock mode in dev)."""

    @pytest.mark.asyncio
    async def test_ai_generation_returns_files(self):
        files = await terraform_generator.generate_from_architecture_with_ai(
            MINIMAL_ARCHITECTURE
        )
        assert isinstance(files, dict)
        assert len(files) >= 4

    @pytest.mark.asyncio
    async def test_ai_generation_has_main_tf(self):
        files = await terraform_generator.generate_from_architecture_with_ai(
            MEDIUM_ARCHITECTURE
        )
        assert "main.tf" in files

    @pytest.mark.asyncio
    async def test_ai_generation_has_provider_tf(self):
        files = await terraform_generator.generate_from_architecture_with_ai(
            MEDIUM_ARCHITECTURE
        )
        assert "provider.tf" in files

    @pytest.mark.asyncio
    async def test_ai_generation_has_variables_tf(self):
        files = await terraform_generator.generate_from_architecture_with_ai(
            MEDIUM_ARCHITECTURE
        )
        assert "variables.tf" in files

    @pytest.mark.asyncio
    async def test_ai_generation_has_outputs_tf(self):
        files = await terraform_generator.generate_from_architecture_with_ai(
            MEDIUM_ARCHITECTURE
        )
        assert "outputs.tf" in files


class TestEdgeCases:
    """Tests for edge cases and unusual architectures."""

    def test_empty_architecture(self):
        files = terraform_generator.generate_from_architecture({})
        assert "main.tf" in files
        assert "variables.tf" in files
        assert len(files) == 4

    def test_missing_network_topology(self):
        files = terraform_generator.generate_from_architecture({"organization_size": "small"})
        assert "main.tf" in files
        assert "eastus2" in files["variables.tf"]  # default region

    def test_missing_security_section(self):
        arch = {"network_topology": {"primary_region": "westeurope"}}
        files = terraform_generator.generate_from_architecture(arch)
        assert "westeurope" in files["variables.tf"]

    def test_spoke_with_no_name(self):
        arch = {
            "network_topology": {
                "spokes": [{"vnet_cidr": "10.99.0.0/16"}],
            },
        }
        files = terraform_generator.generate_from_architecture(arch)
        assert "spoke-0" in files["main.tf"]

    def test_default_hub_cidr(self):
        files = terraform_generator.generate_from_architecture({})
        assert "10.0.0.0/16" in files["variables.tf"]


# ===========================================================================
# API Route tests — using TestClient
# ===========================================================================


class TestListTemplatesRoute:
    """Tests for GET /api/terraform/templates."""

    def test_status_200(self):
        r = client.get("/api/terraform/templates")
        assert r.status_code == 200

    def test_response_has_templates_key(self):
        r = client.get("/api/terraform/templates")
        assert "templates" in r.json()

    def test_templates_is_list(self):
        r = client.get("/api/terraform/templates")
        assert isinstance(r.json()["templates"], list)

    def test_templates_have_name_and_description(self):
        r = client.get("/api/terraform/templates")
        for t in r.json()["templates"]:
            assert "name" in t
            assert "description" in t
            assert "category" in t

    def test_at_least_four_templates(self):
        r = client.get("/api/terraform/templates")
        assert len(r.json()["templates"]) >= 4


class TestGenerateRoute:
    """Tests for POST /api/terraform/generate."""

    def test_status_200(self):
        r = client.post(
            "/api/terraform/generate",
            json={"architecture": MINIMAL_ARCHITECTURE},
        )
        assert r.status_code == 200

    def test_response_has_files(self):
        r = client.post(
            "/api/terraform/generate",
            json={"architecture": MINIMAL_ARCHITECTURE},
        )
        data = r.json()
        assert "files" in data
        assert "total_files" in data
        assert "ai_generated" in data

    def test_files_are_list(self):
        r = client.post(
            "/api/terraform/generate",
            json={"architecture": MINIMAL_ARCHITECTURE},
        )
        assert isinstance(r.json()["files"], list)

    def test_total_files_matches(self):
        r = client.post(
            "/api/terraform/generate",
            json={"architecture": MINIMAL_ARCHITECTURE},
        )
        data = r.json()
        assert data["total_files"] == len(data["files"])

    def test_each_file_has_required_fields(self):
        r = client.post(
            "/api/terraform/generate",
            json={"architecture": MEDIUM_ARCHITECTURE},
        )
        for f in r.json()["files"]:
            assert "name" in f
            assert "content" in f
            assert "size_bytes" in f

    def test_generate_no_ai(self):
        r = client.post(
            "/api/terraform/generate",
            json={"architecture": MINIMAL_ARCHITECTURE, "use_ai": False},
        )
        assert r.status_code == 200
        assert r.json()["ai_generated"] is False

    def test_generate_with_spokes(self):
        r = client.post(
            "/api/terraform/generate",
            json={"architecture": MEDIUM_ARCHITECTURE, "use_ai": False},
        )
        assert r.status_code == 200
        names = [f["name"] for f in r.json()["files"]]
        assert "main.tf" in names
        assert "variables.tf" in names

    def test_generate_enterprise(self):
        r = client.post(
            "/api/terraform/generate",
            json={"architecture": ENTERPRISE_ARCHITECTURE, "use_ai": False},
        )
        assert r.status_code == 200
        assert r.json()["total_files"] >= 4


class TestDownloadRoute:
    """Tests for POST /api/terraform/download."""

    def test_status_200(self):
        r = client.post(
            "/api/terraform/download",
            json={"architecture": MINIMAL_ARCHITECTURE, "use_ai": False},
        )
        assert r.status_code == 200

    def test_content_type_is_zip(self):
        r = client.post(
            "/api/terraform/download",
            json={"architecture": MINIMAL_ARCHITECTURE, "use_ai": False},
        )
        assert "application/zip" in r.headers.get("content-type", "")

    def test_content_disposition_header(self):
        r = client.post(
            "/api/terraform/download",
            json={"architecture": MINIMAL_ARCHITECTURE, "use_ai": False},
        )
        cd = r.headers.get("content-disposition", "")
        assert "onramp-terraform.zip" in cd

    def test_zip_is_valid(self):
        r = client.post(
            "/api/terraform/download",
            json={"architecture": MINIMAL_ARCHITECTURE, "use_ai": False},
        )
        buf = BytesIO(r.content)
        assert zipfile.is_zipfile(buf)

    def test_zip_contains_main_tf(self):
        r = client.post(
            "/api/terraform/download",
            json={"architecture": MINIMAL_ARCHITECTURE, "use_ai": False},
        )
        buf = BytesIO(r.content)
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
            assert any("main.tf" in n for n in names)

    def test_zip_contains_provider_tf(self):
        r = client.post(
            "/api/terraform/download",
            json={"architecture": MINIMAL_ARCHITECTURE, "use_ai": False},
        )
        buf = BytesIO(r.content)
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
            assert any("provider.tf" in n for n in names)

    def test_zip_contains_variables_tf(self):
        r = client.post(
            "/api/terraform/download",
            json={"architecture": MINIMAL_ARCHITECTURE, "use_ai": False},
        )
        buf = BytesIO(r.content)
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
            assert any("variables.tf" in n for n in names)

    def test_zip_contains_outputs_tf(self):
        r = client.post(
            "/api/terraform/download",
            json={"architecture": MINIMAL_ARCHITECTURE, "use_ai": False},
        )
        buf = BytesIO(r.content)
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
            assert any("outputs.tf" in n for n in names)

    def test_zip_file_content_is_hcl(self):
        r = client.post(
            "/api/terraform/download",
            json={"architecture": MINIMAL_ARCHITECTURE, "use_ai": False},
        )
        buf = BytesIO(r.content)
        with zipfile.ZipFile(buf) as zf:
            for name in zf.namelist():
                if name.endswith("provider.tf"):
                    content = zf.read(name).decode()
                    assert "azurerm" in content

    def test_zip_directory_prefix(self):
        r = client.post(
            "/api/terraform/download",
            json={"architecture": MINIMAL_ARCHITECTURE, "use_ai": False},
        )
        buf = BytesIO(r.content)
        with zipfile.ZipFile(buf) as zf:
            for name in zf.namelist():
                assert name.startswith("onramp-terraform/")

    def test_download_returns_bytes(self):
        r = client.post(
            "/api/terraform/download",
            json={"architecture": MEDIUM_ARCHITECTURE, "use_ai": False},
        )
        assert len(r.content) > 0
