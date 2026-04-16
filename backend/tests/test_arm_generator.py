"""Comprehensive tests for the ARM template generator and API routes.

Tests cover:
- ARM generator service (unit tests)
- ARM template validation logic
- API route integration tests (generate, download, validate)
- Edge cases and error handling
"""

import json
import zipfile
from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.arm_generator import ARMGenerator, arm_generator

client = TestClient(app)

# ---------------------------------------------------------------------------
# Test fixtures / helpers
# ---------------------------------------------------------------------------

MINIMAL_ARCHITECTURE = {
    "organization_size": "small",
    "network_topology": {
        "primary_region": "eastus2",
        "hub": {"vnet_cidr": "10.0.0.0/16"},
        "spokes": [],
    },
    "security": {
        "azure_firewall": True,
        "bastion": True,
        "defender_for_cloud": True,
        "sentinel": False,
    },
}

MEDIUM_ARCHITECTURE = {
    "organization_size": "medium",
    "network_topology": {
        "primary_region": "westus2",
        "hub": {"vnet_cidr": "10.0.0.0/16"},
        "spokes": [
            {"name": "workload-prod", "vnet_cidr": "10.1.0.0/16"},
            {"name": "workload-dev", "vnet_cidr": "10.2.0.0/16"},
        ],
    },
    "security": {
        "azure_firewall": True,
        "bastion": True,
        "defender_for_cloud": True,
        "sentinel": True,
    },
}

LARGE_ARCHITECTURE = {
    "organization_size": "large",
    "network_topology": {
        "primary_region": "northeurope",
        "hub": {"vnet_cidr": "10.0.0.0/14"},
        "spokes": [
            {"name": "prod", "vnet_cidr": "10.4.0.0/16"},
            {"name": "staging", "vnet_cidr": "10.5.0.0/16"},
            {"name": "dev", "vnet_cidr": "10.6.0.0/16"},
            {"name": "shared-services", "vnet_cidr": "10.7.0.0/16"},
        ],
    },
    "security": {
        "azure_firewall": False,
        "bastion": False,
        "defender_for_cloud": True,
        "sentinel": True,
    },
}

EMPTY_ARCHITECTURE: dict = {}


# ===========================================================================
# ARM Generator Service — Unit Tests
# ===========================================================================


class TestARMGeneratorBasics:
    """Basic generator functionality."""

    def test_singleton_exists(self):
        assert arm_generator is not None
        assert isinstance(arm_generator, ARMGenerator)

    def test_get_version(self):
        assert arm_generator.get_version() == "1.0.0"

    def test_new_instance_ai_generated_false(self):
        gen = ARMGenerator()
        assert gen.ai_generated is False


