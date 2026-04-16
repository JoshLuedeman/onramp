"""Comprehensive tests for the GitHub Actions workflow generator and pipeline API routes."""

import zipfile
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.pipeline import IaCFormat, PipelineFormat
from app.services.github_actions_generator import (
    GitHubActionsGenerator,
    github_actions_generator,
)

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

NO_NETWORK_ARCHITECTURE = {
    "organization_size": "small",
}


# ===========================================================================
# Unit tests — GitHubActionsGenerator class
# ===========================================================================


class TestGeneratorVersion:
    """Tests for generator metadata."""

    def test_version_returns_string(self):
        assert isinstance(github_actions_generator.get_version(), str)

    def test_version_semver_format(self):
        parts = github_actions_generator.get_version().split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)


class TestListTemplates:
    """Tests for template listing."""

    def test_list_returns_list(self):
        templates = github_actions_generator.list_templates()
        assert isinstance(templates, list)

    def test_list_not_empty(self):
        templates = github_actions_generator.list_templates()
        assert len(templates) >= 4

    def test_each_template_has_required_keys(self):
        for t in github_actions_generator.list_templates():
            assert "name" in t
            assert "description" in t
            assert "iac_format" in t
            assert "pipeline_format" in t

    def test_bicep_template_exists(self):
        names = [t["name"] for t in github_actions_generator.list_templates()]
        assert "deploy-bicep" in names

    def test_terraform_template_exists(self):
        names = [t["name"] for t in github_actions_generator.list_templates()]
        assert "deploy-terraform" in names

    def test_arm_template_exists(self):
        names = [t["name"] for t in github_actions_generator.list_templates()]
        assert "deploy-arm" in names

    def test_pulumi_template_exists(self):
        names = [t["name"] for t in github_actions_generator.list_templates()]
        assert "deploy-pulumi" in names

    def test_all_templates_are_github_actions(self):
        for t in github_actions_generator.list_templates():
            assert t["pipeline_format"] == "github_actions"


class TestSingletonPattern:
    """Tests for the module-level singleton."""

    def test_singleton_is_github_actions_generator(self):
        assert isinstance(github_actions_generator, GitHubActionsGenerator)

    def test_new_instance_independent(self):
        gen = GitHubActionsGenerator()
        gen.ai_generated = True
        # Singleton state is independent
        assert isinstance(gen, GitHubActionsGenerator)


# ===========================================================================
# Bicep workflow generation tests
# ===========================================================================


class TestBicepWorkflowGeneration:
    """Tests for Bicep-specific GitHub Actions workflows."""

    def test_returns_dict(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.bicep
        )
        assert isinstance(files, dict)

    def test_contains_deploy_yml(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.bicep
        )
        assert "deploy-bicep.yml" in files

    def test_contains_validate_yml(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.bicep
        )
        assert "validate.yml" in files

    def test_contains_env_files(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.bicep
        )
        assert "env-dev.yml" in files
        assert "env-staging.yml" in files
        assert "env-prod.yml" in files

    def test_deploy_has_onramp_header(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.bicep
        )
        assert files["deploy-bicep.yml"].startswith("# OnRamp Generated")

    def test_deploy_has_oidc_login(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.bicep
        )
        content = files["deploy-bicep.yml"]
        assert "azure/login@v2" in content
        assert "AZURE_CLIENT_ID" in content
        assert "AZURE_TENANT_ID" in content
        assert "AZURE_SUBSCRIPTION_ID" in content

    def test_deploy_has_id_token_permission(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.bicep
        )
        assert "id-token: write" in files["deploy-bicep.yml"]

    def test_deploy_has_bicep_build(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.bicep
        )
        assert "az bicep build" in files["deploy-bicep.yml"]

    def test_deploy_has_what_if(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.bicep
        )
        assert "what-if" in files["deploy-bicep.yml"].lower()

    def test_deploy_has_az_deployment(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.bicep
        )
        assert "az deployment sub create" in files["deploy-bicep.yml"]

    def test_uses_correct_region(self):
        files = github_actions_generator.generate_workflows(
            MEDIUM_ARCHITECTURE, IaCFormat.bicep
        )
        assert "westus2" in files["deploy-bicep.yml"]

    def test_validate_has_bicep_lint(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.bicep
        )
        assert "az bicep build" in files["validate.yml"]


# ===========================================================================
# Terraform workflow generation tests
# ===========================================================================


