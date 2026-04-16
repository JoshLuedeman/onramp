"""Azure DevOps pipeline generator — creates azure-pipelines.yml from architecture definitions.

Generates CI/CD YAML pipelines for deploying landing zone IaC in four formats:
Bicep, Terraform, ARM, and Pulumi.  Each pipeline includes build validation,
multi-stage deployment (dev → prod), environment approvals/checks, Azure
service-connection configuration, and variable-group references for secrets.
"""

import logging

import yaml

from app.schemas.pipeline import IaCFormat

logger = logging.getLogger(__name__)

IAC_FORMATS: list[str] = [e.value for e in IaCFormat]

# Default Azure DevOps pool image
DEFAULT_VM_IMAGE = "ubuntu-latest"

# Azure DevOps task versions used across generated pipelines
AZURE_CLI_TASK = "AzureCLI@2"
ARM_DEPLOY_TASK = "AzureResourceManagerTemplateDeployment@3"
TERRAFORM_INSTALLER_TASK = "TerraformInstaller@1"
TERRAFORM_TASK = "TerraformTaskV4@4"

# Available Azure DevOps pipeline templates
AZURE_DEVOPS_TEMPLATES = [
    {
        "name": "deploy-bicep-ado",
        "description": "Azure DevOps pipeline to deploy Bicep templates via AzureCLI",
        "iac_format": "bicep",
        "pipeline_format": "azure_devops",
    },
    {
        "name": "deploy-terraform-ado",
        "description": "Azure DevOps pipeline to deploy Terraform with init/plan/apply",
        "iac_format": "terraform",
        "pipeline_format": "azure_devops",
    },
    {
        "name": "deploy-arm-ado",
        "description": "Azure DevOps pipeline to deploy ARM JSON templates",
        "iac_format": "arm",
        "pipeline_format": "azure_devops",
    },
    {
        "name": "deploy-pulumi-ado",
        "description": "Azure DevOps pipeline to deploy Pulumi stacks via AzureCLI",
        "iac_format": "pulumi",
        "pipeline_format": "azure_devops",
    },
]


