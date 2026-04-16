"""Bicep template generation for AI/ML landing zone resources.

Generates Azure Bicep code for ML workspaces, GPU compute clusters,
storage accounts, container registries, Key Vaults and optional
Databricks workspaces.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class AiMlBicepService:
    """Generates Bicep templates for AI/ML landing zone resources."""

    def generate_ml_workspace(self, config: dict[str, Any]) -> str:
        """Generate Bicep for an Azure ML Workspace and dependencies.

        Args:
            config: Dict with ``name``, ``location``, ``sku`` (Basic /
                Enterprise), ``private_endpoint`` (bool).

        Returns:
            Bicep template string.
        """
        name = config.get("name", "mlw-onramp")
        location = config.get("location", "eastus")
        sku = config.get("sku", "Basic")
        private = config.get("private_endpoint", True)

        lines = [
            f"// Azure ML Workspace – {name}",
            f"param location string = '{location}'",
            f"param workspaceName string = '{name}'",
            "",
            "resource storageAccount 'Microsoft.Storage/storageAccounts"
            "@2023-05-01' = {",
            "  name: 'st${uniqueString(resourceGroup().id)}'",
            "  location: location",
            "  kind: 'StorageV2'",
            "  sku: { name: 'Standard_LRS' }",
            "  properties: {",
            "    isHnsEnabled: true",
            "    minimumTlsVersion: 'TLS1_2'",
            "  }",
            "}",
            "",
            "resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {",
            "  name: 'kv-${uniqueString(resourceGroup().id)}'",
            "  location: location",
            "  properties: {",
            "    sku: { family: 'A', name: 'standard' }",
            "    tenantId: subscription().tenantId",
            "    enableSoftDelete: true",
            "    enablePurgeProtection: true",
            "  }",
            "}",
            "",
            "resource appInsights 'Microsoft.Insights/"
            "components@2020-02-02' = {",
            "  name: 'appi-${workspaceName}'",
            "  location: location",
            "  kind: 'web'",
            "  properties: { Application_Type: 'web' }",
            "}",
            "",
            "resource containerRegistry 'Microsoft.ContainerRegistry/"
            "registries@2023-11-01-preview' = {",
            "  name: 'cr${uniqueString(resourceGroup().id)}'",
            "  location: location",
            "  sku: { name: 'Standard' }",
            "}",
            "",
            "resource mlWorkspace 'Microsoft.MachineLearningServices/"
            "workspaces@2024-04-01' = {",
            "  name: workspaceName",
            "  location: location",
            f"  sku: {{ name: '{sku}' }}",
            "  identity: { type: 'SystemAssigned' }",
            "  properties: {",
            "    friendlyName: workspaceName",
            "    storageAccount: storageAccount.id",
            "    keyVault: keyVault.id",
            "    applicationInsights: appInsights.id",
            "    containerRegistry: containerRegistry.id",
            "  }",
            "}",
        ]

        if private:
            lines.extend([
                "",
                "// Private endpoint for ML workspace",
                "resource mlPrivateEndpoint 'Microsoft.Network/"
                "privateEndpoints@2023-11-01' = {",
                "  name: 'pe-${workspaceName}'",
                "  location: location",
                "  properties: {",
                "    privateLinkServiceConnections: [",
                "      {",
                "        name: 'pe-${workspaceName}'",
                "        properties: {",
                "          privateLinkServiceId: mlWorkspace.id",
                "          groupIds: ['amlworkspace']",
                "        }",
                "      }",
                "    ]",
                "  }",
                "}",
            ])

        lines.extend([
            "",
            "output workspaceId string = mlWorkspace.id",
            "output workspaceName string = mlWorkspace.name",
        ])

        return "\n".join(lines)

    def generate_compute_cluster(self, config: dict[str, Any]) -> str:
        """Generate Bicep for an Azure ML compute cluster.

        Args:
            config: Dict with ``workspace_name``, ``cluster_name``,
                ``vm_size``, ``min_nodes``, ``max_nodes``, ``location``.

        Returns:
            Bicep template string.
        """
        ws = config.get("workspace_name", "mlw-onramp")
        name = config.get("cluster_name", "gpu-cluster")
        vm_size = config.get("vm_size", "Standard_NC4as_T4_v3")
        min_n = config.get("min_nodes", 0)
        max_n = config.get("max_nodes", 4)
        location = config.get("location", "eastus")

        lines = [
            f"// ML Compute Cluster – {name}",
            f"param location string = '{location}'",
            f"param workspaceName string = '{ws}'",
            "",
            "resource mlWorkspace 'Microsoft.MachineLearningServices/"
            "workspaces@2024-04-01' existing = {",
            "  name: workspaceName",
            "}",
            "",
            "resource computeCluster 'Microsoft.MachineLearningServices/"
            "workspaces/computes@2024-04-01' = {",
            f"  name: '{name}'",
            "  parent: mlWorkspace",
            "  location: location",
            "  properties: {",
            "    computeType: 'AmlCompute'",
            "    properties: {",
            f"      vmSize: '{vm_size}'",
            "      scaleSettings: {",
            f"        minNodeCount: {min_n}",
            f"        maxNodeCount: {max_n}",
            "        nodeIdleTimeBeforeScaleDown: 'PT15M'",
            "      }",
            "      remoteLoginPortPublicAccess: 'Disabled'",
            "    }",
            "  }",
            "}",
            "",
            "output clusterName string = computeCluster.name",
        ]
        return "\n".join(lines)

    def generate_full_aiml_stack(self, config: dict[str, Any]) -> str:
        """Generate a complete AI/ML landing zone Bicep template.

        Combines ML workspace, compute cluster, ADLS Gen2 storage,
        ACR, Key Vault, private endpoints and optionally Databricks.

        Args:
            config: Dict with ``name``, ``location``, ``vm_size``,
                ``max_nodes``, ``include_databricks`` (bool), ``sku``.

        Returns:
            Full Bicep template string.
        """
        name = config.get("name", "mlw-onramp")
        location = config.get("location", "eastus")
        vm_size = config.get("vm_size", "Standard_NC4as_T4_v3")
        max_nodes = config.get("max_nodes", 4)
        include_databricks = config.get("include_databricks", False)

        workspace_bicep = self.generate_ml_workspace(
            {"name": name, "location": location, "sku": "Basic",
             "private_endpoint": True}
        )
        cluster_bicep = self.generate_compute_cluster(
            {"workspace_name": name, "cluster_name": "gpu-cluster",
             "vm_size": vm_size, "max_nodes": max_nodes,
             "location": location}
        )

        parts = [
            f"// Full AI/ML Landing Zone – {name}",
            "targetScope = 'resourceGroup'",
            "",
            workspace_bicep,
            "",
            cluster_bicep,
        ]

        if include_databricks:
            parts.extend([
                "",
                "// Azure Databricks Workspace",
                "resource databricksWorkspace 'Microsoft.Databricks/"
                "workspaces@2024-05-01' = {",
                "  name: 'dbw-${uniqueString(resourceGroup().id)}'",
                f"  location: '{location}'",
                "  sku: { name: 'premium' }",
                "  properties: {",
                "    managedResourceGroupId: subscriptionResourceId("
                "'Microsoft.Resources/resourceGroups', "
                "'databricks-rg-${uniqueString(resourceGroup().id)}')",
                "  }",
                "}",
            ])

        return "\n".join(parts)


# Module-level singleton
aiml_bicep_service = AiMlBicepService()
