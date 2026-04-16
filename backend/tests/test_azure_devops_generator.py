"""Comprehensive tests for the Azure DevOps pipeline generator and API routes.

Tests cover:
- AzureDevOpsGenerator service (unit tests)
- Pipeline generation for all IaC formats (Bicep, Terraform, ARM, Pulumi)
- Variable groups, service connections, environment configuration
- Stage structure, conditions, and approval patterns
- Supplementary files (variable templates, README)
- Edge cases, empty architectures, custom environments
- API route integration tests (generate, download, templates, formats)
- YAML validity of all generated output
"""

import zipfile
from io import BytesIO

import pytest
import yaml
from fastapi.testclient import TestClient

from app.main import app
from app.services.azure_devops_generator import (
    ARM_DEPLOY_TASK,
    AZURE_CLI_TASK,
    DEFAULT_VM_IMAGE,
    IAC_FORMATS,
    TERRAFORM_INSTALLER_TASK,
    TERRAFORM_TASK,
    AzureDevOpsGenerator,
    azure_devops_generator,
)

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

AUTH_HEADER = {"Authorization": "Bearer fake-token"}


def _parse_pipeline_yaml(files: dict[str, str]) -> dict:
    """Parse the main azure-pipelines.yml from generated files."""
    content = files["azure-pipelines.yml"]
    # Skip the header comment
    return yaml.safe_load(content)


# ===========================================================================
# Generator Service — Basic Tests
# ===========================================================================


class TestGeneratorBasics:
    """Singleton and basic functionality."""

    def test_singleton_exists(self):
        assert azure_devops_generator is not None
        assert isinstance(azure_devops_generator, AzureDevOpsGenerator)

    def test_get_version(self):
        assert azure_devops_generator.get_version() == "1.0.0"

    def test_new_instance_ai_generated_false(self):
        gen = AzureDevOpsGenerator()
        assert gen.ai_generated is False

    def test_supported_formats_returns_all_four(self):
        fmts = azure_devops_generator.supported_formats()
        assert set(fmts) == {"bicep", "terraform", "arm", "pulumi"}

    def test_supported_formats_matches_constant(self):
        assert azure_devops_generator.supported_formats() == IAC_FORMATS

    def test_list_templates_returns_four(self):
        templates = azure_devops_generator.list_templates()
        assert len(templates) == 4

    def test_list_templates_all_azure_devops(self):
        for t in azure_devops_generator.list_templates():
            assert t["pipeline_format"] == "azure_devops"

    def test_list_templates_covers_all_formats(self):
        fmts = {t["iac_format"] for t in azure_devops_generator.list_templates()}
        assert fmts == {"bicep", "terraform", "arm", "pulumi"}

    def test_templates_constant_immutability(self):
        """list_templates returns a copy, not the original list."""
        templates = azure_devops_generator.list_templates()
        templates.clear()
        assert len(azure_devops_generator.list_templates()) == 4


# ===========================================================================
# Format Validation
# ===========================================================================


class TestValidateFormat:
    """Tests for validate_format."""

    def test_valid_formats(self):
        for fmt in IAC_FORMATS:
            assert azure_devops_generator.validate_format(fmt) == fmt

    def test_case_insensitive(self):
        assert azure_devops_generator.validate_format("BICEP") == "bicep"
        assert azure_devops_generator.validate_format("Terraform") == "terraform"

    def test_strips_whitespace(self):
        assert azure_devops_generator.validate_format("  arm  ") == "arm"

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Unsupported IaC format"):
            azure_devops_generator.validate_format("cloudformation")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            azure_devops_generator.validate_format("")

    def test_accepts_iac_format_enum(self):
        from app.schemas.pipeline import IaCFormat
        assert azure_devops_generator.validate_format(IaCFormat.bicep) == "bicep"
        assert azure_devops_generator.validate_format(IaCFormat.terraform) == "terraform"


# ===========================================================================
# Bicep Pipeline Generation
# ===========================================================================