class TestGenerateFromArchitecture:
    """Tests for generate_from_architecture with various inputs."""

    def test_returns_dict(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        assert isinstance(files, dict)

    def test_minimal_arch_file_set(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        assert "azuredeploy.json" in files
        assert "azuredeploy.parameters.json" in files
        assert "nestedtemplates/networking.json" in files
        assert "nestedtemplates/security.json" in files

    def test_file_count_minimal(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        assert len(files) == 4

    def test_medium_arch_includes_spokes(self):
        files = arm_generator.generate_from_architecture(MEDIUM_ARCHITECTURE)
        main = json.loads(files["azuredeploy.json"])
        resource_names = [
            r.get("name", "") for r in main["resources"]
        ]
        assert "spoke-workload-prod" in resource_names
        assert "spoke-workload-dev" in resource_names

    def test_large_arch_spoke_count(self):
        files = arm_generator.generate_from_architecture(LARGE_ARCHITECTURE)
        main = json.loads(files["azuredeploy.json"])
        spoke_resources = [
            r for r in main["resources"]
            if r.get("name", "").startswith("spoke-")
        ]
        assert len(spoke_resources) == 4

    def test_empty_architecture_defaults(self):
        files = arm_generator.generate_from_architecture(EMPTY_ARCHITECTURE)
        assert "azuredeploy.json" in files
        main = json.loads(files["azuredeploy.json"])
        # Defaults should be applied
        assert main["parameters"]["location"]["defaultValue"] == "eastus2"

    def test_all_files_valid_json(self):
        files = arm_generator.generate_from_architecture(MEDIUM_ARCHITECTURE)
        for name, content in files.items():
            parsed = json.loads(content)
            assert isinstance(parsed, dict), f"{name} should parse to a dict"


class TestMainTemplate:
    """Detailed tests for the main azuredeploy.json template."""

    def test_schema_field(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        main = json.loads(files["azuredeploy.json"])
        assert main["$schema"].startswith(
            "https://schema.management.azure.com/schemas/"
        )
        assert "deploymentTemplate" in main["$schema"]

    def test_content_version(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        main = json.loads(files["azuredeploy.json"])
        assert main["contentVersion"] == "1.0.0.0"

    def test_metadata_generator(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        main = json.loads(files["azuredeploy.json"])
        assert main["metadata"]["generator"] == "OnRamp"
        assert "version" in main["metadata"]
        assert "generated_at" in main["metadata"]

    def test_parameters_location(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        main = json.loads(files["azuredeploy.json"])
        assert "location" in main["parameters"]
        assert main["parameters"]["location"]["type"] == "string"
        assert main["parameters"]["location"]["defaultValue"] == "eastus2"

    def test_parameters_environment(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        main = json.loads(files["azuredeploy.json"])
        env_param = main["parameters"]["environment"]
        assert env_param["type"] == "string"
        assert "allowedValues" in env_param
        assert "prod" in env_param["allowedValues"]

    def test_parameters_hub_cidr(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        main = json.loads(files["azuredeploy.json"])
        assert "hubVnetCidr" in main["parameters"]
        assert main["parameters"]["hubVnetCidr"]["defaultValue"] == "10.0.0.0/16"

    def test_parameters_firewall_bool(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        main = json.loads(files["azuredeploy.json"])
        assert main["parameters"]["enableFirewall"]["type"] == "bool"
        assert main["parameters"]["enableFirewall"]["defaultValue"] is True

    def test_variables_resource_group_names(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        main = json.loads(files["azuredeploy.json"])
        assert "platformRgName" in main["variables"]
        assert "networkingRgName" in main["variables"]
        assert "securityRgName" in main["variables"]

    def test_variables_tags(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        main = json.loads(files["azuredeploy.json"])
        tags = main["variables"]["tags"]
        assert tags["managedBy"] == "OnRamp"
        assert tags["organizationSize"] == "small"

    def test_resources_is_list(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        main = json.loads(files["azuredeploy.json"])
        assert isinstance(main["resources"], list)
        assert len(main["resources"]) > 0

    def test_resource_groups_created(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        main = json.loads(files["azuredeploy.json"])
        rg_resources = [
            r for r in main["resources"]
            if r["type"] == "Microsoft.Resources/resourceGroups"
        ]
        assert len(rg_resources) == 3

    def test_hub_networking_deployment(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        main = json.loads(files["azuredeploy.json"])
        hub_dep = [
            r for r in main["resources"]
            if r.get("name") == "hub-networking"
        ]
        assert len(hub_dep) == 1
        assert hub_dep[0]["type"] == "Microsoft.Resources/deployments"

    def test_security_deployment(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        main = json.loads(files["azuredeploy.json"])
        sec_dep = [
            r for r in main["resources"]
            if r.get("name") == "security-resources"
        ]
        assert len(sec_dep) == 1

    def test_outputs_present(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        main = json.loads(files["azuredeploy.json"])
        assert "outputs" in main
        assert "platformResourceGroupName" in main["outputs"]
        assert "networkingResourceGroupName" in main["outputs"]
        assert "securityResourceGroupName" in main["outputs"]

    def test_region_propagation(self):
        """Region from architecture should appear in parameters."""
        files = arm_generator.generate_from_architecture(MEDIUM_ARCHITECTURE)
        main = json.loads(files["azuredeploy.json"])
        assert main["parameters"]["location"]["defaultValue"] == "westus2"

    def test_firewall_disabled(self):
        files = arm_generator.generate_from_architecture(LARGE_ARCHITECTURE)
        main = json.loads(files["azuredeploy.json"])
        assert main["parameters"]["enableFirewall"]["defaultValue"] is False


class TestParametersFile:
    """Tests for azuredeploy.parameters.json."""

    def test_parameters_schema(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        params = json.loads(files["azuredeploy.parameters.json"])
        assert "deploymentParameters" in params["$schema"]

    def test_parameters_content_version(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        params = json.loads(files["azuredeploy.parameters.json"])
        assert params["contentVersion"] == "1.0.0.0"

    def test_parameters_location_value(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        params = json.loads(files["azuredeploy.parameters.json"])
        assert params["parameters"]["location"]["value"] == "eastus2"

    def test_parameters_environment_value(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        params = json.loads(files["azuredeploy.parameters.json"])
        assert params["parameters"]["environment"]["value"] == "prod"

    def test_parameters_hub_cidr_value(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        params = json.loads(files["azuredeploy.parameters.json"])
        assert params["parameters"]["hubVnetCidr"]["value"] == "10.0.0.0/16"

    def test_parameters_region_matches_arch(self):
        files = arm_generator.generate_from_architecture(MEDIUM_ARCHITECTURE)
        params = json.loads(files["azuredeploy.parameters.json"])
        assert params["parameters"]["location"]["value"] == "westus2"


class TestNetworkingTemplate:
    """Tests for nestedtemplates/networking.json."""

    def test_networking_schema(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        net = json.loads(files["nestedtemplates/networking.json"])
        assert "deploymentTemplate" in net["$schema"]

    def test_networking_parameters(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        net = json.loads(files["nestedtemplates/networking.json"])
        assert "location" in net["parameters"]
        assert "hubVnetCidr" in net["parameters"]
        assert "enableFirewall" in net["parameters"]
        assert "enableBastion" in net["parameters"]
        assert "tags" in net["parameters"]

    def test_networking_hub_vnet_resource(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        net = json.loads(files["nestedtemplates/networking.json"])
        vnet_resources = [
            r for r in net["resources"]
            if r["type"] == "Microsoft.Network/virtualNetworks"
        ]
        assert len(vnet_resources) == 1

    def test_networking_subnets(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        net = json.loads(files["nestedtemplates/networking.json"])
        vnet = net["resources"][0]
        subnet_names = [s["name"] for s in vnet["properties"]["subnets"]]
        assert "[variables('firewallSubnetName')]" in subnet_names
        assert "[variables('bastionSubnetName')]" in subnet_names
        assert "[variables('gatewaySubnetName')]" in subnet_names

    def test_networking_outputs(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        net = json.loads(files["nestedtemplates/networking.json"])
        assert "hubVnetId" in net["outputs"]
        assert "hubVnetName" in net["outputs"]


class TestSecurityTemplate:
    """Tests for nestedtemplates/security.json."""

    def test_security_schema(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        sec = json.loads(files["nestedtemplates/security.json"])
        assert "deploymentTemplate" in sec["$schema"]

    def test_security_log_analytics(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        sec = json.loads(files["nestedtemplates/security.json"])
        law_resources = [
            r for r in sec["resources"]
            if r["type"] == "Microsoft.OperationalInsights/workspaces"
        ]
        assert len(law_resources) == 1

    def test_security_key_vault(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        sec = json.loads(files["nestedtemplates/security.json"])
        kv_resources = [
            r for r in sec["resources"]
            if r["type"] == "Microsoft.KeyVault/vaults"
        ]
        assert len(kv_resources) == 1

    def test_security_outputs(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        sec = json.loads(files["nestedtemplates/security.json"])
        assert "workspaceId" in sec["outputs"]
        assert "keyVaultName" in sec["outputs"]
        assert "defenderEnabled" in sec["outputs"]
        assert "sentinelEnabled" in sec["outputs"]

    def test_security_defender_flag(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        sec = json.loads(files["nestedtemplates/security.json"])
        assert sec["outputs"]["defenderEnabled"]["value"] is True

    def test_security_sentinel_disabled(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        sec = json.loads(files["nestedtemplates/security.json"])
        assert sec["outputs"]["sentinelEnabled"]["value"] is False

    def test_security_sentinel_enabled(self):
        files = arm_generator.generate_from_architecture(MEDIUM_ARCHITECTURE)
        sec = json.loads(files["nestedtemplates/security.json"])
        assert sec["outputs"]["sentinelEnabled"]["value"] is True


# ===========================================================================
# ARM Template Validation — Unit Tests
# ===========================================================================


class TestValidateTemplate:
    """Tests for the validate_template method."""

    def test_valid_template(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        result = arm_generator.validate_template(files["azuredeploy.json"])
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_invalid_json(self):
        result = arm_generator.validate_template("not json at all {{{")
        assert result["valid"] is False
        assert any("Invalid JSON" in e for e in result["errors"])

    def test_missing_schema(self):
        template = json.dumps({
            "contentVersion": "1.0.0.0",
            "resources": [],
        })
        result = arm_generator.validate_template(template)
        assert result["valid"] is False
        assert any("$schema" in e for e in result["errors"])

    def test_missing_content_version(self):
        template = json.dumps({
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "resources": [],
        })
        result = arm_generator.validate_template(template)
        assert result["valid"] is False
        assert any("contentVersion" in e for e in result["errors"])

    def test_missing_resources(self):
        template = json.dumps({
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
        })
        result = arm_generator.validate_template(template)
        assert result["valid"] is False
        assert any("resources" in e for e in result["errors"])

    def test_resources_not_array(self):
        template = json.dumps({
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "resources": "not-a-list",
        })
        result = arm_generator.validate_template(template)
        assert result["valid"] is False
        assert any("array" in e for e in result["errors"])

    def test_resource_missing_type(self):
        template = json.dumps({
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "resources": [{"apiVersion": "2024-01-01", "name": "test"}],
        })
        result = arm_generator.validate_template(template)
        assert result["valid"] is False
        assert any("type" in e for e in result["errors"])

    def test_parameter_missing_type_field(self):
        template = json.dumps({
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "parameters": {"badParam": {"defaultValue": "oops"}},
            "resources": [],
        })
        result = arm_generator.validate_template(template)
        assert result["valid"] is False
        assert any("badParam" in e for e in result["errors"])

    def test_warning_no_parameters(self):
        template = json.dumps({
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "resources": [],
        })
        result = arm_generator.validate_template(template)
        assert result["valid"] is True
        assert any("parameters" in w for w in result["warnings"])

    def test_warning_no_outputs(self):
        template = json.dumps({
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "resources": [],
        })
        result = arm_generator.validate_template(template)
        assert any("outputs" in w for w in result["warnings"])

    def test_warning_wrong_schema(self):
        template = json.dumps({
            "$schema": "https://example.com/wrong-schema.json#",
            "contentVersion": "1.0.0.0",
            "resources": [],
        })
        result = arm_generator.validate_template(template)
        assert any("$schema" in w for w in result["warnings"])

    def test_not_a_json_object(self):
        result = arm_generator.validate_template('"just a string"')
        assert result["valid"] is False
        assert any("JSON object" in e for e in result["errors"])

    def test_validate_networking_template(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        result = arm_generator.validate_template(
            files["nestedtemplates/networking.json"]
        )
        assert result["valid"] is True

    def test_validate_security_template(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        result = arm_generator.validate_template(
            files["nestedtemplates/security.json"]
        )
        assert result["valid"] is True

    def test_empty_string(self):
        result = arm_generator.validate_template("")
        assert result["valid"] is False


# ===========================================================================
# API Route Tests — Integration
# ===========================================================================


class TestGenerateRoute:
    """Tests for POST /api/arm/generate."""

    def test_generate_returns_200(self):
        r = client.post("/api/arm/generate", json={
            "architecture": MINIMAL_ARCHITECTURE,
            "use_ai": False,
        })
        assert r.status_code == 200

    def test_generate_response_structure(self):
        r = client.post("/api/arm/generate", json={
            "architecture": MINIMAL_ARCHITECTURE,
            "use_ai": False,
        })
        data = r.json()
        assert "files" in data
        assert "total_files" in data
        assert "ai_generated" in data

    def test_generate_file_names(self):
        r = client.post("/api/arm/generate", json={
            "architecture": MINIMAL_ARCHITECTURE,
            "use_ai": False,
        })
        data = r.json()
        file_names = [f["name"] for f in data["files"]]
        assert "azuredeploy.json" in file_names
        assert "azuredeploy.parameters.json" in file_names

    def test_generate_total_files(self):
        r = client.post("/api/arm/generate", json={
            "architecture": MINIMAL_ARCHITECTURE,
            "use_ai": False,
        })
        data = r.json()
        assert data["total_files"] == 4

    def test_generate_ai_generated_false(self):
        r = client.post("/api/arm/generate", json={
            "architecture": MINIMAL_ARCHITECTURE,
            "use_ai": False,
        })
        data = r.json()
        assert data["ai_generated"] is False

    def test_generate_files_have_size(self):
        r = client.post("/api/arm/generate", json={
            "architecture": MINIMAL_ARCHITECTURE,
            "use_ai": False,
        })
        data = r.json()
        for f in data["files"]:
            assert f["size_bytes"] > 0
            assert isinstance(f["content"], str)

    def test_generate_medium_arch(self):
        r = client.post("/api/arm/generate", json={
            "architecture": MEDIUM_ARCHITECTURE,
            "use_ai": False,
        })
        data = r.json()
        assert data["total_files"] == 4
        # Main template should contain spoke references
        main_file = next(f for f in data["files"] if f["name"] == "azuredeploy.json")
        assert "spoke-workload-prod" in main_file["content"]

    def test_generate_empty_arch(self):
        r = client.post("/api/arm/generate", json={
            "architecture": {},
            "use_ai": False,
        })
        assert r.status_code == 200

    def test_generate_missing_architecture(self):
        """Pydantic should reject a missing architecture field."""
        r = client.post("/api/arm/generate", json={"use_ai": False})
        assert r.status_code == 422


class TestDownloadRoute:
    """Tests for POST /api/arm/download."""

    def test_download_returns_200(self):
        r = client.post("/api/arm/download", json={
            "architecture": MINIMAL_ARCHITECTURE,
            "use_ai": False,
        })
        assert r.status_code == 200

    def test_download_content_type_zip(self):
        r = client.post("/api/arm/download", json={
            "architecture": MINIMAL_ARCHITECTURE,
            "use_ai": False,
        })
        assert r.headers["content-type"] == "application/zip"

    def test_download_content_disposition(self):
        r = client.post("/api/arm/download", json={
            "architecture": MINIMAL_ARCHITECTURE,
            "use_ai": False,
        })
        assert "onramp-arm-templates.zip" in r.headers["content-disposition"]

    def test_download_valid_zip(self):
        r = client.post("/api/arm/download", json={
            "architecture": MINIMAL_ARCHITECTURE,
            "use_ai": False,
        })
        zf = zipfile.ZipFile(BytesIO(r.content))
        names = zf.namelist()
        assert "azuredeploy.json" in names
        assert "azuredeploy.parameters.json" in names

    def test_download_zip_files_valid_json(self):
        r = client.post("/api/arm/download", json={
            "architecture": MINIMAL_ARCHITECTURE,
            "use_ai": False,
        })
        zf = zipfile.ZipFile(BytesIO(r.content))
        for name in zf.namelist():
            content = zf.read(name).decode("utf-8")
            parsed = json.loads(content)
            assert isinstance(parsed, dict)


class TestValidateRoute:
    """Tests for POST /api/arm/validate."""

    def test_validate_valid_template(self):
        files = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        r = client.post("/api/arm/validate", json={
            "template": files["azuredeploy.json"],
        })
        assert r.status_code == 200
        data = r.json()
        assert data["valid"] is True

    def test_validate_invalid_json(self):
        r = client.post("/api/arm/validate", json={
            "template": "{{bad json",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    def test_validate_missing_field(self):
        """Pydantic should reject missing template field."""
        r = client.post("/api/arm/validate", json={})
        assert r.status_code == 422

    def test_validate_returns_warnings(self):
        template = json.dumps({
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "resources": [],
        })
        r = client.post("/api/arm/validate", json={"template": template})
        data = r.json()
        assert data["valid"] is True
        assert len(data["warnings"]) > 0


# ===========================================================================
# AI Generation (mocked)
# ===========================================================================


class TestAIGeneration:
    """Tests for AI-based generation with mocked AI client."""

    async def test_ai_fallback_on_attribute_error(self):
        """When AI client has no generate_arm method, falls back to static."""
        gen = ARMGenerator()
        files = await gen.generate_from_architecture_with_ai(MINIMAL_ARCHITECTURE)
        assert "azuredeploy.json" in files
        assert gen.ai_generated is False

    async def test_ai_success_mock(self):
        """Test successful AI generation merge."""
        gen = ARMGenerator()
        mock_ai_files = {"custom-module.json": '{"custom": true}'}

        mock_client = AsyncMock()
        mock_client.generate_arm = AsyncMock(
            return_value=json.dumps(mock_ai_files)
        )

        with patch("app.services.ai_foundry.ai_client", mock_client):
            files = await gen.generate_from_architecture_with_ai(MINIMAL_ARCHITECTURE)
            assert "azuredeploy.json" in files
            assert gen.ai_generated is True

    async def test_ai_invalid_json_fallback(self):
        """AI returns non-JSON — should fall back gracefully."""
        gen = ARMGenerator()

        mock_client = AsyncMock()
        mock_client.generate_arm = AsyncMock(return_value="not json")

        with patch("app.services.ai_foundry.ai_client", mock_client):
            files = await gen.generate_from_architecture_with_ai(MINIMAL_ARCHITECTURE)
            assert "azuredeploy.json" in files
            assert gen.ai_generated is False

    async def test_ai_empty_dict_fallback(self):
        """AI returns empty dict — should fall back."""
        gen = ARMGenerator()

        mock_client = AsyncMock()
        mock_client.generate_arm = AsyncMock(return_value="{}")

        with patch("app.services.ai_foundry.ai_client", mock_client):
            files = await gen.generate_from_architecture_with_ai(MINIMAL_ARCHITECTURE)
            assert "azuredeploy.json" in files
            assert gen.ai_generated is False

    async def test_ai_route_with_ai_flag(self):
        """POST /generate with use_ai=True triggers AI path (fallback)."""
        r = client.post("/api/arm/generate", json={
            "architecture": MINIMAL_ARCHITECTURE,
            "use_ai": True,
        })
        # In dev mode, AI isn't configured so fallback to static
        assert r.status_code == 200
        data = r.json()
        assert "azuredeploy.json" in [f["name"] for f in data["files"]]


# ===========================================================================
# Edge Cases & Regression Tests
# ===========================================================================


class TestEdgeCases:
    """Edge case and regression tests."""

    def test_spoke_cidr_defaults(self):
        """Spokes without explicit CIDR get default."""
        arch = {
            "network_topology": {
                "spokes": [{"name": "test-spoke"}],
            },
        }
        files = arm_generator.generate_from_architecture(arch)
        main = json.loads(files["azuredeploy.json"])
        spoke_deps = [
            r for r in main["resources"]
            if r.get("name", "").startswith("spoke-")
        ]
        assert len(spoke_deps) == 1

    def test_spoke_name_defaults(self):
        """Spokes without explicit name get indexed default."""
        arch = {
            "network_topology": {
                "spokes": [{"vnet_cidr": "10.1.0.0/16"}],
            },
        }
        files = arm_generator.generate_from_architecture(arch)
        main = json.loads(files["azuredeploy.json"])
        spoke_names = [
            r["name"] for r in main["resources"]
            if r.get("name", "").startswith("spoke-")
        ]
        assert "spoke-spoke-0" in spoke_names

    def test_many_spokes(self):
        """Generator handles many spokes without error."""
        arch = {
            "network_topology": {
                "spokes": [
                    {"name": f"spoke-{i}", "vnet_cidr": f"10.{i}.0.0/16"}
                    for i in range(20)
                ],
            },
        }
        files = arm_generator.generate_from_architecture(arch)
        main = json.loads(files["azuredeploy.json"])
        spoke_deps = [
            r for r in main["resources"]
            if r.get("name", "").startswith("spoke-")
        ]
        assert len(spoke_deps) == 20

    def test_organization_size_in_tags(self):
        """Organization size propagated to tags."""
        for size in ("small", "medium", "large", "enterprise"):
            arch = {"organization_size": size}
            files = arm_generator.generate_from_architecture(arch)
            main = json.loads(files["azuredeploy.json"])
            assert main["variables"]["tags"]["organizationSize"] == size

    def test_security_flags_propagation(self):
        """Security booleans flow to parameters."""
        arch = {
            "security": {
                "azure_firewall": False,
                "bastion": False,
            },
        }
        files = arm_generator.generate_from_architecture(arch)
        main = json.loads(files["azuredeploy.json"])
        assert main["parameters"]["enableFirewall"]["defaultValue"] is False
        assert main["parameters"]["enableBastion"]["defaultValue"] is False

    def test_concurrent_generation(self):
        """Multiple generates don't interfere with each other."""
        files1 = arm_generator.generate_from_architecture(MINIMAL_ARCHITECTURE)
        files2 = arm_generator.generate_from_architecture(LARGE_ARCHITECTURE)
        main1 = json.loads(files1["azuredeploy.json"])
        main2 = json.loads(files2["azuredeploy.json"])
        assert main1["parameters"]["location"]["defaultValue"] == "eastus2"
        assert main2["parameters"]["location"]["defaultValue"] == "northeurope"

    def test_validate_all_generated_templates(self):
        """Every deployment template file from generate should pass validation."""
        files = arm_generator.generate_from_architecture(MEDIUM_ARCHITECTURE)
        for name, content in files.items():
            # Skip parameter files — they use a different schema
            if "parameters" in name:
                continue
            result = arm_generator.validate_template(content)
            assert result["valid"] is True, (
                f"{name} failed validation: {result['errors']}"
            )
