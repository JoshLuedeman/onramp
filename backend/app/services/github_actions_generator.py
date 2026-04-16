"""GitHub Actions workflow generator — creates CI/CD YAML from architecture definitions.

Generates GitHub Actions workflow files for deploying Azure landing zone IaC in
Bicep, Terraform, ARM, and Pulumi formats. Uses OIDC (federated credentials) for
Azure authentication rather than client secrets.
"""

import logging
from datetime import datetime, timezone

from app.schemas.pipeline import IaCFormat

logger = logging.getLogger(__name__)

# Available pipeline templates
PIPELINE_TEMPLATES = [
    {
        "name": "deploy-bicep",
        "description": "GitHub Actions workflow to deploy Bicep templates with Azure CLI",
        "iac_format": "bicep",
        "pipeline_format": "github_actions",
    },
    {
        "name": "deploy-terraform",
        "description": "GitHub Actions workflow to deploy Terraform with init/plan/apply",
        "iac_format": "terraform",
        "pipeline_format": "github_actions",
    },
    {
        "name": "deploy-arm",
        "description": "GitHub Actions workflow to deploy ARM JSON templates",
        "iac_format": "arm",
        "pipeline_format": "github_actions",
    },
    {
        "name": "deploy-pulumi",
        "description": "GitHub Actions workflow to deploy Pulumi stacks",
        "iac_format": "pulumi",
        "pipeline_format": "github_actions",
    },
]