class TestBicepPipeline:
    """Tests for Bicep azure-pipelines.yml generation."""

    def test_returns_dict(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        assert isinstance(files, dict)

    def test_contains_main_pipeline(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        assert "azure-pipelines.yml" in files

    def test_valid_yaml(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        pipeline = _parse_pipeline_yaml(files)
        assert isinstance(pipeline, dict)

    def test_trigger_on_main(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        pipeline = _parse_pipeline_yaml(files)
        assert "main" in pipeline["trigger"]["branches"]["include"]

    def test_pr_trigger_exists(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        pipeline = _parse_pipeline_yaml(files)
        assert "pr" in pipeline
        assert "main" in pipeline["pr"]["branches"]["include"]

    def test_pool_vm_image(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        pipeline = _parse_pipeline_yaml(files)
        assert pipeline["pool"]["vmImage"] == DEFAULT_VM_IMAGE

    def test_has_three_stages_default(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        pipeline = _parse_pipeline_yaml(files)
        # Build + Deploy_dev + Deploy_prod = 3
        assert len(pipeline["stages"]) == 3

    def test_build_stage_first(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        pipeline = _parse_pipeline_yaml(files)
        assert pipeline["stages"][0]["stage"] == "Build"

    def test_deploy_dev_stage(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        pipeline = _parse_pipeline_yaml(files)
        assert pipeline["stages"][1]["stage"] == "Deploy_dev"

    def test_deploy_prod_stage(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        pipeline = _parse_pipeline_yaml(files)
        assert pipeline["stages"][2]["stage"] == "Deploy_prod"

    def test_bicep_validation_uses_azure_cli(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        pipeline = _parse_pipeline_yaml(files)
        build_jobs = pipeline["stages"][0]["jobs"]
        steps = build_jobs[0]["steps"]
        task_steps = [s for s in steps if "task" in s]
        assert any(s["task"] == AZURE_CLI_TASK for s in task_steps)

    def test_bicep_deploy_uses_azure_cli(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        pipeline = _parse_pipeline_yaml(files)
        deploy_stage = pipeline["stages"][1]
        deploy_steps = deploy_stage["jobs"][0]["strategy"]["runOnce"]["deploy"]["steps"]
        task_steps = [s for s in deploy_steps if "task" in s]
        assert any(s["task"] == AZURE_CLI_TASK for s in task_steps)

    def test_bicep_deploy_references_region(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        pipeline = _parse_pipeline_yaml(files)
        deploy_stage = pipeline["stages"][1]
        deploy_steps = deploy_stage["jobs"][0]["strategy"]["runOnce"]["deploy"]["steps"]
        task_steps = [s for s in deploy_steps if "task" in s]
        script = task_steps[0]["inputs"]["inlineScript"]
        assert "eastus2" in script

    def test_sets_ai_generated_false(self):
        gen = AzureDevOpsGenerator()
        gen.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        assert gen.ai_generated is False


# ===========================================================================
# Terraform Pipeline Generation
# ===========================================================================


class TestTerraformPipeline:
    """Tests for Terraform azure-pipelines.yml generation."""

    def test_contains_main_pipeline(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "terraform"
        )
        assert "azure-pipelines.yml" in files

    def test_terraform_version_variable(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "terraform"
        )
        pipeline = _parse_pipeline_yaml(files)
        var_names = [v.get("name") for v in pipeline["variables"]]
        assert "terraformVersion" in var_names

    def test_backend_variables_present(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "terraform"
        )
        pipeline = _parse_pipeline_yaml(files)
        var_names = [v.get("name") for v in pipeline["variables"]]
        assert "backendResourceGroup" in var_names
        assert "backendStorageAccount" in var_names
        assert "backendContainerName" in var_names

    def test_terraform_installer_in_build(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "terraform"
        )
        pipeline = _parse_pipeline_yaml(files)
        build_steps = pipeline["stages"][0]["jobs"][0]["steps"]
        task_steps = [s for s in build_steps if "task" in s]
        assert any(s["task"] == TERRAFORM_INSTALLER_TASK for s in task_steps)

    def test_terraform_validate_in_build(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "terraform"
        )
        pipeline = _parse_pipeline_yaml(files)
        build_steps = pipeline["stages"][0]["jobs"][0]["steps"]
        task_steps = [s for s in build_steps if "task" in s]
        assert any(
            s["task"] == TERRAFORM_TASK and s["inputs"]["command"] == "validate"
            for s in task_steps
        )

    def test_terraform_plan_in_build(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "terraform"
        )
        pipeline = _parse_pipeline_yaml(files)
        build_steps = pipeline["stages"][0]["jobs"][0]["steps"]
        task_steps = [s for s in build_steps if "task" in s]
        assert any(
            s["task"] == TERRAFORM_TASK and s["inputs"]["command"] == "plan"
            for s in task_steps
        )

    def test_terraform_apply_in_deploy(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "terraform"
        )
        pipeline = _parse_pipeline_yaml(files)
        deploy_stage = pipeline["stages"][1]
        deploy_steps = (
            deploy_stage["jobs"][0]["strategy"]["runOnce"]["deploy"]["steps"]
        )
        task_steps = [s for s in deploy_steps if "task" in s]
        assert any(
            s["task"] == TERRAFORM_TASK and s["inputs"]["command"] == "apply"
            for s in task_steps
        )

    def test_terraform_deploy_uses_var_file(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "terraform"
        )
        pipeline = _parse_pipeline_yaml(files)
        deploy_stage = pipeline["stages"][1]
        deploy_steps = (
            deploy_stage["jobs"][0]["strategy"]["runOnce"]["deploy"]["steps"]
        )
        task_steps = [s for s in deploy_steps if "task" in s]
        apply_task = [
            s for s in task_steps
            if s.get("inputs", {}).get("command") == "apply"
        ][0]
        assert "dev.tfvars" in apply_task["inputs"]["commandOptions"]


# ===========================================================================
# ARM Pipeline Generation
# ===========================================================================


class TestARMPipeline:
    """Tests for ARM JSON azure-pipelines.yml generation."""

    def test_contains_main_pipeline(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "arm")
        assert "azure-pipelines.yml" in files

    def test_arm_validation_uses_arm_task(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "arm")
        pipeline = _parse_pipeline_yaml(files)
        build_steps = pipeline["stages"][0]["jobs"][0]["steps"]
        task_steps = [s for s in build_steps if "task" in s]
        assert any(s["task"] == ARM_DEPLOY_TASK for s in task_steps)

    def test_arm_validation_mode(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "arm")
        pipeline = _parse_pipeline_yaml(files)
        build_steps = pipeline["stages"][0]["jobs"][0]["steps"]
        task_steps = [s for s in build_steps if "task" in s]
        arm_tasks = [s for s in task_steps if s["task"] == ARM_DEPLOY_TASK]
        assert arm_tasks[0]["inputs"]["deploymentMode"] == "Validation"

    def test_arm_deploy_uses_incremental(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "arm")
        pipeline = _parse_pipeline_yaml(files)
        deploy_stage = pipeline["stages"][1]
        deploy_steps = (
            deploy_stage["jobs"][0]["strategy"]["runOnce"]["deploy"]["steps"]
        )
        task_steps = [s for s in deploy_steps if "task" in s]
        arm_tasks = [s for s in task_steps if s["task"] == ARM_DEPLOY_TASK]
        assert arm_tasks[0]["inputs"]["deploymentMode"] == "Incremental"

    def test_arm_deploy_references_parameters_file(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "arm")
        pipeline = _parse_pipeline_yaml(files)
        deploy_stage = pipeline["stages"][1]
        deploy_steps = (
            deploy_stage["jobs"][0]["strategy"]["runOnce"]["deploy"]["steps"]
        )
        task_steps = [s for s in deploy_steps if "task" in s]
        arm_tasks = [s for s in task_steps if s["task"] == ARM_DEPLOY_TASK]
        params_file = arm_tasks[0]["inputs"]["csmParametersFile"]
        assert "azuredeploy.parameters.dev.json" in params_file


# ===========================================================================
# Pulumi Pipeline Generation
# ===========================================================================


class TestPulumiPipeline:
    """Tests for Pulumi azure-pipelines.yml generation."""

    def test_contains_main_pipeline(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "pulumi"
        )
        assert "azure-pipelines.yml" in files

    def test_pulumi_version_variable(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "pulumi"
        )
        pipeline = _parse_pipeline_yaml(files)
        var_names = [v.get("name") for v in pipeline["variables"]]
        assert "pulumiVersion" in var_names

    def test_pulumi_stack_variable(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "pulumi"
        )
        pipeline = _parse_pipeline_yaml(files)
        var_names = [v.get("name") for v in pipeline["variables"]]
        assert "pulumiStack" in var_names

    def test_pulumi_preview_in_build(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "pulumi"
        )
        pipeline = _parse_pipeline_yaml(files)
        build_steps = pipeline["stages"][0]["jobs"][0]["steps"]
        task_steps = [s for s in build_steps if "task" in s]
        assert any(
            "pulumi preview" in s.get("inputs", {}).get("inlineScript", "")
            for s in task_steps
        )

    def test_pulumi_up_in_deploy(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "pulumi"
        )
        pipeline = _parse_pipeline_yaml(files)
        deploy_stage = pipeline["stages"][1]
        deploy_steps = (
            deploy_stage["jobs"][0]["strategy"]["runOnce"]["deploy"]["steps"]
        )
        task_steps = [s for s in deploy_steps if "task" in s]
        assert any(
            "pulumi up" in s.get("inputs", {}).get("inlineScript", "")
            for s in task_steps
        )

    def test_pulumi_access_token_env(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "pulumi"
        )
        pipeline = _parse_pipeline_yaml(files)
        build_steps = pipeline["stages"][0]["jobs"][0]["steps"]
        env_steps = [s for s in build_steps if "env" in s]
        assert any(
            "PULUMI_ACCESS_TOKEN" in s.get("env", {}) for s in env_steps
        )


# ===========================================================================
# Variables & Service Connection
# ===========================================================================


class TestVariables:
    """Tests for variable groups and service connection configuration."""

    def test_variable_group_present(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        pipeline = _parse_pipeline_yaml(files)
        groups = [v for v in pipeline["variables"] if "group" in v]
        assert any(v["group"] == "landing-zone-secrets" for v in groups)

    def test_custom_variable_group(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "bicep", variable_group="my-secrets"
        )
        pipeline = _parse_pipeline_yaml(files)
        groups = [v for v in pipeline["variables"] if "group" in v]
        assert any(v["group"] == "my-secrets" for v in groups)

    def test_service_connection_variable(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        pipeline = _parse_pipeline_yaml(files)
        named_vars = {v["name"]: v["value"] for v in pipeline["variables"] if "name" in v}
        assert named_vars["azureServiceConnection"] == "azure-service-connection"

    def test_custom_service_connection(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE,
            "bicep",
            service_connection="my-azure-sc",
        )
        pipeline = _parse_pipeline_yaml(files)
        named_vars = {v["name"]: v["value"] for v in pipeline["variables"] if "name" in v}
        assert named_vars["azureServiceConnection"] == "my-azure-sc"

    def test_location_variable_matches_architecture(self):
        files = azure_devops_generator.generate_pipeline(MEDIUM_ARCHITECTURE, "bicep")
        pipeline = _parse_pipeline_yaml(files)
        named_vars = {v["name"]: v["value"] for v in pipeline["variables"] if "name" in v}
        assert named_vars["location"] == "westus2"

    def test_org_size_variable(self):
        files = azure_devops_generator.generate_pipeline(LARGE_ARCHITECTURE, "arm")
        pipeline = _parse_pipeline_yaml(files)
        named_vars = {v["name"]: v["value"] for v in pipeline["variables"] if "name" in v}
        assert named_vars["organizationSize"] == "large"


# ===========================================================================
# Stage Structure & Conditions
# ===========================================================================


class TestStageStructure:
    """Tests for stage ordering, dependencies, and conditions."""

    def test_deploy_dev_depends_on_build(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        pipeline = _parse_pipeline_yaml(files)
        dev_stage = pipeline["stages"][1]
        assert dev_stage["dependsOn"] == "Build"

    def test_deploy_prod_depends_on_dev(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        pipeline = _parse_pipeline_yaml(files)
        prod_stage = pipeline["stages"][2]
        assert prod_stage["dependsOn"] == "Deploy_dev"

    def test_prod_condition_restricts_to_main(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        pipeline = _parse_pipeline_yaml(files)
        prod_stage = pipeline["stages"][2]
        assert "refs/heads/main" in prod_stage["condition"]

    def test_dev_condition_just_succeeded(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        pipeline = _parse_pipeline_yaml(files)
        dev_stage = pipeline["stages"][1]
        assert dev_stage["condition"] == "succeeded()"

    def test_environment_name_pattern(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        pipeline = _parse_pipeline_yaml(files)
        for stage in pipeline["stages"][1:]:
            env = stage["jobs"][0]["environment"]
            assert env.startswith("landing-zone-")

    def test_deployment_job_strategy(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        pipeline = _parse_pipeline_yaml(files)
        deploy_stage = pipeline["stages"][1]
        job = deploy_stage["jobs"][0]
        assert "runOnce" in job["strategy"]


# ===========================================================================
# Custom Environments
# ===========================================================================


class TestCustomEnvironments:
    """Tests for custom environment configurations."""

    def test_single_environment(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "bicep", environments=["staging"]
        )
        pipeline = _parse_pipeline_yaml(files)
        # Build + Deploy_staging = 2
        assert len(pipeline["stages"]) == 2

    def test_three_environments(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "bicep", environments=["dev", "staging", "prod"]
        )
        pipeline = _parse_pipeline_yaml(files)
        assert len(pipeline["stages"]) == 4  # Build + 3 deploys

    def test_stage_chaining_with_three_envs(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "bicep", environments=["dev", "staging", "prod"]
        )
        pipeline = _parse_pipeline_yaml(files)
        assert pipeline["stages"][1]["dependsOn"] == "Build"
        assert pipeline["stages"][2]["dependsOn"] == "Deploy_dev"
        assert pipeline["stages"][3]["dependsOn"] == "Deploy_staging"

    def test_four_environments(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE,
            "terraform",
            environments=["dev", "qa", "staging", "prod"],
        )
        pipeline = _parse_pipeline_yaml(files)
        assert len(pipeline["stages"]) == 5  # Build + 4 deploys


# ===========================================================================
# Supplementary Files
# ===========================================================================


class TestSupplementaryFiles:
    """Tests for variable templates and README generation."""

    def test_variable_templates_per_environment(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        assert "pipelines/variables.dev.yml" in files
        assert "pipelines/variables.prod.yml" in files

    def test_variable_template_valid_yaml(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        for key, content in files.items():
            if key.startswith("pipelines/variables."):
                parsed = yaml.safe_load(content)
                assert "variables" in parsed

    def test_variable_template_has_environment(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        content = yaml.safe_load(files["pipelines/variables.dev.yml"])
        env_var = [v for v in content["variables"] if v["name"] == "environment"]
        assert env_var[0]["value"] == "dev"

    def test_prod_variable_template_protection(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        content = yaml.safe_load(files["pipelines/variables.prod.yml"])
        protection = [
            v for v in content["variables"] if v["name"] == "deploymentProtection"
        ]
        assert protection[0]["value"] == "true"

    def test_readme_exists(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        assert "pipelines/README.md" in files

    def test_readme_mentions_service_connection(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "bicep", service_connection="my-sc"
        )
        readme = files["pipelines/README.md"]
        assert "my-sc" in readme

    def test_readme_mentions_variable_group(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "bicep", variable_group="my-vg"
        )
        readme = files["pipelines/README.md"]
        assert "my-vg" in readme

    def test_readme_mentions_iac_format(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "terraform"
        )
        readme = files["pipelines/README.md"]
        assert "Terraform" in readme

    def test_pulumi_readme_mentions_access_token(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "pulumi"
        )
        readme = files["pipelines/README.md"]
        assert "PULUMI_ACCESS_TOKEN" in readme

    def test_terraform_variable_template_has_backend_key(self):
        files = azure_devops_generator.generate_pipeline(
            MINIMAL_ARCHITECTURE, "terraform"
        )
        content = yaml.safe_load(files["pipelines/variables.dev.yml"])
        backend_vars = [v for v in content["variables"] if v["name"] == "backendKey"]
        assert len(backend_vars) == 1
        assert "dev" in backend_vars[0]["value"]


# ===========================================================================
# Empty / Edge-Case Architectures
# ===========================================================================


class TestEdgeCases:
    """Edge cases and unusual inputs."""

    def test_empty_architecture_uses_defaults(self):
        files = azure_devops_generator.generate_pipeline(EMPTY_ARCHITECTURE, "bicep")
        pipeline = _parse_pipeline_yaml(files)
        named_vars = {v["name"]: v["value"] for v in pipeline["variables"] if "name" in v}
        assert named_vars["location"] == "eastus2"
        assert named_vars["organizationSize"] == "medium"

    def test_empty_architecture_all_formats(self):
        for fmt in IAC_FORMATS:
            files = azure_devops_generator.generate_pipeline(EMPTY_ARCHITECTURE, fmt)
            assert "azure-pipelines.yml" in files
            pipeline = _parse_pipeline_yaml(files)
            assert len(pipeline["stages"]) >= 2

    def test_generate_all_formats(self):
        result = azure_devops_generator.generate_all_formats(MINIMAL_ARCHITECTURE)
        assert set(result.keys()) == {"bicep", "terraform", "arm", "pulumi"}
        for fmt, files in result.items():
            assert "azure-pipelines.yml" in files

    def test_yaml_header_comment(self):
        files = azure_devops_generator.generate_pipeline(MINIMAL_ARCHITECTURE, "bicep")
        content = files["azure-pipelines.yml"]
        assert content.startswith("# Auto-generated by OnRamp")

    def test_all_files_valid_yaml(self):
        """Every YAML file generated should be parseable."""
        for fmt in IAC_FORMATS:
            files = azure_devops_generator.generate_pipeline(
                MEDIUM_ARCHITECTURE, fmt
            )
            for name, content in files.items():
                if name.endswith((".yml", ".yaml")):
                    parsed = yaml.safe_load(content)
                    assert isinstance(parsed, dict), f"{name} failed to parse for {fmt}"

    def test_checkout_in_build_steps(self):
        for fmt in IAC_FORMATS:
            files = azure_devops_generator.generate_pipeline(
                MINIMAL_ARCHITECTURE, fmt
            )
            pipeline = _parse_pipeline_yaml(files)
            build_steps = pipeline["stages"][0]["jobs"][0]["steps"]
            assert build_steps[0] == {"checkout": "self"}

    def test_checkout_in_deploy_steps(self):
        for fmt in IAC_FORMATS:
            files = azure_devops_generator.generate_pipeline(
                MINIMAL_ARCHITECTURE, fmt
            )
            pipeline = _parse_pipeline_yaml(files)
            deploy_stage = pipeline["stages"][1]
            deploy_steps = (
                deploy_stage["jobs"][0]["strategy"]["runOnce"]["deploy"]["steps"]
            )
            assert deploy_steps[0] == {"checkout": "self"}


# ===========================================================================
# API Route Integration Tests
# ===========================================================================


@pytest.fixture(autouse=True)
def _override_auth():
    """Override auth dependency for all tests in this module."""
    from app.auth import get_current_user

    def fake_user():
        return {"sub": "test-user", "tid": "test-tenant"}

    app.dependency_overrides[get_current_user] = fake_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


class TestAPITemplates:
    """Tests for GET /api/pipelines/templates."""

    def test_templates_endpoint_returns_ok(self):
        resp = client.get("/api/pipelines/templates")
        assert resp.status_code == 200

    def test_templates_includes_azure_devops(self):
        resp = client.get("/api/pipelines/templates")
        data = resp.json()
        ado_templates = [
            t for t in data["templates"] if t["pipeline_format"] == "azure_devops"
        ]
        assert len(ado_templates) == 4

    def test_templates_includes_github_actions(self):
        resp = client.get("/api/pipelines/templates")
        data = resp.json()
        gh_templates = [
            t for t in data["templates"] if t["pipeline_format"] == "github_actions"
        ]
        assert len(gh_templates) >= 1


class TestAPIFormats:
    """Tests for GET /api/pipelines/formats."""

    def test_formats_endpoint_returns_ok(self):
        resp = client.get("/api/pipelines/formats")
        assert resp.status_code == 200

    def test_formats_lists_both_pipeline_types(self):
        resp = client.get("/api/pipelines/formats")
        data = resp.json()
        assert "azure_devops" in data["pipeline_formats"]
        assert "github_actions" in data["pipeline_formats"]

    def test_formats_lists_iac_formats(self):
        resp = client.get("/api/pipelines/formats")
        data = resp.json()
        assert set(data["iac_formats"]) == {"bicep", "terraform", "arm", "pulumi"}


class TestAPIGenerate:
    """Tests for POST /api/pipelines/generate with azure_devops format."""

    def test_generate_azure_devops_bicep(self):
        resp = client.post(
            "/api/pipelines/generate",
            json={
                "architecture": MINIMAL_ARCHITECTURE,
                "iac_format": "bicep",
                "pipeline_format": "azure_devops",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["pipeline_format"] == "azure_devops"
        assert data["iac_format"] == "bicep"
        assert data["total_files"] >= 1

    def test_generate_azure_devops_terraform(self):
        resp = client.post(
            "/api/pipelines/generate",
            json={
                "architecture": MINIMAL_ARCHITECTURE,
                "iac_format": "terraform",
                "pipeline_format": "azure_devops",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_files"] >= 1
        file_names = [f["name"] for f in data["files"]]
        assert "azure-pipelines.yml" in file_names

    def test_generate_response_file_has_size(self):
        resp = client.post(
            "/api/pipelines/generate",
            json={
                "architecture": MINIMAL_ARCHITECTURE,
                "iac_format": "bicep",
                "pipeline_format": "azure_devops",
            },
        )
        data = resp.json()
        for f in data["files"]:
            assert f["size_bytes"] > 0

    def test_generate_default_is_github_actions(self):
        resp = client.post(
            "/api/pipelines/generate",
            json={
                "architecture": MINIMAL_ARCHITECTURE,
                "iac_format": "bicep",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["pipeline_format"] == "github_actions"


class TestAPIDownload:
    """Tests for POST /api/pipelines/download with azure_devops format."""

    def test_download_azure_devops_returns_zip(self):
        resp = client.post(
            "/api/pipelines/download",
            json={
                "architecture": MINIMAL_ARCHITECTURE,
                "iac_format": "bicep",
                "pipeline_format": "azure_devops",
            },
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"

    def test_download_zip_contains_pipeline(self):
        resp = client.post(
            "/api/pipelines/download",
            json={
                "architecture": MINIMAL_ARCHITECTURE,
                "iac_format": "bicep",
                "pipeline_format": "azure_devops",
            },
        )
        buf = BytesIO(resp.content)
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
            assert "azure-pipelines.yml" in names

    def test_download_filename_in_header(self):
        resp = client.post(
            "/api/pipelines/download",
            json={
                "architecture": MINIMAL_ARCHITECTURE,
                "iac_format": "arm",
                "pipeline_format": "azure_devops",
            },
        )
        cd = resp.headers.get("content-disposition", "")
        assert "azure_devops" in cd
        assert "arm" in cd