class AzureDevOpsGenerator:
    """Generates Azure DevOps YAML pipeline definitions for Azure landing zone IaC.

    Supports Bicep, Terraform, ARM JSON, and Pulumi formats.  The generated
    ``azure-pipelines.yml`` follows Microsoft best-practice patterns:

    * Trigger on ``main`` with PR validation
    * Three stages — **Build**, **Deploy-Dev**, **Deploy-Prod**
    * Environment-based approval gates between stages
    * Variable groups for secrets / service-connection names
    * Format-specific Azure DevOps tasks
    """

    def __init__(self) -> None:
        self.ai_generated: bool = False

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_version(self) -> str:
        """Return the current generator version."""
        return "1.0.0"

    @staticmethod
    def supported_formats() -> list[str]:
        """Return the list of supported IaC format identifiers."""
        return list(IAC_FORMATS)

    def list_templates(self) -> list[dict]:
        """List all available Azure DevOps pipeline templates."""
        return list(AZURE_DEVOPS_TEMPLATES)

    def validate_format(self, iac_format: str | IaCFormat) -> str:
        """Validate and normalise an IaC format string.

        Args:
            iac_format: Raw format string or ``IaCFormat`` enum from the caller.

        Returns:
            The normalised format string.

        Raises:
            ValueError: If the format is not supported.
        """
        raw = iac_format.value if isinstance(iac_format, IaCFormat) else iac_format
        normalised = raw.strip().lower()
        if normalised not in IAC_FORMATS:
            raise ValueError(
                f"Unsupported IaC format '{iac_format}'. "
                f"Supported formats: {', '.join(IAC_FORMATS)}"
            )
        return normalised

    # ------------------------------------------------------------------
    # Top-level generation
    # ------------------------------------------------------------------

    def generate_pipeline(
        self,
        architecture: dict,
        iac_format: str | IaCFormat = "bicep",
        *,
        environments: list[str] | None = None,
        service_connection: str = "azure-service-connection",
        variable_group: str = "landing-zone-secrets",
        include_approval_gates: bool = True,
        project_name: str = "onramp-landing-zone",
    ) -> dict[str, str]:
        """Generate Azure DevOps pipeline files for a given IaC format.

        Args:
            architecture: The architecture definition JSON (from the questionnaire).
            iac_format: One of ``bicep``, ``terraform``, ``arm``, ``pulumi``.
            environments: Ordered list of deployment environments.
                Defaults to ``["dev", "prod"]``.
            service_connection: Name of the Azure service connection in Azure DevOps.
            variable_group: Name of the variable group containing secrets.

        Returns:
            A ``dict[str, str]`` mapping file names to their YAML content.
        """
        fmt = self.validate_format(iac_format)
        envs = environments or ["dev", "prod"]

        region = (
            architecture.get("network_topology", {}).get("primary_region", "eastus2")
        )
        org_size = architecture.get("organization_size", "medium")

        pipeline_dict = self._build_pipeline_dict(
            fmt,
            architecture=architecture,
            region=region,
            org_size=org_size,
            environments=envs,
            service_connection=service_connection,
            variable_group=variable_group,
        )

        pipeline_yaml = self._dict_to_yaml(pipeline_dict)
        files: dict[str, str] = {"azure-pipelines.yml": pipeline_yaml}

        # Add format-specific supplementary files
        extra = self._generate_supplementary_files(
            fmt,
            architecture=architecture,
            environments=envs,
            service_connection=service_connection,
            variable_group=variable_group,
        )
        files.update(extra)

        self.ai_generated = False
        logger.info(
            "Azure DevOps pipeline generated for %s (%d files)", fmt, len(files)
        )
        return files

    def generate_all_formats(
        self,
        architecture: dict,
        **kwargs,
    ) -> dict[str, dict[str, str]]:
        """Generate pipelines for every supported IaC format.

        Returns:
            A nested dict ``{format_name: {filename: content}}``.
        """
        result: dict[str, dict[str, str]] = {}
        for fmt in IAC_FORMATS:
            result[fmt] = self.generate_pipeline(architecture, fmt, **kwargs)
        return result

    async def generate_pipeline_with_ai(
        self,
        architecture: dict,
        iac_format: str | IaCFormat = "bicep",
        **kwargs,
    ) -> dict[str, str]:
        """Generate pipeline files, optionally enhanced by AI.

        Falls back to static generation if the AI client is unavailable or
        returns an unusable response.
        """
        from app.services.ai_foundry import ai_client

        static_files = self.generate_pipeline(architecture, iac_format, **kwargs)

        try:
            raw_response = await ai_client.generate_pipeline(
                architecture, iac_format
            )
            import json

            ai_files = json.loads(raw_response)
            if not isinstance(ai_files, dict) or not ai_files:
                raise ValueError("AI response is not a valid file mapping")
            static_files.update(ai_files)
            self.ai_generated = True
            logger.info("Azure DevOps pipeline enhanced by AI for %s", iac_format)
        except (AttributeError, TypeError, ValueError) as exc:
            logger.warning(
                "AI pipeline generation failed, using static fallback: %s", exc
            )
            self.ai_generated = False
        except Exception as exc:  # noqa: BLE001
            logger.warning("Unexpected AI error, static fallback: %s", exc)
            self.ai_generated = False

        return static_files

    # ------------------------------------------------------------------
    # Pipeline structure builders
    # ------------------------------------------------------------------

    def _build_pipeline_dict(
        self,
        iac_format: IaCFormat,
        *,
        architecture: dict,
        region: str,
        org_size: str,
        environments: list[str],
        service_connection: str,
        variable_group: str,
    ) -> dict:
        """Assemble the top-level pipeline dict for any IaC format."""
        trigger = self._build_trigger()
        pr_trigger = self._build_pr_trigger()
        variables = self._build_variables(
            iac_format,
            region=region,
            org_size=org_size,
            variable_group=variable_group,
            service_connection=service_connection,
        )
        stages = self._build_stages(
            iac_format,
            architecture=architecture,
            environments=environments,
            service_connection=service_connection,
            region=region,
        )

        pipeline: dict = {
            "trigger": trigger,
            "pr": pr_trigger,
            "pool": {"vmImage": DEFAULT_VM_IMAGE},
            "variables": variables,
            "stages": stages,
        }
        return pipeline

    # ------------------------------------------------------------------
    # Trigger / PR
    # ------------------------------------------------------------------

    @staticmethod
    def _build_trigger() -> dict:
        """CI trigger on main branch, scoped to IaC directories."""
        return {
            "branches": {"include": ["main"]},
            "paths": {"include": ["infra/*"]},
        }

    @staticmethod
    def _build_pr_trigger() -> dict:
        """PR validation trigger."""
        return {
            "branches": {"include": ["main", "develop"]},
            "paths": {"include": ["infra/*"]},
        }

    # ------------------------------------------------------------------
    # Variables
    # ------------------------------------------------------------------

    def _build_variables(
        self,
        iac_format: IaCFormat,
        *,
        region: str,
        org_size: str,
        variable_group: str,
        service_connection: str,
    ) -> list[dict]:
        """Build the variables section (inline + variable-group reference)."""
        variables: list[dict] = [
            {"group": variable_group},
            {"name": "azureServiceConnection", "value": service_connection},
            {"name": "location", "value": region},
            {"name": "organizationSize", "value": org_size},
        ]

        if iac_format == "terraform":
            variables.append({"name": "terraformVersion", "value": "1.7.0"})
            variables.append(
                {"name": "backendResourceGroup", "value": "rg-terraform-state"}
            )
            variables.append(
                {"name": "backendStorageAccount", "value": "stterraformstate"}
            )
            variables.append(
                {"name": "backendContainerName", "value": "tfstate"}
            )
        elif iac_format == "pulumi":
            variables.append({"name": "pulumiVersion", "value": "latest"})
            variables.append({"name": "pulumiStack", "value": "dev"})

        return variables

    # ------------------------------------------------------------------
    # Stages
    # ------------------------------------------------------------------

    def _build_stages(
        self,
        iac_format: IaCFormat,
        *,
        architecture: dict,
        environments: list[str],
        service_connection: str,
        region: str,
    ) -> list[dict]:
        """Build the ordered list of stages: build + one deploy per env."""
        stages: list[dict] = []

        # Build / validate stage
        stages.append(
            self._build_build_stage(iac_format, architecture=architecture)
        )

        # Deployment stages — each depends on the previous
        previous_stage = "Build"
        for env in environments:
            stage = self._build_deploy_stage(
                iac_format,
                environment=env,
                service_connection=service_connection,
                region=region,
                depends_on=previous_stage,
                architecture=architecture,
            )
            stages.append(stage)
            previous_stage = f"Deploy_{env}"

        return stages

    # ------------------------------------------------------------------
    # Build stage
    # ------------------------------------------------------------------

    def _build_build_stage(
        self, iac_format: IaCFormat, *, architecture: dict
    ) -> dict:
        """Create the Build / validation stage."""
        jobs: list[dict] = [
            {
                "job": "Validate",
                "displayName": f"Validate {iac_format.title()} templates",
                "steps": self._build_validation_steps(iac_format),
            }
        ]
        return {
            "stage": "Build",
            "displayName": "Build & Validate",
            "jobs": jobs,
        }

    def _build_validation_steps(self, iac_format: IaCFormat) -> list[dict]:
        """Return validation steps appropriate for the IaC format."""
        steps: list[dict] = [{"checkout": "self"}]

        if iac_format == "bicep":
            steps.append(
                {
                    "task": AZURE_CLI_TASK,
                    "displayName": "Validate Bicep templates",
                    "inputs": {
                        "azureSubscription": "$(azureServiceConnection)",
                        "scriptType": "bash",
                        "scriptLocation": "inlineScript",
                        "inlineScript": (
                            "az bicep build --file infra/main.bicep\n"
                            "az deployment sub validate \\\n"
                            "  --location $(location) \\\n"
                            "  --template-file infra/main.bicep \\\n"
                            "  --parameters infra/parameters.json"
                        ),
                    },
                }
            )
        elif iac_format == "terraform":
            steps.extend(
                [
                    {
                        "task": TERRAFORM_INSTALLER_TASK,
                        "displayName": "Install Terraform",
                        "inputs": {
                            "terraformVersion": "$(terraformVersion)",
                        },
                    },
                    {
                        "task": TERRAFORM_TASK,
                        "displayName": "Terraform Init",
                        "inputs": {
                            "provider": "azurerm",
                            "command": "init",
                            "workingDirectory": "$(System.DefaultWorkingDirectory)/infra",
                            "backendServiceArm": "$(azureServiceConnection)",
                            "backendAzureRmResourceGroupName": "$(backendResourceGroup)",
                            "backendAzureRmStorageAccountName": "$(backendStorageAccount)",
                            "backendAzureRmContainerName": "$(backendContainerName)",
                            "backendAzureRmKey": "landing-zone.tfstate",
                        },
                    },
                    {
                        "task": TERRAFORM_TASK,
                        "displayName": "Terraform Validate",
                        "inputs": {
                            "provider": "azurerm",
                            "command": "validate",
                            "workingDirectory": "$(System.DefaultWorkingDirectory)/infra",
                        },
                    },
                    {
                        "task": TERRAFORM_TASK,
                        "displayName": "Terraform Plan",
                        "inputs": {
                            "provider": "azurerm",
                            "command": "plan",
                            "workingDirectory": "$(System.DefaultWorkingDirectory)/infra",
                            "environmentServiceNameAzureRM": "$(azureServiceConnection)",
                            "commandOptions": "-out=tfplan",
                        },
                    },
                ]
            )
        elif iac_format == "arm":
            steps.append(
                {
                    "task": ARM_DEPLOY_TASK,
                    "displayName": "Validate ARM template",
                    "inputs": {
                        "deploymentScope": "Subscription",
                        "azureResourceManagerConnection": "$(azureServiceConnection)",
                        "location": "$(location)",
                        "templateLocation": "Linked artifact",
                        "csmFile": "$(System.DefaultWorkingDirectory)/infra/azuredeploy.json",
                        "csmParametersFile": (
                            "$(System.DefaultWorkingDirectory)/infra/azuredeploy.parameters.json"
                        ),
                        "deploymentMode": "Validation",
                    },
                }
            )
        elif iac_format == "pulumi":
            steps.extend(
                [
                    {
                        "task": AZURE_CLI_TASK,
                        "displayName": "Install Pulumi CLI",
                        "inputs": {
                            "azureSubscription": "$(azureServiceConnection)",
                            "scriptType": "bash",
                            "scriptLocation": "inlineScript",
                            "inlineScript": (
                                "curl -fsSL https://get.pulumi.com | sh\n"
                                "export PATH=$PATH:$HOME/.pulumi/bin"
                            ),
                        },
                    },
                    {
                        "task": AZURE_CLI_TASK,
                        "displayName": "Pulumi Preview",
                        "inputs": {
                            "azureSubscription": "$(azureServiceConnection)",
                            "scriptType": "bash",
                            "scriptLocation": "inlineScript",
                            "inlineScript": (
                                "cd infra\n"
                                "npm install\n"
                                "pulumi preview --stack $(pulumiStack)"
                            ),
                        },
                        "env": {
                            "PULUMI_ACCESS_TOKEN": "$(PULUMI_ACCESS_TOKEN)",
                        },
                    },
                ]
            )

        return steps

    # ------------------------------------------------------------------
    # Deploy stage
    # ------------------------------------------------------------------

    def _build_deploy_stage(
        self,
        iac_format: IaCFormat,
        *,
        environment: str,
        service_connection: str,
        region: str,
        depends_on: str,
        architecture: dict,
    ) -> dict:
        """Create a deployment stage for a specific environment."""
        stage_name = f"Deploy_{environment}"
        return {
            "stage": stage_name,
            "displayName": f"Deploy to {environment.upper()}",
            "dependsOn": depends_on,
            "condition": self._stage_condition(environment),
            "jobs": [
                {
                    "deployment": f"deploy_{environment}",
                    "displayName": f"Deploy Landing Zone ({environment})",
                    "environment": f"landing-zone-{environment}",
                    "strategy": {
                        "runOnce": {
                            "deploy": {
                                "steps": self._build_deploy_steps(
                                    iac_format,
                                    environment=environment,
                                    service_connection=service_connection,
                                    region=region,
                                    architecture=architecture,
                                ),
                            }
                        }
                    },
                }
            ],
        }

    @staticmethod
    def _stage_condition(environment: str) -> str:
        """Return the condition expression for a deployment stage."""
        if environment == "prod":
            return "and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))"
        return "succeeded()"

    def _build_deploy_steps(
        self,
        iac_format: IaCFormat,
        *,
        environment: str,
        service_connection: str,
        region: str,
        architecture: dict,
    ) -> list[dict]:
        """Return deploy steps for the given IaC format and environment."""
        steps: list[dict] = [{"checkout": "self"}]

        if iac_format == "bicep":
            steps.append(
                {
                    "task": AZURE_CLI_TASK,
                    "displayName": f"Deploy Bicep ({environment})",
                    "inputs": {
                        "azureSubscription": "$(azureServiceConnection)",
                        "scriptType": "bash",
                        "scriptLocation": "inlineScript",
                        "inlineScript": (
                            f"az deployment sub create \\\n"
                            f"  --name onramp-landing-zone-{environment} \\\n"
                            f"  --location {region} \\\n"
                            f"  --template-file infra/main.bicep \\\n"
                            f"  --parameters infra/parameters.{environment}.json"
                        ),
                    },
                }
            )
        elif iac_format == "terraform":
            steps.extend(
                [
                    {
                        "task": TERRAFORM_INSTALLER_TASK,
                        "displayName": "Install Terraform",
                        "inputs": {
                            "terraformVersion": "$(terraformVersion)",
                        },
                    },
                    {
                        "task": TERRAFORM_TASK,
                        "displayName": "Terraform Init",
                        "inputs": {
                            "provider": "azurerm",
                            "command": "init",
                            "workingDirectory": "$(System.DefaultWorkingDirectory)/infra",
                            "backendServiceArm": "$(azureServiceConnection)",
                            "backendAzureRmResourceGroupName": "$(backendResourceGroup)",
                            "backendAzureRmStorageAccountName": "$(backendStorageAccount)",
                            "backendAzureRmContainerName": "$(backendContainerName)",
                            "backendAzureRmKey": f"landing-zone-{environment}.tfstate",
                        },
                    },
                    {
                        "task": TERRAFORM_TASK,
                        "displayName": f"Terraform Apply ({environment})",
                        "inputs": {
                            "provider": "azurerm",
                            "command": "apply",
                            "workingDirectory": "$(System.DefaultWorkingDirectory)/infra",
                            "environmentServiceNameAzureRM": "$(azureServiceConnection)",
                            "commandOptions": "-auto-approve -var-file=environments/"
                            f"{environment}.tfvars",
                        },
                    },
                ]
            )
        elif iac_format == "arm":
            steps.append(
                {
                    "task": ARM_DEPLOY_TASK,
                    "displayName": f"Deploy ARM template ({environment})",
                    "inputs": {
                        "deploymentScope": "Subscription",
                        "azureResourceManagerConnection": "$(azureServiceConnection)",
                        "location": "$(location)",
                        "templateLocation": "Linked artifact",
                        "csmFile": "$(System.DefaultWorkingDirectory)/infra/azuredeploy.json",
                        "csmParametersFile": (
                            "$(System.DefaultWorkingDirectory)/infra/"
                            f"azuredeploy.parameters.{environment}.json"
                        ),
                        "deploymentMode": "Incremental",
                        "deploymentName": f"onramp-landing-zone-{environment}",
                    },
                }
            )
        elif iac_format == "pulumi":
            stack = f"{environment}"
            steps.extend(
                [
                    {
                        "task": AZURE_CLI_TASK,
                        "displayName": "Install Pulumi CLI",
                        "inputs": {
                            "azureSubscription": "$(azureServiceConnection)",
                            "scriptType": "bash",
                            "scriptLocation": "inlineScript",
                            "inlineScript": (
                                "curl -fsSL https://get.pulumi.com | sh\n"
                                "export PATH=$PATH:$HOME/.pulumi/bin"
                            ),
                        },
                    },
                    {
                        "task": AZURE_CLI_TASK,
                        "displayName": f"Pulumi Up ({environment})",
                        "inputs": {
                            "azureSubscription": "$(azureServiceConnection)",
                            "scriptType": "bash",
                            "scriptLocation": "inlineScript",
                            "inlineScript": (
                                "cd infra\n"
                                "npm install\n"
                                f"pulumi stack select {stack}\n"
                                "pulumi up --yes"
                            ),
                        },
                        "env": {
                            "PULUMI_ACCESS_TOKEN": "$(PULUMI_ACCESS_TOKEN)",
                        },
                    },
                ]
            )

        return steps

    # ------------------------------------------------------------------
    # Supplementary files
    # ------------------------------------------------------------------

    def _generate_supplementary_files(
        self,
        iac_format: IaCFormat,
        *,
        architecture: dict,
        environments: list[str],
        service_connection: str,
        variable_group: str,
    ) -> dict[str, str]:
        """Generate additional helper files alongside the main pipeline YAML."""
        files: dict[str, str] = {}

        # Environment-specific variable templates
        for env in environments:
            env_vars = self._build_environment_variables(
                iac_format, environment=env, architecture=architecture
            )
            content = self._dict_to_yaml({"variables": env_vars})
            files[f"pipelines/variables.{env}.yml"] = content

        # README for the pipeline
        files["pipelines/README.md"] = self._generate_readme(
            iac_format,
            service_connection=service_connection,
            variable_group=variable_group,
            environments=environments,
        )

        return files

    def _build_environment_variables(
        self,
        iac_format: IaCFormat,
        *,
        environment: str,
        architecture: dict,
    ) -> list[dict]:
        """Build per-environment variable overrides."""
        region = (
            architecture.get("network_topology", {}).get("primary_region", "eastus2")
        )
        variables: list[dict] = [
            {"name": "environment", "value": environment},
            {"name": "location", "value": region},
        ]

        if environment == "prod":
            variables.append({"name": "deploymentProtection", "value": "true"})
        else:
            variables.append({"name": "deploymentProtection", "value": "false"})

        if iac_format == "terraform":
            variables.append(
                {
                    "name": "backendKey",
                    "value": f"landing-zone-{environment}.tfstate",
                }
            )

        return variables

    def _generate_readme(
        self,
        iac_format: IaCFormat,
        *,
        service_connection: str,
        variable_group: str,
        environments: list[str],
    ) -> str:
        """Generate a markdown README documenting the pipeline setup."""
        env_list = ", ".join(f"`{e}`" for e in environments)
        return (
            f"# Azure DevOps Pipeline — {iac_format.title()}\n\n"
            f"Auto-generated by **OnRamp** for deploying Azure landing zone "
            f"infrastructure using {iac_format.title()}.\n\n"
            f"## Prerequisites\n\n"
            f"1. Create an Azure service connection named "
            f"**`{service_connection}`** in your Azure DevOps project.\n"
            f"2. Create a variable group named **`{variable_group}`** "
            f"containing the required secrets.\n"
            f"3. Create environments ({env_list}) with appropriate "
            f"approval checks.\n\n"
            f"## Stages\n\n"
            f"| Stage | Description |\n"
            f"|-------|-------------|\n"
            f"| Build | Validates {iac_format.title()} templates |\n"
            + "".join(
                f"| Deploy_{e} | Deploys to **{e}** environment |\n"
                for e in environments
            )
            + f"\n## Variable Group: `{variable_group}`\n\n"
            f"Ensure the following secrets are defined:\n\n"
            f"- `ARM_SUBSCRIPTION_ID`\n"
            f"- `ARM_TENANT_ID`\n"
            + (
                "- `PULUMI_ACCESS_TOKEN`\n"
                if iac_format == "pulumi"
                else ""
            )
            + "\n## Environment Approvals\n\n"
            "Configure approval gates on each environment in Azure DevOps → "
            "Pipelines → Environments.\n"
        )

    # ------------------------------------------------------------------
    # YAML serialisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _dict_to_yaml(data: dict) -> str:
        """Serialise a dict to YAML with a header comment."""
        header = "# Auto-generated by OnRamp — do not edit manually\n"
        body = yaml.dump(
            data, default_flow_style=False, sort_keys=False, width=120
        )
        return header + body


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
azure_devops_generator = AzureDevOpsGenerator()