class GitHubActionsGenerator:
    """Generates GitHub Actions workflow YAML from architecture definitions.

    Produces environment-specific workflows (dev, staging, prod) with OIDC-based
    Azure authentication, approval gates, and proper deployment steps for each
    supported IaC format.
    """

    def __init__(self):
        self.ai_generated: bool = False

    def get_version(self) -> str:
        """Return the current generator version."""
        return "1.0.0"

    def list_templates(self) -> list[dict]:
        """List all available pipeline templates."""
        return list(PIPELINE_TEMPLATES)

    def generate_workflows(
        self,
        architecture: dict,
        iac_format: IaCFormat,
        environments: list[str] | None = None,
        include_approval_gates: bool = True,
        project_name: str = "onramp-landing-zone",
    ) -> dict[str, str]:
        """Generate GitHub Actions workflow files from an architecture definition.

        Args:
            architecture: Architecture definition JSON.
            iac_format: The IaC format to generate workflows for.
            environments: Target deployment environments. Defaults to dev/staging/prod.
            include_approval_gates: Whether to include environment protection rules.
            project_name: Project name used in workflow naming and file paths.

        Returns:
            A dict of {filename: yaml_content}.
        """
        if environments is None:
            environments = ["dev", "staging", "prod"]

        files: dict[str, str] = {}

        # Extract architecture metadata
        primary_region = self._extract_region(architecture)
        resource_groups = self._extract_resource_groups(architecture)

        # Generate main deployment workflow
        main_workflow = self._generate_main_workflow(
            iac_format=iac_format,
            environments=environments,
            include_approval_gates=include_approval_gates,
            project_name=project_name,
            primary_region=primary_region,
            resource_groups=resource_groups,
            architecture=architecture,
        )
        main_filename = f"deploy-{iac_format.value}.yml"
        files[main_filename] = main_workflow

        # Generate environment-specific parameter files
        for env in environments:
            env_file = self._generate_env_params(
                iac_format=iac_format,
                environment=env,
                primary_region=primary_region,
                project_name=project_name,
                architecture=architecture,
            )
            env_filename = f"env-{env}.yml"
            files[env_filename] = env_file

        # Generate reusable workflow for validation
        validate_file = self._generate_validate_workflow(
            iac_format=iac_format,
            project_name=project_name,
            primary_region=primary_region,
        )
        files["validate.yml"] = validate_file

        self.ai_generated = False
        logger.info(
            "Generated %d workflow files for %s (envs: %s)",
            len(files),
            iac_format.value,
            ", ".join(environments),
        )
        return files

    # ── Internal helpers ──────────────────────────────────────────────────

    def _extract_region(self, architecture: dict) -> str:
        """Extract the primary Azure region from architecture definition."""
        network = architecture.get("network_topology", {})
        if isinstance(network, dict):
            region = network.get("primary_region", "")
            if region:
                return region
        return "eastus2"

    def _extract_resource_groups(self, architecture: dict) -> list[str]:
        """Extract resource group names from architecture definition."""
        rgs = ["platform", "networking", "security"]
        network = architecture.get("network_topology", {})
        if isinstance(network, dict):
            spokes = network.get("spokes", [])
            if isinstance(spokes, list):
                for spoke in spokes:
                    if isinstance(spoke, dict):
                        name = spoke.get("name", "")
                        if name:
                            rgs.append(f"spoke-{name}")
        return rgs

    def _oidc_login_step(self) -> str:
        """Return the azure/login OIDC step YAML block."""
        return (
            "      - name: Azure Login (OIDC)\n"
            "        uses: azure/login@v2\n"
            "        with:\n"
            "          client-id: ${{ secrets.AZURE_CLIENT_ID }}\n"
            "          tenant-id: ${{ secrets.AZURE_TENANT_ID }}\n"
            "          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}\n"
        )

    def _generate_main_workflow(
        self,
        iac_format: IaCFormat,
        environments: list[str],
        include_approval_gates: bool,
        project_name: str,
        primary_region: str,
        resource_groups: list[str],
        architecture: dict,
    ) -> str:
        """Generate the main deployment workflow YAML."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        iac = iac_format.value

        lines: list[str] = []
        lines.append(f"# OnRamp Generated GitHub Actions Workflow — {timestamp}")
        lines.append(f"# IaC Format: {iac}")
        lines.append(f"# Project: {project_name}")
        lines.append(f"# Environments: {', '.join(environments)}")
        lines.append("")
        lines.append(f"name: Deploy {iac.title()} Landing Zone")
        lines.append("")
        lines.append("on:")
        lines.append("  push:")
        lines.append("    branches: [main]")
        lines.append("    paths:")
        lines.append(f"      - 'infra/{iac}/**'")
        lines.append("  pull_request:")
        lines.append("    branches: [main]")
        lines.append("    paths:")
        lines.append(f"      - 'infra/{iac}/**'")
        lines.append("  workflow_dispatch:")
        lines.append("    inputs:")
        lines.append("      environment:")
        lines.append("        description: 'Target environment'")
        lines.append("        required: true")
        lines.append("        type: choice")
        lines.append("        options:")
        for env in environments:
            lines.append(f"          - {env}")
        lines.append("")
        lines.append("permissions:")
        lines.append("  id-token: write")
        lines.append("  contents: read")
        lines.append("")

        # Env block
        lines.append("env:")
        lines.append(f"  LOCATION: {primary_region}")
        lines.append(f"  PROJECT_NAME: {project_name}")
        lines.append("")

        # Generate jobs for each environment
        for i, env in enumerate(environments):
            needs_clause = ""
            if i > 0 and include_approval_gates:
                needs_clause = f"\n    needs: deploy-{environments[i - 1]}"

            lines.append("jobs:")
            if i > 0:
                # Only the first 'jobs:' key is valid; subsequent are just job entries
                lines.pop()

            job_lines = self._generate_deploy_job(
                iac_format=iac_format,
                environment=env,
                needs_clause=needs_clause,
                primary_region=primary_region,
                project_name=project_name,
                resource_groups=resource_groups,
            )
            lines.extend(job_lines)
            lines.append("")

        return "\n".join(lines)

    def _generate_deploy_job(
        self,
        iac_format: IaCFormat,
        environment: str,
        needs_clause: str,
        primary_region: str,
        project_name: str,
        resource_groups: list[str],
    ) -> list[str]:
        """Generate a deployment job for a specific environment."""
        lines: list[str] = []

        lines.append(f"  deploy-{environment}:")
        lines.append(f"    name: Deploy to {environment.title()}")
        lines.append("    runs-on: ubuntu-latest")
        if needs_clause:
            lines.append(f"    needs: deploy-{needs_clause.split('deploy-')[1].strip()}")
        lines.append(f"    environment: {environment}")
        lines.append("    steps:")
        lines.append("      - name: Checkout code")
        lines.append("        uses: actions/checkout@v4")
        lines.append("")

        # Azure OIDC login
        lines.append(self._oidc_login_step().rstrip())
        lines.append("")

        # IaC-specific deployment steps
        if iac_format == IaCFormat.bicep:
            lines.extend(self._bicep_deploy_steps(environment, primary_region, project_name))
        elif iac_format == IaCFormat.terraform:
            lines.extend(
                self._terraform_deploy_steps(environment, primary_region, project_name)
            )
        elif iac_format == IaCFormat.arm:
            lines.extend(self._arm_deploy_steps(environment, primary_region, project_name))
        elif iac_format == IaCFormat.pulumi:
            lines.extend(
                self._pulumi_deploy_steps(environment, primary_region, project_name)
            )

        return lines

    def _bicep_deploy_steps(
        self, environment: str, region: str, project_name: str
    ) -> list[str]:
        """Generate Bicep-specific deployment steps."""
        return [
            "      - name: Validate Bicep",
            "        run: |",
            "          az bicep build --file infra/bicep/main.bicep",
            "",
            "      - name: What-If Analysis",
            "        run: |",
            "          az deployment sub what-if \\",
            f"            --location {region} \\",
            f"            --name {project_name}-{environment} \\",
            "            --template-file infra/bicep/main.bicep \\",
            f"            --parameters infra/bicep/parameters/{environment}.bicepparam",
            "",
            "      - name: Deploy Bicep",
            "        run: |",
            "          az deployment sub create \\",
            f"            --location {region} \\",
            f"            --name {project_name}-{environment} \\",
            "            --template-file infra/bicep/main.bicep \\",
            f"            --parameters infra/bicep/parameters/{environment}.bicepparam",
        ]

    def _terraform_deploy_steps(
        self, environment: str, region: str, project_name: str
    ) -> list[str]:
        """Generate Terraform-specific deployment steps."""
        return [
            "      - name: Setup Terraform",
            "        uses: hashicorp/setup-terraform@v3",
            "        with:",
            "          terraform_version: '1.5.0'",
            "",
            "      - name: Terraform Init",
            "        run: |",
            f"          cd infra/terraform/environments/{environment}",
            "          terraform init",
            "        env:",
            "          ARM_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}",
            "          ARM_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}",
            "          ARM_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}",
            "          ARM_USE_OIDC: true",
            "",
            "      - name: Terraform Plan",
            "        run: |",
            f"          cd infra/terraform/environments/{environment}",
            f"          terraform plan -out={environment}.tfplan",
            "        env:",
            "          ARM_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}",
            "          ARM_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}",
            "          ARM_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}",
            "          ARM_USE_OIDC: true",
            "",
            "      - name: Terraform Apply",
            "        if: github.ref == 'refs/heads/main' && github.event_name != 'pull_request'",
            "        run: |",
            f"          cd infra/terraform/environments/{environment}",
            f"          terraform apply -auto-approve {environment}.tfplan",
            "        env:",
            "          ARM_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}",
            "          ARM_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}",
            "          ARM_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}",
            "          ARM_USE_OIDC: true",
        ]

    def _arm_deploy_steps(
        self, environment: str, region: str, project_name: str
    ) -> list[str]:
        """Generate ARM template-specific deployment steps."""
        return [
            "      - name: Validate ARM Template",
            "        run: |",
            "          az deployment sub validate \\",
            f"            --location {region} \\",
            f"            --name {project_name}-{environment} \\",
            "            --template-file infra/arm/azuredeploy.json \\",
            f"            --parameters infra/arm/parameters/{environment}.parameters.json",
            "",
            "      - name: What-If Analysis",
            "        run: |",
            "          az deployment sub what-if \\",
            f"            --location {region} \\",
            f"            --name {project_name}-{environment} \\",
            "            --template-file infra/arm/azuredeploy.json \\",
            f"            --parameters infra/arm/parameters/{environment}.parameters.json",
            "",
            "      - name: Deploy ARM Template",
            "        run: |",
            "          az deployment sub create \\",
            f"            --location {region} \\",
            f"            --name {project_name}-{environment} \\",
            "            --template-file infra/arm/azuredeploy.json \\",
            f"            --parameters infra/arm/parameters/{environment}.parameters.json",
        ]

    def _pulumi_deploy_steps(
        self, environment: str, region: str, project_name: str
    ) -> list[str]:
        """Generate Pulumi-specific deployment steps."""
        return [
            "      - name: Setup Node.js",
            "        uses: actions/setup-node@v4",
            "        with:",
            "          node-version: '20'",
            "",
            "      - name: Install Pulumi CLI",
            "        uses: pulumi/actions@v5",
            "        with:",
            "          command: version",
            "",
            "      - name: Install Dependencies",
            "        run: |",
            "          cd infra/pulumi",
            "          npm ci",
            "",
            "      - name: Pulumi Preview",
            "        uses: pulumi/actions@v5",
            "        with:",
            "          command: preview",
            f"          stack-name: {project_name}-{environment}",
            "          work-dir: infra/pulumi",
            "        env:",
            "          ARM_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}",
            "          ARM_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}",
            "          ARM_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}",
            "          ARM_USE_OIDC: true",
            "          PULUMI_ACCESS_TOKEN: ${{ secrets.PULUMI_ACCESS_TOKEN }}",
            "",
            "      - name: Pulumi Deploy",
            "        if: github.ref == 'refs/heads/main' && github.event_name != 'pull_request'",
            "        uses: pulumi/actions@v5",
            "        with:",
            "          command: up",
            f"          stack-name: {project_name}-{environment}",
            "          work-dir: infra/pulumi",
            "        env:",
            "          ARM_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}",
            "          ARM_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}",
            "          ARM_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}",
            "          ARM_USE_OIDC: true",
            "          PULUMI_ACCESS_TOKEN: ${{ secrets.PULUMI_ACCESS_TOKEN }}",
        ]

    def _generate_env_params(
        self,
        iac_format: IaCFormat,
        environment: str,
        primary_region: str,
        project_name: str,
        architecture: dict,
    ) -> str:
        """Generate environment-specific parameter/variable file."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        org_size = architecture.get("organization_size", "small")
        network = architecture.get("network_topology", {})
        hub_cidr = "10.0.0.0/16"
        if isinstance(network, dict):
            hub = network.get("hub", {})
            if isinstance(hub, dict):
                hub_cidr = hub.get("vnet_cidr", "10.0.0.0/16")

        # Environment-specific overrides
        env_region_map = {
            "dev": primary_region,
            "staging": primary_region,
            "prod": primary_region,
        }
        region = env_region_map.get(environment, primary_region)

        lines: list[str] = []
        lines.append(f"# OnRamp Generated Environment Parameters — {timestamp}")
        lines.append(f"# Environment: {environment}")
        lines.append(f"# IaC Format: {iac_format.value}")
        lines.append("")
        lines.append(f"environment: {environment}")
        lines.append(f"location: {region}")
        lines.append(f"project_name: {project_name}")
        lines.append(f"organization_size: {org_size}")
        lines.append(f"hub_vnet_cidr: {hub_cidr}")
        lines.append("")
        lines.append("# Resource naming prefix")
        lines.append(f"resource_prefix: {project_name}-{environment}")
        lines.append("")
        lines.append("# Tags")
        lines.append("tags:")
        lines.append(f"  environment: {environment}")
        lines.append("  managed_by: onramp")
        lines.append(f"  project: {project_name}")

        return "\n".join(lines)

    def _generate_validate_workflow(
        self,
        iac_format: IaCFormat,
        project_name: str,
        primary_region: str,
    ) -> str:
        """Generate a reusable validation workflow."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        iac = iac_format.value

        lines: list[str] = []
        lines.append(f"# OnRamp Generated Validation Workflow — {timestamp}")
        lines.append(f"# IaC Format: {iac}")
        lines.append("")
        lines.append(f"name: Validate {iac.title()} Templates")
        lines.append("")
        lines.append("on:")
        lines.append("  pull_request:")
        lines.append("    branches: [main]")
        lines.append("    paths:")
        lines.append(f"      - 'infra/{iac}/**'")
        lines.append("")
        lines.append("permissions:")
        lines.append("  id-token: write")
        lines.append("  contents: read")
        lines.append("")
        lines.append("jobs:")
        lines.append("  validate:")
        lines.append(f"    name: Validate {iac.title()}")
        lines.append("    runs-on: ubuntu-latest")
        lines.append("    steps:")
        lines.append("      - name: Checkout code")
        lines.append("        uses: actions/checkout@v4")
        lines.append("")
        lines.append(self._oidc_login_step().rstrip())
        lines.append("")

        if iac_format == IaCFormat.bicep:
            lines.append("      - name: Lint Bicep")
            lines.append("        run: az bicep build --file infra/bicep/main.bicep")
        elif iac_format == IaCFormat.terraform:
            lines.append("      - name: Setup Terraform")
            lines.append("        uses: hashicorp/setup-terraform@v3")
            lines.append("")
            lines.append("      - name: Terraform Format Check")
            lines.append("        run: terraform fmt -check -recursive infra/terraform/")
            lines.append("")
            lines.append("      - name: Terraform Validate")
            lines.append("        run: |")
            lines.append("          cd infra/terraform")
            lines.append("          terraform init -backend=false")
            lines.append("          terraform validate")
        elif iac_format == IaCFormat.arm:
            lines.append("      - name: Validate ARM Template")
            lines.append("        run: |")
            lines.append("          az deployment sub validate \\")
            lines.append(f"            --location {primary_region} \\")
            lines.append("            --template-file infra/arm/azuredeploy.json")
        elif iac_format == IaCFormat.pulumi:
            lines.append("      - name: Setup Node.js")
            lines.append("        uses: actions/setup-node@v4")
            lines.append("        with:")
            lines.append("          node-version: '20'")
            lines.append("")
            lines.append("      - name: Install & Preview")
            lines.append("        run: |")
            lines.append("          cd infra/pulumi")
            lines.append("          npm ci")
            lines.append("          npx pulumi preview --non-interactive")
            lines.append("        env:")
            lines.append("          PULUMI_ACCESS_TOKEN: ${{ secrets.PULUMI_ACCESS_TOKEN }}")

        return "\n".join(lines)


# Module-level singleton
github_actions_generator = GitHubActionsGenerator()