class TestTerraformWorkflowGeneration:
    """Tests for Terraform-specific GitHub Actions workflows."""

    def test_contains_deploy_yml(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.terraform
        )
        assert "deploy-terraform.yml" in files

    def test_deploy_has_setup_terraform(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.terraform
        )
        assert "hashicorp/setup-terraform@v3" in files["deploy-terraform.yml"]

    def test_deploy_has_terraform_init(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.terraform
        )
        assert "terraform init" in files["deploy-terraform.yml"]

    def test_deploy_has_terraform_plan(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.terraform
        )
        assert "terraform plan" in files["deploy-terraform.yml"]

    def test_deploy_has_terraform_apply(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.terraform
        )
        assert "terraform apply" in files["deploy-terraform.yml"]

    def test_deploy_has_arm_use_oidc(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.terraform
        )
        assert "ARM_USE_OIDC: true" in files["deploy-terraform.yml"]

    def test_deploy_has_arm_client_id(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.terraform
        )
        assert "ARM_CLIENT_ID" in files["deploy-terraform.yml"]

    def test_validate_has_fmt_check(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.terraform
        )
        assert "terraform fmt -check" in files["validate.yml"]

    def test_validate_has_terraform_validate(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.terraform
        )
        assert "terraform validate" in files["validate.yml"]


# ===========================================================================
# ARM workflow generation tests
# ===========================================================================


class TestARMWorkflowGeneration:
    """Tests for ARM template-specific GitHub Actions workflows."""

    def test_contains_deploy_yml(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.arm
        )
        assert "deploy-arm.yml" in files

    def test_deploy_has_arm_validate(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.arm
        )
        assert "az deployment sub validate" in files["deploy-arm.yml"]

    def test_deploy_has_arm_deploy(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.arm
        )
        assert "az deployment sub create" in files["deploy-arm.yml"]

    def test_deploy_references_azuredeploy_json(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.arm
        )
        assert "azuredeploy.json" in files["deploy-arm.yml"]

    def test_validate_has_arm_validate(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.arm
        )
        assert "az deployment sub validate" in files["validate.yml"]


# ===========================================================================
# Pulumi workflow generation tests
# ===========================================================================


class TestPulumiWorkflowGeneration:
    """Tests for Pulumi-specific GitHub Actions workflows."""

    def test_contains_deploy_yml(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.pulumi
        )
        assert "deploy-pulumi.yml" in files

    def test_deploy_has_setup_node(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.pulumi
        )
        assert "actions/setup-node@v4" in files["deploy-pulumi.yml"]

    def test_deploy_has_pulumi_actions(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.pulumi
        )
        assert "pulumi/actions@v5" in files["deploy-pulumi.yml"]

    def test_deploy_has_pulumi_preview(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.pulumi
        )
        assert "command: preview" in files["deploy-pulumi.yml"]

    def test_deploy_has_pulumi_up(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.pulumi
        )
        assert "command: up" in files["deploy-pulumi.yml"]

    def test_deploy_has_pulumi_access_token(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.pulumi
        )
        assert "PULUMI_ACCESS_TOKEN" in files["deploy-pulumi.yml"]

    def test_deploy_has_npm_ci(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.pulumi
        )
        assert "npm ci" in files["deploy-pulumi.yml"]

    def test_validate_has_pulumi_preview(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.pulumi
        )
        assert "pulumi preview" in files["validate.yml"]


# ===========================================================================
# Environment-specific generation tests
# ===========================================================================


class TestEnvironmentGeneration:
    """Tests for environment-specific workflow generation."""

    def test_default_three_environments(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.bicep
        )
        assert "env-dev.yml" in files
        assert "env-staging.yml" in files
        assert "env-prod.yml" in files

    def test_custom_environments(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.bicep, environments=["qa", "uat"]
        )
        assert "env-qa.yml" in files
        assert "env-uat.yml" in files
        assert "env-dev.yml" not in files

    def test_single_environment(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.bicep, environments=["prod"]
        )
        assert "env-prod.yml" in files
        # 1 deploy + 1 env + 1 validate = 3 files
        assert len(files) == 3

    def test_env_file_has_environment_name(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.bicep
        )
        assert "environment: dev" in files["env-dev.yml"]
        assert "environment: staging" in files["env-staging.yml"]
        assert "environment: prod" in files["env-prod.yml"]

    def test_env_file_has_region(self):
        files = github_actions_generator.generate_workflows(
            MEDIUM_ARCHITECTURE, IaCFormat.bicep
        )
        assert "westus2" in files["env-dev.yml"]

    def test_env_file_has_project_name(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.bicep, project_name="my-lz"
        )
        assert "my-lz" in files["env-dev.yml"]

    def test_env_file_has_tags(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.bicep
        )
        assert "managed_by: onramp" in files["env-dev.yml"]

    def test_env_file_has_hub_cidr(self):
        files = github_actions_generator.generate_workflows(
            MEDIUM_ARCHITECTURE, IaCFormat.bicep
        )
        assert "10.100.0.0/16" in files["env-dev.yml"]


