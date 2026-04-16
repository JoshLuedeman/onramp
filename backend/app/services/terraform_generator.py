"""Terraform HCL generator — creates deployable Terraform configurations from architecture definitions."""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# Available Terraform module templates that OnRamp can generate
TERRAFORM_MODULES = [
    {
        "name": "hub-networking",
        "description": "Hub virtual network with firewall and bastion subnets",
        "category": "networking",
    },
    {
        "name": "spoke-networking",
        "description": "Spoke virtual network with peering to hub",
        "category": "networking",
    },
    {
        "name": "resource-groups",
        "description": "Platform, networking, and security resource groups",
        "category": "foundation",
    },
    {
        "name": "policy-assignments",
        "description": "Azure Policy assignments for governance controls",
        "category": "governance",
    },
    {
        "name": "log-analytics",
        "description": "Log Analytics workspace for centralized monitoring",
        "category": "management",
    },
    {
        "name": "key-vault",
        "description": "Azure Key Vault for secrets management",
        "category": "security",
    },
]


class TerraformGenerator:
    """Generates Terraform HCL configurations from architecture definitions."""

    def __init__(self):
        self.ai_generated: bool = False

    def get_version(self) -> str:
        """Return the current generator version."""
        return "1.0.0"

    def list_templates(self) -> list[dict]:
        """List all available Terraform module templates."""
        return TERRAFORM_MODULES

    async def generate_from_architecture_with_ai(self, architecture: dict) -> dict[str, str]:
        """Generate Terraform files using AI, falling back to static generation.

        Returns a dict of {filename: hcl_content}.
        """
        from app.services.ai_foundry import ai_client

        # Start with static generation as the base
        static_files = self.generate_from_architecture(architecture)

        try:
            raw_response = await ai_client.generate_terraform(architecture)
            ai_files = json.loads(raw_response)
            if not isinstance(ai_files, dict) or not ai_files:
                raise ValueError("AI response is not a valid file mapping")
            # Merge: AI-generated content overrides/supplements static templates
            static_files.update(ai_files)
            self.ai_generated = True
            logger.info("Terraform generated via AI (%d files)", len(ai_files))
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning("AI Terraform generation failed, using static fallback: %s", e)
            self.ai_generated = False

        return static_files

    def generate_from_architecture(self, architecture: dict) -> dict[str, str]:
        """Generate a set of Terraform files from an architecture definition.

        Returns a dict of {filename: hcl_content}.
        """
        files: dict[str, str] = {}

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        version_header = f"# OnRamp Generated - v{self.get_version()} - {timestamp}\n"

        files["provider.tf"] = self._generate_provider()
        files["variables.tf"] = self._generate_variables(architecture)
        files["main.tf"] = version_header + self._generate_main(architecture)
        files["outputs.tf"] = self._generate_outputs(architecture)

        return files

    def _generate_provider(self) -> str:
        """Generate the Terraform provider configuration."""
        lines = [
            'terraform {',
            '  required_version = ">= 1.5.0"',
            '',
            '  required_providers {',
            '    azurerm = {',
            '      source  = "hashicorp/azurerm"',
            '      version = "~> 4.0"',
            '    }',
            '  }',
            '}',
            '',
            'provider "azurerm" {',
            '  features {',
            '    resource_group {',
            '      prevent_deletion_if_contains_resources = false',
            '    }',
            '  }',
            '}',
        ]
        return "\n".join(lines)

    def _generate_variables(self, architecture: dict) -> str:
        """Generate Terraform variable definitions from architecture."""
        region = architecture.get("network_topology", {}).get("primary_region", "eastus2")
        hub_cidr = (
            architecture.get("network_topology", {})
            .get("hub", {})
            .get("vnet_cidr", "10.0.0.0/16")
        )
        enable_fw = architecture.get("security", {}).get("azure_firewall", True)
        org_size = architecture.get("organization_size", "medium")

        lines = [
            'variable "location" {',
            '  description = "Primary Azure region"',
            '  type        = string',
            f'  default     = "{region}"',
            '}',
            '',
            'variable "environment" {',
            '  description = "Environment name"',
            '  type        = string',
            '  default     = "prod"',
            '}',
            '',
            'variable "organization_size" {',
            '  description = "Organization size tier"',
            '  type        = string',
            f'  default     = "{org_size}"',
            '}',
            '',
            'variable "hub_cidr" {',
            '  description = "Hub VNET CIDR block"',
            '  type        = string',
            f'  default     = "{hub_cidr}"',
            '}',
            '',
            'variable "enable_firewall" {',
            '  description = "Enable Azure Firewall in the hub network"',
            '  type        = bool',
            f'  default     = {str(enable_fw).lower()}',
            '}',
            '',
            'variable "enable_bastion" {',
            '  description = "Enable Azure Bastion for secure VM access"',
            '  type        = bool',
            '  default     = true',
            '}',
        ]

        # Add spoke CIDR variables
        spokes = architecture.get("network_topology", {}).get("spokes", [])
        for i, spoke in enumerate(spokes):
            spoke_name = spoke.get("name", f"spoke-{i}")
            spoke_cidr = spoke.get("vnet_cidr", f"10.{i + 1}.0.0/16")
            lines.extend([
                '',
                f'variable "spoke_{spoke_name}_cidr" {{',
                f'  description = "CIDR block for spoke {spoke_name}"',
                '  type        = string',
                f'  default     = "{spoke_cidr}"',
                '}',
            ])

        return "\n".join(lines)

    def _generate_main(self, architecture: dict) -> str:
        """Generate the main Terraform configuration."""
        lines = [
            'locals {',
            '  tags = {',
            '    managed_by        = "OnRamp"',
            '    organization_size = var.organization_size',
            '    environment       = var.environment',
            '  }',
            '}',
            '',
            '# Resource Groups',
            'resource "azurerm_resource_group" "platform" {',
            '  name     = "rg-platform-${var.environment}"',
            '  location = var.location',
            '  tags     = local.tags',
            '}',
            '',
            'resource "azurerm_resource_group" "networking" {',
            '  name     = "rg-networking-${var.environment}"',
            '  location = var.location',
            '  tags     = local.tags',
            '}',
            '',
            'resource "azurerm_resource_group" "security" {',
            '  name     = "rg-security-${var.environment}"',
            '  location = var.location',
            '  tags     = local.tags',
            '}',
            '',
            '# Hub Virtual Network',
            'resource "azurerm_virtual_network" "hub" {',
            '  name                = "vnet-hub"',
            '  location            = azurerm_resource_group.networking.location',
            '  resource_group_name = azurerm_resource_group.networking.name',
            '  address_space       = [var.hub_cidr]',
            '  tags                = local.tags',
            '}',
            '',
            'resource "azurerm_subnet" "firewall" {',
            '  name                 = "AzureFirewallSubnet"',
            '  resource_group_name  = azurerm_resource_group.networking.name',
            '  virtual_network_name = azurerm_virtual_network.hub.name',
            '  address_prefixes     = [cidrsubnet(var.hub_cidr, 10, 0)]',
            '}',
            '',
            'resource "azurerm_subnet" "bastion" {',
            '  name                 = "AzureBastionSubnet"',
            '  resource_group_name  = azurerm_resource_group.networking.name',
            '  virtual_network_name = azurerm_virtual_network.hub.name',
            '  address_prefixes     = [cidrsubnet(var.hub_cidr, 10, 1)]',
            '}',
        ]

        # Add spoke virtual networks
        spokes = architecture.get("network_topology", {}).get("spokes", [])
        for i, spoke in enumerate(spokes):
            spoke_name = spoke.get("name", f"spoke-{i}")
            var_name = f"spoke_{spoke_name}_cidr"
            lines.extend([
                '',
                f'# Spoke: {spoke_name}',
                f'resource "azurerm_virtual_network" "spoke_{spoke_name}" {{',
                f'  name                = "vnet-spoke-{spoke_name}"',
                '  location            = azurerm_resource_group.networking.location',
                '  resource_group_name = azurerm_resource_group.networking.name',
                f'  address_space       = [var.{var_name}]',
                '  tags                = local.tags',
                '}',
                '',
                f'resource "azurerm_virtual_network_peering" "hub_to_{spoke_name}" {{',
                f'  name                      = "peer-hub-to-{spoke_name}"',
                '  resource_group_name       = azurerm_resource_group.networking.name',
                '  virtual_network_name      = azurerm_virtual_network.hub.name',
                f'  remote_virtual_network_id = azurerm_virtual_network.spoke_{spoke_name}.id',
                '  allow_forwarded_traffic   = true',
                '  allow_gateway_transit     = true',
                '}',
                '',
                f'resource "azurerm_virtual_network_peering" "{spoke_name}_to_hub" {{',
                f'  name                      = "peer-{spoke_name}-to-hub"',
                '  resource_group_name       = azurerm_resource_group.networking.name',
                f'  virtual_network_name      = azurerm_virtual_network.spoke_{spoke_name}.name',
                '  remote_virtual_network_id = azurerm_virtual_network.hub.id',
                '  allow_forwarded_traffic   = true',
                '  use_remote_gateways       = false',
                '}',
            ])

        return "\n".join(lines)

    def _generate_outputs(self, architecture: dict) -> str:
        """Generate Terraform output definitions."""
        lines = [
            'output "resource_group_platform_id" {',
            '  description = "Platform resource group ID"',
            '  value       = azurerm_resource_group.platform.id',
            '}',
            '',
            'output "resource_group_networking_id" {',
            '  description = "Networking resource group ID"',
            '  value       = azurerm_resource_group.networking.id',
            '}',
            '',
            'output "resource_group_security_id" {',
            '  description = "Security resource group ID"',
            '  value       = azurerm_resource_group.security.id',
            '}',
            '',
            'output "hub_vnet_id" {',
            '  description = "Hub virtual network ID"',
            '  value       = azurerm_virtual_network.hub.id',
            '}',
            '',
            'output "hub_vnet_name" {',
            '  description = "Hub virtual network name"',
            '  value       = azurerm_virtual_network.hub.name',
            '}',
        ]

        # Add spoke outputs
        spokes = architecture.get("network_topology", {}).get("spokes", [])
        for i, spoke in enumerate(spokes):
            spoke_name = spoke.get("name", f"spoke-{i}")
            lines.extend([
                '',
                f'output "spoke_{spoke_name}_vnet_id" {{',
                f'  description = "Spoke {spoke_name} virtual network ID"',
                f'  value       = azurerm_virtual_network.spoke_{spoke_name}.id',
                '}',
            ])

        return "\n".join(lines)


# Singleton
terraform_generator = TerraformGenerator()
