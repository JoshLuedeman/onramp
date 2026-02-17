"""Bicep template generator — creates deployable Bicep from architecture definitions."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "bicep"


class BicepGenerator:
    """Generates Bicep templates from architecture definitions."""

    def __init__(self):
        self.template_dir = TEMPLATE_DIR
        self.ai_generated: bool = False

    def get_version(self) -> str:
        """Return the current template version."""
        return "1.0.0"

    def get_template(self, template_name: str) -> str | None:
        """Load a Bicep template file."""
        template_path = self.template_dir / template_name
        if template_path.exists():
            return template_path.read_text()
        return None

    def list_templates(self) -> list[dict]:
        """List all available Bicep templates."""
        templates = []
        if self.template_dir.exists():
            for f in sorted(self.template_dir.glob("*.bicep")):
                templates.append({
                    "name": f.stem,
                    "filename": f.name,
                    "size_bytes": f.stat().st_size,
                })
        return templates

    async def generate_from_architecture_with_ai(self, architecture: dict) -> dict[str, str]:
        """Generate Bicep files using AI, falling back to static templates.

        Returns a dict of {filename: bicep_content}.
        """
        from app.services.ai_foundry import ai_client

        # Start with static templates as the base
        static_files = self.generate_from_architecture(architecture)

        try:
            raw_response = await ai_client.generate_bicep(architecture)
            ai_files = json.loads(raw_response)
            if not isinstance(ai_files, dict) or not ai_files:
                raise ValueError("AI response is not a valid file mapping")
            # Merge: AI-generated content overrides/supplements static templates
            static_files.update(ai_files)
            self.ai_generated = True
            logger.info("Bicep generated via AI (%d files)", len(ai_files))
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning("AI Bicep generation failed, using static fallback: %s", e)
            self.ai_generated = False

        return static_files

    def generate_from_architecture(self, architecture: dict) -> dict[str, str]:
        """Generate a set of Bicep files from an architecture definition.

        Returns a dict of {filename: bicep_content}.
        """
        files: dict[str, str] = {}

        # Management groups
        mg_template = self.get_template("management-groups.bicep")
        if mg_template:
            files["management-groups.bicep"] = mg_template

        # Hub networking
        hub_template = self.get_template("hub-networking.bicep")
        if hub_template:
            files["hub-networking.bicep"] = hub_template

        # Spoke networking for each spoke
        spoke_template = self.get_template("spoke-networking.bicep")
        if spoke_template:
            files["spoke-networking.bicep"] = spoke_template

        # Policy assignments
        policy_template = self.get_template("policy-assignments.bicep")
        if policy_template:
            files["policy-assignments.bicep"] = policy_template

        # Generate main orchestration file with version header
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        version_header = f"// OnRamp Generated - v{self.get_version()} - {timestamp}\n"
        files["main.bicep"] = version_header + self._generate_main_bicep(architecture)

        # Generate parameters file
        files["parameters.json"] = self._generate_parameters(architecture)

        return files

    def _generate_main_bicep(self, architecture: dict) -> str:
        """Generate the main orchestration Bicep file."""
        region = architecture.get("network_topology", {}).get("primary_region", "eastus2")
        org_size = architecture.get("organization_size", "medium")

        lines = [
            "targetScope = 'subscription'",
            "",
            "@description('Primary Azure region')",
            f"param location string = '{region}'",
            "",
            "@description('Environment name')",
            "param environment string = 'prod'",
            "",
            "var tags = {",
            "  managedBy: 'OnRamp'",
            f"  organizationSize: '{org_size}'",
            "  environment: environment",
            "}",
            "",
            "// Resource Groups",
            "resource rgPlatform 'Microsoft.Resources/resourceGroups@2024-03-01' = {",
            "  name: 'rg-platform-${environment}'",
            "  location: location",
            "  tags: tags",
            "}",
            "",
            "resource rgNetworking 'Microsoft.Resources/resourceGroups@2024-03-01' = {",
            "  name: 'rg-networking-${environment}'",
            "  location: location",
            "  tags: tags",
            "}",
            "",
            "resource rgSecurity 'Microsoft.Resources/resourceGroups@2024-03-01' = {",
            "  name: 'rg-security-${environment}'",
            "  location: location",
            "  tags: tags",
            "}",
            "",
            "// Hub Networking",
            "module hubNetwork 'hub-networking.bicep' = {",
            "  scope: rgNetworking",
            "  name: 'hub-networking'",
            "  params: {",
            "    location: location",
            f"    hubCidr: '{architecture.get('network_topology', {}).get('hub', {}).get('vnet_cidr', '10.0.0.0/16')}'",
            f"    enableFirewall: {str(architecture.get('security', {}).get('azure_firewall', True)).lower()}",
            "    enableBastion: true",
            "    tags: tags",
            "  }",
            "}",
        ]

        # Add spoke modules
        spokes = architecture.get("network_topology", {}).get("spokes", [])
        for i, spoke in enumerate(spokes):
            spoke_name = spoke.get("name", f"spoke-{i}")
            spoke_cidr = spoke.get("vnet_cidr", f"10.{i+1}.0.0/16")
            lines.extend([
                "",
                f"module spoke{i} 'spoke-networking.bicep' = {{",
                "  scope: rgNetworking",
                f"  name: 'spoke-{spoke_name}'",
                "  params: {",
                "    location: location",
                f"    spokeName: '{spoke_name}'",
                f"    spokeCidr: '{spoke_cidr}'",
                "    hubVnetId: hubNetwork.outputs.hubVnetId",
                "    tags: tags",
                "  }",
                "  dependsOn: [hubNetwork]",
                "}",
            ])

        return "\n".join(lines)

    def _generate_parameters(self, architecture: dict) -> str:
        """Generate a parameters JSON file."""
        import json

        region = architecture.get("network_topology", {}).get("primary_region", "eastus2")
        params = {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
            "contentVersion": "1.0.0.0",
            "parameters": {
                "location": {"value": region},
                "environment": {"value": "prod"},
            },
        }
        return json.dumps(params, indent=2)


# Singleton
bicep_generator = BicepGenerator()