class TestApprovalGates:
    """Tests for approval gate generation between environments."""

    def test_deploy_has_environment_field(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.bicep
        )
        content = files["deploy-bicep.yml"]
        assert "environment: dev" in content
        assert "environment: staging" in content
        assert "environment: prod" in content

    def test_deploy_has_needs_dependency(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.bicep, include_approval_gates=True
        )
        content = files["deploy-bicep.yml"]
        assert "needs: deploy-dev" in content

    def test_deploy_has_workflow_dispatch(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.bicep
        )
        assert "workflow_dispatch" in files["deploy-bicep.yml"]


# ===========================================================================
# Region extraction tests
# ===========================================================================


class TestRegionExtraction:
    """Tests for region extraction from architecture."""

    def test_extracts_region_from_network_topology(self):
        gen = GitHubActionsGenerator()
        assert gen._extract_region(MEDIUM_ARCHITECTURE) == "westus2"

    def test_defaults_to_eastus2(self):
        gen = GitHubActionsGenerator()
        assert gen._extract_region({}) == "eastus2"

    def test_extracts_from_enterprise(self):
        gen = GitHubActionsGenerator()
        assert gen._extract_region(ENTERPRISE_ARCHITECTURE) == "northeurope"


class TestResourceGroupExtraction:
    """Tests for resource group extraction from architecture."""

    def test_default_resource_groups(self):
        gen = GitHubActionsGenerator()
        rgs = gen._extract_resource_groups({})
        assert "platform" in rgs
        assert "networking" in rgs
        assert "security" in rgs

    def test_extracts_spoke_resource_groups(self):
        gen = GitHubActionsGenerator()
        rgs = gen._extract_resource_groups(MEDIUM_ARCHITECTURE)
        assert "spoke-prod" in rgs
        assert "spoke-dev" in rgs

    def test_enterprise_spoke_resource_groups(self):
        gen = GitHubActionsGenerator()
        rgs = gen._extract_resource_groups(ENTERPRISE_ARCHITECTURE)
        assert "spoke-prod" in rgs
        assert "spoke-staging" in rgs
        assert "spoke-dev" in rgs
        assert "spoke-shared" in rgs


# ===========================================================================
# Edge case tests
# ===========================================================================


class TestEdgeCases:
    """Tests for edge cases and unusual architectures."""

    def test_empty_architecture(self):
        files = github_actions_generator.generate_workflows({}, IaCFormat.bicep)
        assert "deploy-bicep.yml" in files
        assert "validate.yml" in files

    def test_no_network_topology(self):
        files = github_actions_generator.generate_workflows(
            NO_NETWORK_ARCHITECTURE, IaCFormat.terraform
        )
        assert "deploy-terraform.yml" in files
        assert "eastus2" in files["deploy-terraform.yml"]  # default region

    def test_custom_project_name(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE,
            IaCFormat.bicep,
            project_name="contoso-lz",
        )
        assert "contoso-lz" in files["deploy-bicep.yml"]

    def test_empty_environments_list(self):
        files = github_actions_generator.generate_workflows(
            MINIMAL_ARCHITECTURE, IaCFormat.bicep, environments=[]
        )
        # Should still have deploy + validate files
        assert "deploy-bicep.yml" in files
        assert "validate.yml" in files

    def test_all_iac_formats_generate_successfully(self):
        for fmt in IaCFormat:
            files = github_actions_generator.generate_workflows(
                MINIMAL_ARCHITECTURE, fmt
            )
            assert len(files) >= 2  # at least deploy + validate

    def test_workflow_name_matches_iac_format(self):
        for fmt in IaCFormat:
            files = github_actions_generator.generate_workflows(
                MINIMAL_ARCHITECTURE, fmt
            )
            assert f"deploy-{fmt.value}.yml" in files

    def test_network_topology_not_dict(self):
        arch = {"network_topology": "flat"}
        files = github_actions_generator.generate_workflows(arch, IaCFormat.bicep)
        assert "deploy-bicep.yml" in files
        # Should fall back to default region
        assert "eastus2" in files["deploy-bicep.yml"]


