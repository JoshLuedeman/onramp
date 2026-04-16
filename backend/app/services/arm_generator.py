"""ARM template generator — creates deployable ARM JSON from architecture definitions."""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ARM template JSON schema URL
ARM_SCHEMA = "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#"
ARM_PARAMS_SCHEMA = (
    "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#"
)
CONTENT_VERSION = "1.0.0.0"


class ARMGenerator:
    """Generates ARM JSON templates from architecture definitions."""

    def __init__(self):
        self.ai_generated: bool = False

    def get_version(self) -> str:
        """Return the current template version."""
        return "1.0.0"

    async def generate_from_architecture_with_ai(
        self, architecture: dict
    ) -> dict[str, str]:
        """Generate ARM files using AI, falling back to static templates.

        Returns a dict of {filename: arm_json_content}.
        """
        from app.services.ai_foundry import ai_client

        # Start with static templates as the base
        static_files = self.generate_from_architecture(architecture)

        try:
            raw_response = await ai_client.generate_arm(architecture)
            ai_files = json.loads(raw_response)
            if not isinstance(ai_files, dict) or not ai_files:
                raise ValueError("AI response is not a valid file mapping")
            # Merge: AI-generated content overrides/supplements static templates
            static_files.update(ai_files)
            self.ai_generated = True
            logger.info("ARM generated via AI (%d files)", len(ai_files))
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning("AI ARM generation failed, using static fallback: %s", e)
            self.ai_generated = False
        except AttributeError:
            logger.warning("AI client does not support ARM generation, using static fallback")
            self.ai_generated = False

        return static_files

    def generate_from_architecture(self, architecture: dict) -> dict[str, str]:
        """Generate a set of ARM template files from an architecture definition.

        Returns a dict of {filename: arm_json_content}.
        """
        files: dict[str, str] = {}

        # Generate main deployment template
        files["azuredeploy.json"] = self._generate_main_template(architecture)

        # Generate parameters file
        files["azuredeploy.parameters.json"] = self._generate_parameters(architecture)

        # Generate networking nested template
        files["nestedtemplates/networking.json"] = self._generate_networking_template(
            architecture
        )

        # Generate security nested template
        files["nestedtemplates/security.json"] = self._generate_security_template(
            architecture
        )

        return files

    def _generate_main_template(self, architecture: dict) -> str:
        """Generate the main ARM deployment template."""
        region = (
            architecture.get("network_topology", {}).get("primary_region", "eastus2")
        )
        org_size = architecture.get("organization_size", "medium")
        hub_cidr = (
            architecture.get("network_topology", {})
            .get("hub", {})
            .get("vnet_cidr", "10.0.0.0/16")
        )
        enable_firewall = architecture.get("security", {}).get("azure_firewall", True)
        enable_bastion = architecture.get("security", {}).get("bastion", True)

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        template: dict = {
            "$schema": ARM_SCHEMA,
            "contentVersion": CONTENT_VERSION,
            "metadata": {
                "generator": "OnRamp",
                "version": self.get_version(),
                "generated_at": timestamp,
                "organization_size": org_size,
            },
            "parameters": {
                "location": {
                    "type": "string",
                    "defaultValue": region,
                    "metadata": {"description": "Primary Azure region for deployment"},
                },
                "environment": {
                    "type": "string",
                    "defaultValue": "prod",
                    "allowedValues": ["dev", "staging", "prod"],
                    "metadata": {"description": "Environment name"},
                },
                "hubVnetCidr": {
                    "type": "string",
                    "defaultValue": hub_cidr,
                    "metadata": {"description": "CIDR for the hub virtual network"},
                },
                "enableFirewall": {
                    "type": "bool",
                    "defaultValue": enable_firewall,
                    "metadata": {"description": "Enable Azure Firewall in the hub"},
                },
                "enableBastion": {
                    "type": "bool",
                    "defaultValue": enable_bastion,
                    "metadata": {"description": "Enable Azure Bastion in the hub"},
                },
            },
            "variables": {
                "platformRgName": "[concat('rg-platform-', parameters('environment'))]",
                "networkingRgName": "[concat('rg-networking-', parameters('environment'))]",
                "securityRgName": "[concat('rg-security-', parameters('environment'))]",
                "tags": {
                    "managedBy": "OnRamp",
                    "organizationSize": org_size,
                    "environment": "[parameters('environment')]",
                },
            },
            "resources": self._build_resources(architecture),
            "outputs": {
                "platformResourceGroupName": {
                    "type": "string",
                    "value": "[variables('platformRgName')]",
                },
                "networkingResourceGroupName": {
                    "type": "string",
                    "value": "[variables('networkingRgName')]",
                },
                "securityResourceGroupName": {
                    "type": "string",
                    "value": "[variables('securityRgName')]",
                },
            },
        }

        return json.dumps(template, indent=2)

    def _build_resources(self, architecture: dict) -> list[dict]:
        """Build the resources array for the main ARM template."""
        resources: list[dict] = []

        # Resource groups
        for rg_var, rg_purpose in [
            ("platformRgName", "Platform services"),
            ("networkingRgName", "Networking resources"),
            ("securityRgName", "Security resources"),
        ]:
            resources.append({
                "type": "Microsoft.Resources/resourceGroups",
                "apiVersion": "2024-03-01",
                "name": f"[variables('{rg_var}')]",
                "location": "[parameters('location')]",
                "tags": "[variables('tags')]",
                "properties": {},
            })

        # Hub virtual network (nested deployment into networking RG)
        resources.append({
            "type": "Microsoft.Resources/deployments",
            "apiVersion": "2024-03-01",
            "name": "hub-networking",
            "resourceGroup": "[variables('networkingRgName')]",
            "dependsOn": [
                "[resourceId('Microsoft.Resources/resourceGroups', "
                "variables('networkingRgName'))]",
            ],
            "properties": {
                "mode": "Incremental",
                "templateLink": {
                    "relativePath": "nestedtemplates/networking.json",
                },
                "parameters": {
                    "location": {"value": "[parameters('location')]"},
                    "hubVnetCidr": {"value": "[parameters('hubVnetCidr')]"},
                    "enableFirewall": {"value": "[parameters('enableFirewall')]"},
                    "enableBastion": {"value": "[parameters('enableBastion')]"},
                    "tags": {"value": "[variables('tags')]"},
                },
            },
        })

        # Spoke deployments
        spokes = architecture.get("network_topology", {}).get("spokes", [])
        for i, spoke in enumerate(spokes):
            spoke_name = spoke.get("name", f"spoke-{i}")
            spoke_cidr = spoke.get("vnet_cidr", f"10.{i + 1}.0.0/16")
            resources.append({
                "type": "Microsoft.Resources/deployments",
                "apiVersion": "2024-03-01",
                "name": f"spoke-{spoke_name}",
                "resourceGroup": "[variables('networkingRgName')]",
                "dependsOn": [
                    "[resourceId('Microsoft.Resources/resourceGroups', "
                    "variables('networkingRgName'))]",
                    "hub-networking",
                ],
                "properties": {
                    "mode": "Incremental",
                    "template": {
                        "$schema": ARM_SCHEMA,
                        "contentVersion": CONTENT_VERSION,
                        "parameters": {},
                        "resources": [
                            {
                                "type": "Microsoft.Network/virtualNetworks",
                                "apiVersion": "2024-01-01",
                                "name": f"vnet-{spoke_name}",
                                "location": "[parameters('location')]",
                                "tags": "[variables('tags')]",
                                "properties": {
                                    "addressSpace": {
                                        "addressPrefixes": [spoke_cidr],
                                    },
                                    "subnets": [
                                        {
                                            "name": "default",
                                            "properties": {
                                                "addressPrefix": spoke_cidr,
                                            },
                                        },
                                    ],
                                },
                            },
                        ],
                    },
                },
            })

        # Security deployment
        resources.append({
            "type": "Microsoft.Resources/deployments",
            "apiVersion": "2024-03-01",
            "name": "security-resources",
            "resourceGroup": "[variables('securityRgName')]",
            "dependsOn": [
                "[resourceId('Microsoft.Resources/resourceGroups', "
                "variables('securityRgName'))]",
            ],
            "properties": {
                "mode": "Incremental",
                "templateLink": {
                    "relativePath": "nestedtemplates/security.json",
                },
                "parameters": {
                    "location": {"value": "[parameters('location')]"},
                    "tags": {"value": "[variables('tags')]"},
                },
            },
        })

        return resources

    def _generate_parameters(self, architecture: dict) -> str:
        """Generate the ARM parameters file."""
        region = (
            architecture.get("network_topology", {}).get("primary_region", "eastus2")
        )
        hub_cidr = (
            architecture.get("network_topology", {})
            .get("hub", {})
            .get("vnet_cidr", "10.0.0.0/16")
        )
        enable_firewall = architecture.get("security", {}).get("azure_firewall", True)

        params = {
            "$schema": ARM_PARAMS_SCHEMA,
            "contentVersion": CONTENT_VERSION,
            "parameters": {
                "location": {"value": region},
                "environment": {"value": "prod"},
                "hubVnetCidr": {"value": hub_cidr},
                "enableFirewall": {"value": enable_firewall},
                "enableBastion": {"value": True},
            },
        }
        return json.dumps(params, indent=2)

    def _generate_networking_template(self, architecture: dict) -> str:
        """Generate the networking nested ARM template."""
        template = {
            "$schema": ARM_SCHEMA,
            "contentVersion": CONTENT_VERSION,
            "parameters": {
                "location": {"type": "string"},
                "hubVnetCidr": {"type": "string"},
                "enableFirewall": {"type": "bool"},
                "enableBastion": {"type": "bool"},
                "tags": {"type": "object"},
            },
            "variables": {
                "hubVnetName": "vnet-hub",
                "firewallSubnetName": "AzureFirewallSubnet",
                "bastionSubnetName": "AzureBastionSubnet",
                "gatewaySubnetName": "GatewaySubnet",
            },
            "resources": [
                {
                    "type": "Microsoft.Network/virtualNetworks",
                    "apiVersion": "2024-01-01",
                    "name": "[variables('hubVnetName')]",
                    "location": "[parameters('location')]",
                    "tags": "[parameters('tags')]",
                    "properties": {
                        "addressSpace": {
                            "addressPrefixes": ["[parameters('hubVnetCidr')]"],
                        },
                        "subnets": [
                            {
                                "name": "[variables('firewallSubnetName')]",
                                "properties": {"addressPrefix": "10.0.1.0/26"},
                            },
                            {
                                "name": "[variables('bastionSubnetName')]",
                                "properties": {"addressPrefix": "10.0.1.64/26"},
                            },
                            {
                                "name": "[variables('gatewaySubnetName')]",
                                "properties": {"addressPrefix": "10.0.1.128/27"},
                            },
                        ],
                    },
                },
            ],
            "outputs": {
                "hubVnetId": {
                    "type": "string",
                    "value": "[resourceId('Microsoft.Network/virtualNetworks', "
                    "variables('hubVnetName'))]",
                },
                "hubVnetName": {
                    "type": "string",
                    "value": "[variables('hubVnetName')]",
                },
            },
        }
        return json.dumps(template, indent=2)

    def _generate_security_template(self, architecture: dict) -> str:
        """Generate the security nested ARM template."""
        defender_enabled = architecture.get("security", {}).get(
            "defender_for_cloud", True
        )
        sentinel_enabled = architecture.get("security", {}).get("sentinel", False)

        resources: list[dict] = []

        # Log Analytics workspace (always created for security)
        resources.append({
            "type": "Microsoft.OperationalInsights/workspaces",
            "apiVersion": "2023-09-01",
            "name": "law-security",
            "location": "[parameters('location')]",
            "tags": "[parameters('tags')]",
            "properties": {
                "sku": {"name": "PerGB2018"},
                "retentionInDays": 90,
            },
        })

        # Key Vault
        resources.append({
            "type": "Microsoft.KeyVault/vaults",
            "apiVersion": "2023-07-01",
            "name": "kv-security-onramp",
            "location": "[parameters('location')]",
            "tags": "[parameters('tags')]",
            "properties": {
                "sku": {"family": "A", "name": "standard"},
                "tenantId": "[subscription().tenantId]",
                "enableRbacAuthorization": True,
                "enableSoftDelete": True,
                "softDeleteRetentionInDays": 90,
            },
        })

        template = {
            "$schema": ARM_SCHEMA,
            "contentVersion": CONTENT_VERSION,
            "parameters": {
                "location": {"type": "string"},
                "tags": {"type": "object"},
            },
            "resources": resources,
            "outputs": {
                "workspaceId": {
                    "type": "string",
                    "value": "[resourceId('Microsoft.OperationalInsights/workspaces', "
                    "'law-security')]",
                },
                "keyVaultName": {
                    "type": "string",
                    "value": "kv-security-onramp",
                },
                "defenderEnabled": {
                    "type": "bool",
                    "value": defender_enabled,
                },
                "sentinelEnabled": {
                    "type": "bool",
                    "value": sentinel_enabled,
                },
            },
        }
        return json.dumps(template, indent=2)

    def validate_template(self, template_content: str) -> dict:
        """Validate an ARM template structure.

        Returns a dict with 'valid', 'errors', and 'warnings' fields.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Parse JSON
        try:
            template = json.loads(template_content)
        except json.JSONDecodeError as e:
            return {
                "valid": False,
                "errors": [f"Invalid JSON: {e}"],
                "warnings": [],
            }

        if not isinstance(template, dict):
            return {
                "valid": False,
                "errors": ["Template must be a JSON object"],
                "warnings": [],
            }

        # Check required top-level fields
        if "$schema" not in template:
            errors.append("Missing required field: $schema")
        elif "deploymentTemplate" not in template.get("$schema", ""):
            warnings.append(
                "$schema does not reference a deployment template schema"
            )

        if "contentVersion" not in template:
            errors.append("Missing required field: contentVersion")

        if "resources" not in template:
            errors.append("Missing required field: resources")
        elif not isinstance(template.get("resources"), list):
            errors.append("'resources' must be an array")

        # Check optional but recommended fields
        if "parameters" not in template:
            warnings.append("Template has no parameters defined")

        if "outputs" not in template:
            warnings.append("Template has no outputs defined")

        # Validate resource structure
        resources = template.get("resources", [])
        if isinstance(resources, list):
            for i, resource in enumerate(resources):
                if not isinstance(resource, dict):
                    errors.append(f"Resource at index {i} is not an object")
                    continue
                if "type" not in resource:
                    errors.append(f"Resource at index {i} missing 'type'")
                if "apiVersion" not in resource:
                    # Nested inline templates may not require apiVersion on inner resources
                    if resource.get("type") != "Microsoft.Resources/deployments":
                        warnings.append(
                            f"Resource at index {i} missing 'apiVersion'"
                        )

        # Validate parameters structure
        params = template.get("parameters", {})
        if isinstance(params, dict):
            for param_name, param_def in params.items():
                if isinstance(param_def, dict) and "type" not in param_def:
                    errors.append(
                        f"Parameter '{param_name}' missing 'type' field"
                    )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }


# Singleton
arm_generator = ARMGenerator()