# ===========================================================================
# Schema / enum tests
# ===========================================================================


class TestSchemas:
    """Tests for Pydantic schemas and enums."""

    def test_pipeline_format_github_actions(self):
        assert PipelineFormat.github_actions.value == "github_actions"

    def test_pipeline_format_azure_devops(self):
        assert PipelineFormat.azure_devops.value == "azure_devops"

    def test_iac_format_bicep(self):
        assert IaCFormat.bicep.value == "bicep"

    def test_iac_format_terraform(self):
        assert IaCFormat.terraform.value == "terraform"

    def test_iac_format_arm(self):
        assert IaCFormat.arm.value == "arm"

    def test_iac_format_pulumi(self):
        assert IaCFormat.pulumi.value == "pulumi"


# ===========================================================================
# API Route tests — using TestClient
# ===========================================================================


class TestListTemplatesRoute:
    """Tests for GET /api/pipelines/templates."""

    def test_status_200(self):
        r = client.get("/api/pipelines/templates")
        assert r.status_code == 200

    def test_response_has_templates_key(self):
        r = client.get("/api/pipelines/templates")
        assert "templates" in r.json()

    def test_templates_is_list(self):
        r = client.get("/api/pipelines/templates")
        assert isinstance(r.json()["templates"], list)

    def test_templates_have_required_fields(self):
        r = client.get("/api/pipelines/templates")
        for t in r.json()["templates"]:
            assert "name" in t
            assert "description" in t
            assert "iac_format" in t
            assert "pipeline_format" in t

    def test_at_least_four_templates(self):
        r = client.get("/api/pipelines/templates")
        assert len(r.json()["templates"]) >= 4


class TestGenerateRoute:
    """Tests for POST /api/pipelines/generate."""

    def test_status_200_bicep(self):
        r = client.post(
            "/api/pipelines/generate",
            json={"architecture": MINIMAL_ARCHITECTURE, "iac_format": "bicep"},
        )
        assert r.status_code == 200

    def test_status_200_terraform(self):
        r = client.post(
            "/api/pipelines/generate",
            json={"architecture": MINIMAL_ARCHITECTURE, "iac_format": "terraform"},
        )
        assert r.status_code == 200

    def test_status_200_arm(self):
        r = client.post(
            "/api/pipelines/generate",
            json={"architecture": MINIMAL_ARCHITECTURE, "iac_format": "arm"},
        )
        assert r.status_code == 200

    def test_status_200_pulumi(self):
        r = client.post(
            "/api/pipelines/generate",
            json={"architecture": MINIMAL_ARCHITECTURE, "iac_format": "pulumi"},
        )
        assert r.status_code == 200

    def test_response_has_files(self):
        r = client.post(
            "/api/pipelines/generate",
            json={"architecture": MINIMAL_ARCHITECTURE, "iac_format": "bicep"},
        )
        data = r.json()
        assert "files" in data
        assert "total_files" in data
        assert "iac_format" in data
        assert "pipeline_format" in data
        assert "environments" in data

    def test_files_are_list(self):
        r = client.post(
            "/api/pipelines/generate",
            json={"architecture": MINIMAL_ARCHITECTURE, "iac_format": "bicep"},
        )
        assert isinstance(r.json()["files"], list)

    def test_total_files_matches(self):
        r = client.post(
            "/api/pipelines/generate",
            json={"architecture": MINIMAL_ARCHITECTURE, "iac_format": "bicep"},
        )
        data = r.json()
        assert data["total_files"] == len(data["files"])

    def test_each_file_has_required_fields(self):
        r = client.post(
            "/api/pipelines/generate",
            json={"architecture": MEDIUM_ARCHITECTURE, "iac_format": "terraform"},
        )
        for f in r.json()["files"]:
            assert "name" in f
            assert "content" in f
            assert "size_bytes" in f
            assert "environment" in f

    def test_iac_format_in_response(self):
        r = client.post(
            "/api/pipelines/generate",
            json={"architecture": MINIMAL_ARCHITECTURE, "iac_format": "bicep"},
        )
        assert r.json()["iac_format"] == "bicep"

    def test_pipeline_format_in_response(self):
        r = client.post(
            "/api/pipelines/generate",
            json={"architecture": MINIMAL_ARCHITECTURE, "iac_format": "bicep"},
        )
        assert r.json()["pipeline_format"] == "github_actions"

    def test_environments_in_response(self):
        r = client.post(
            "/api/pipelines/generate",
            json={"architecture": MINIMAL_ARCHITECTURE, "iac_format": "bicep"},
        )
        envs = r.json()["environments"]
        assert "dev" in envs
        assert "staging" in envs
        assert "prod" in envs

    def test_custom_environments(self):
        r = client.post(
            "/api/pipelines/generate",
            json={
                "architecture": MINIMAL_ARCHITECTURE,
                "iac_format": "bicep",
                "environments": ["qa", "uat"],
            },
        )
        assert r.status_code == 200
        envs = r.json()["environments"]
        assert "qa" in envs
        assert "uat" in envs

    def test_invalid_iac_format_returns_422(self):
        r = client.post(
            "/api/pipelines/generate",
            json={"architecture": MINIMAL_ARCHITECTURE, "iac_format": "invalid"},
        )
        assert r.status_code == 422

    def test_missing_architecture_returns_422(self):
        r = client.post(
            "/api/pipelines/generate",
            json={"iac_format": "bicep"},
        )
        assert r.status_code == 422

    def test_enterprise_architecture(self):
        r = client.post(
            "/api/pipelines/generate",
            json={"architecture": ENTERPRISE_ARCHITECTURE, "iac_format": "terraform"},
        )
        assert r.status_code == 200
        assert r.json()["total_files"] >= 5


class TestDownloadRoute:
    """Tests for POST /api/pipelines/download."""

    def test_status_200(self):
        r = client.post(
            "/api/pipelines/download",
            json={"architecture": MINIMAL_ARCHITECTURE, "iac_format": "bicep"},
        )
        assert r.status_code == 200

    def test_content_type_is_zip(self):
        r = client.post(
            "/api/pipelines/download",
            json={"architecture": MINIMAL_ARCHITECTURE, "iac_format": "bicep"},
        )
        assert "application/zip" in r.headers.get("content-type", "")

    def test_content_disposition_header(self):
        r = client.post(
            "/api/pipelines/download",
            json={"architecture": MINIMAL_ARCHITECTURE, "iac_format": "bicep"},
        )
        cd = r.headers.get("content-disposition", "")
        assert "onramp-pipeline-bicep" in cd

    def test_zip_is_valid(self):
        r = client.post(
            "/api/pipelines/download",
            json={"architecture": MINIMAL_ARCHITECTURE, "iac_format": "bicep"},
        )
        buf = BytesIO(r.content)
        assert zipfile.is_zipfile(buf)

    def test_zip_contains_workflow_files(self):
        r = client.post(
            "/api/pipelines/download",
            json={"architecture": MINIMAL_ARCHITECTURE, "iac_format": "bicep"},
        )
        buf = BytesIO(r.content)
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
            assert any("deploy-bicep.yml" in n for n in names)

    def test_zip_contains_validate_workflow(self):
        r = client.post(
            "/api/pipelines/download",
            json={"architecture": MINIMAL_ARCHITECTURE, "iac_format": "terraform"},
        )
        buf = BytesIO(r.content)
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
            assert any("validate.yml" in n for n in names)

    def test_zip_files_under_github_workflows(self):
        r = client.post(
            "/api/pipelines/download",
            json={"architecture": MINIMAL_ARCHITECTURE, "iac_format": "bicep"},
        )
        buf = BytesIO(r.content)
        with zipfile.ZipFile(buf) as zf:
            for name in zf.namelist():
                assert name.startswith(".github/workflows/")

    def test_zip_content_is_yaml(self):
        r = client.post(
            "/api/pipelines/download",
            json={"architecture": MINIMAL_ARCHITECTURE, "iac_format": "bicep"},
        )
        buf = BytesIO(r.content)
        with zipfile.ZipFile(buf) as zf:
            for name in zf.namelist():
                if name.endswith(".yml"):
                    content = zf.read(name).decode("utf-8")
                    assert "# OnRamp Generated" in content

    def test_terraform_download_has_correct_filename(self):
        r = client.post(
            "/api/pipelines/download",
            json={"architecture": MINIMAL_ARCHITECTURE, "iac_format": "terraform"},
        )
        cd = r.headers.get("content-disposition", "")
        assert "onramp-pipeline-terraform" in cd

    def test_download_all_iac_formats(self):
        for fmt in ["bicep", "terraform", "arm", "pulumi"]:
            r = client.post(
                "/api/pipelines/download",
                json={"architecture": MINIMAL_ARCHITECTURE, "iac_format": fmt},
            )
            assert r.status_code == 200
            buf = BytesIO(r.content)
            assert zipfile.is_zipfile(buf)
