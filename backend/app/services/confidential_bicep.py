"""Bicep template generation for Azure Confidential Computing resources.

Generates Bicep modules for confidential VMs, confidential AKS clusters,
Azure Attestation providers, Key Vault with mHSM backing, and
Always Encrypted SQL databases.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ConfidentialBicepService:
    """Service for generating Bicep templates for confidential computing."""

    def generate_confidential_vm(self, config: dict) -> str:
        """Generate Bicep template for a confidential VM.

        Args:
            config: Dict with keys: name, location, vm_sku, os_type,
                admin_username, tee_type, security_type.

        Returns:
            Bicep template string for the confidential VM resource.
        """
        name = config.get("name", "ccVm")
        location = config.get("location", "eastus")
        vm_sku = config.get("vm_sku", "Standard_DC4as_v5")
        os_type = config.get("os_type", "Linux")
        admin_username = config.get("admin_username", "azureadmin")
        security_type = config.get("security_type", "ConfidentialVM")

        os_image = self._get_os_image(os_type)

        return f"""// Confidential VM with hardware-based encryption (TEE)
param location string = '{location}'
param vmName string = '{name}'
param adminUsername string = '{admin_username}'
@secure()
param adminPasswordOrKey string

resource confidentialVm 'Microsoft.Compute/virtualMachines@2024-03-01' = {{
  name: vmName
  location: location
  properties: {{
    hardwareProfile: {{
      vmSize: '{vm_sku}'
    }}
    osProfile: {{
      computerName: vmName
      adminUsername: adminUsername
      adminPassword: adminPasswordOrKey
    }}
    storageProfile: {{
      imageReference: {{
        publisher: '{os_image["publisher"]}'
        offer: '{os_image["offer"]}'
        sku: '{os_image["sku"]}'
        version: 'latest'
      }}
      osDisk: {{
        createOption: 'FromImage'
        managedDisk: {{
          securityProfile: {{
            securityEncryptionType: 'VMGuestStateOnly'
          }}
        }}
      }}
    }}
    securityProfile: {{
      securityType: '{security_type}'
      uefiSettings: {{
        secureBootEnabled: true
        vTpmEnabled: true
      }}
    }}
    networkProfile: {{
      networkInterfaces: [
        {{
          id: nic.id
        }}
      ]
    }}
  }}
}}

resource nic 'Microsoft.Network/networkInterfaces@2023-11-01' = {{
  name: '${{vmName}}-nic'
  location: location
  properties: {{
    ipConfigurations: [
      {{
        name: 'ipconfig1'
        properties: {{
          subnet: {{
            id: subnet.id
          }}
          privateIPAllocationMethod: 'Dynamic'
        }}
      }}
    ]
  }}
}}

resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {{
  name: '${{vmName}}-vnet'
  location: location
  properties: {{
    addressSpace: {{
      addressPrefixes: [
        '10.0.0.0/16'
      ]
    }}
    subnets: [
      {{
        name: 'default'
        properties: {{
          addressPrefix: '10.0.0.0/24'
        }}
      }}
    ]
  }}
}}

resource subnet 'Microsoft.Network/virtualNetworks/subnets@2023-11-01' existing = {{
  parent: vnet
  name: 'default'
}}

output vmId string = confidentialVm.id
output vmName string = confidentialVm.name
"""

    def generate_confidential_aks(self, config: dict) -> str:
        """Generate Bicep template for a confidential AKS cluster.

        Args:
            config: Dict with keys: name, location, node_count,
                node_vm_sku, kubernetes_version.

        Returns:
            Bicep template string for confidential AKS.
        """
        name = config.get("name", "ccAksCluster")
        location = config.get("location", "eastus")
        node_count = config.get("node_count", 3)
        node_vm_sku = config.get("node_vm_sku", "Standard_DC4as_v5")
        k8s_version = config.get("kubernetes_version", "1.29")

        return f"""// Confidential AKS cluster with TEE-backed node pools
param location string = '{location}'
param clusterName string = '{name}'
param kubernetesVersion string = '{k8s_version}'

resource aksCluster 'Microsoft.ContainerService/managedClusters@2024-02-01' = {{
  name: clusterName
  location: location
  identity: {{
    type: 'SystemAssigned'
  }}
  properties: {{
    kubernetesVersion: kubernetesVersion
    dnsPrefix: '${{clusterName}}-dns'
    agentPoolProfiles: [
      {{
        name: 'systempool'
        count: {node_count}
        vmSize: '{node_vm_sku}'
        osType: 'Linux'
        mode: 'System'
        enableEncryptionAtHost: true
      }}
      {{
        name: 'confpool'
        count: {node_count}
        vmSize: '{node_vm_sku}'
        osType: 'Linux'
        mode: 'User'
        enableEncryptionAtHost: true
        workloadRuntime: 'KataCcIsolation'
      }}
    ]
    networkProfile: {{
      networkPlugin: 'azure'
      networkPolicy: 'azure'
    }}
    addonProfiles: {{
      azureKeyvaultSecretsProvider: {{
        enabled: true
      }}
    }}
  }}
}}

output clusterId string = aksCluster.id
output clusterName string = aksCluster.name
output clusterFqdn string = aksCluster.properties.fqdn
"""

    def generate_attestation_provider(self, config: dict) -> str:
        """Generate Bicep template for an Azure Attestation provider.

        Args:
            config: Dict with keys: name, location.

        Returns:
            Bicep template string for the attestation provider.
        """
        name = config.get("name", "ccAttestation")
        location = config.get("location", "eastus")

        return f"""// Azure Attestation provider for TEE verification
param location string = '{location}'
param attestationName string = '{name}'

resource attestationProvider 'Microsoft.Attestation/attestationProviders@2021-06-01' = {{
  name: attestationName
  location: location
  properties: {{}}
}}

output attestationId string = attestationProvider.id
output attestUri string = attestationProvider.properties.attestUri
"""

    def generate_confidential_sql(self, config: dict) -> str:
        """Generate Bicep template for Always Encrypted SQL Database.

        Args:
            config: Dict with keys: server_name, database_name, location,
                admin_login.

        Returns:
            Bicep template string for the SQL server and database.
        """
        server_name = config.get("server_name", "ccSqlServer")
        db_name = config.get("database_name", "ccDatabase")
        location = config.get("location", "eastus")
        admin_login = config.get("admin_login", "sqladmin")

        return f"""// Always Encrypted SQL Database with secure enclave support
param location string = '{location}'
param serverName string = '{server_name}'
param databaseName string = '{db_name}'
param adminLogin string = '{admin_login}'
@secure()
param adminPassword string

resource sqlServer 'Microsoft.Sql/servers@2023-08-01-preview' = {{
  name: serverName
  location: location
  properties: {{
    administratorLogin: adminLogin
    administratorLoginPassword: adminPassword
    minimalTlsVersion: '1.2'
  }}
}}

resource sqlDatabase 'Microsoft.Sql/servers/databases@2023-08-01-preview' = {{
  parent: sqlServer
  name: databaseName
  location: location
  sku: {{
    name: 'S0'
    tier: 'Standard'
  }}
  properties: {{
    preferredEnclaveType: 'VBS'
  }}
}}

resource attestationPolicy 'Microsoft.Sql/servers/databases/securityAlertPolicies@2023-08-01-preview' = {{
  parent: sqlDatabase
  name: 'Default'
  properties: {{
    state: 'Enabled'
  }}
}}

output serverId string = sqlServer.id
output databaseId string = sqlDatabase.id
output serverFqdn string = sqlServer.properties.fullyQualifiedDomainName
"""

    def generate_full_confidential_stack(self, config: dict) -> str:
        """Generate a complete confidential computing landing zone Bicep.

        Args:
            config: Dict with keys: name_prefix, location, vm_sku,
                node_count, include_aks, include_sql, include_attestation.

        Returns:
            Combined Bicep template string for the full stack.
        """
        prefix = config.get("name_prefix", "cc")
        location = config.get("location", "eastus")
        vm_sku = config.get("vm_sku", "Standard_DC4as_v5")
        include_aks = config.get("include_aks", True)
        include_sql = config.get("include_sql", True)
        include_attestation = config.get("include_attestation", True)
        node_count = config.get("node_count", 3)

        sections: list[str] = []

        # Header
        sections.append(f"""// Confidential Computing Landing Zone — full stack
// Generated by OnRamp Confidential Computing Service
targetScope = 'resourceGroup'

param location string = '{location}'
param namePrefix string = '{prefix}'
""")

        # Key Vault with mHSM
        sections.append("""// ── Key Vault with HSM ──────────────────────────────────────────────────
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${namePrefix}-kv'
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'premium'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    enablePurgeProtection: true
    enabledForDiskEncryption: true
  }
}

output keyVaultId string = keyVault.id
output keyVaultUri string = keyVault.properties.vaultUri
""")

        # Attestation provider
        if include_attestation:
            sections.append("""// ── Azure Attestation ───────────────────────────────────────────────────
resource attestation 'Microsoft.Attestation/attestationProviders@2021-06-01' = {
  name: '${namePrefix}attest'
  location: location
  properties: {}
}

output attestationUri string = attestation.properties.attestUri
""")

        # Confidential VM
        sections.append(f"""// ── Confidential VM ─────────────────────────────────────────────────────
@secure()
param vmAdminPassword string

resource ccVnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {{
  name: '${{namePrefix}}-vnet'
  location: location
  properties: {{
    addressSpace: {{
      addressPrefixes: [
        '10.0.0.0/16'
      ]
    }}
    subnets: [
      {{
        name: 'compute'
        properties: {{
          addressPrefix: '10.0.1.0/24'
        }}
      }}
      {{
        name: 'data'
        properties: {{
          addressPrefix: '10.0.2.0/24'
        }}
      }}
    ]
  }}
}}

resource ccNic 'Microsoft.Network/networkInterfaces@2023-11-01' = {{
  name: '${{namePrefix}}-vm-nic'
  location: location
  properties: {{
    ipConfigurations: [
      {{
        name: 'ipconfig1'
        properties: {{
          subnet: {{
            id: ccVnet.properties.subnets[0].id
          }}
          privateIPAllocationMethod: 'Dynamic'
        }}
      }}
    ]
  }}
}}

resource confidentialVm 'Microsoft.Compute/virtualMachines@2024-03-01' = {{
  name: '${{namePrefix}}-vm'
  location: location
  properties: {{
    hardwareProfile: {{
      vmSize: '{vm_sku}'
    }}
    osProfile: {{
      computerName: '${{namePrefix}}-vm'
      adminUsername: 'azureadmin'
      adminPassword: vmAdminPassword
    }}
    storageProfile: {{
      imageReference: {{
        publisher: 'Canonical'
        offer: '0001-com-ubuntu-confidential-vm-jammy'
        sku: '22_04-lts-cvm'
        version: 'latest'
      }}
      osDisk: {{
        createOption: 'FromImage'
        managedDisk: {{
          securityProfile: {{
            securityEncryptionType: 'VMGuestStateOnly'
          }}
        }}
      }}
    }}
    securityProfile: {{
      securityType: 'ConfidentialVM'
      uefiSettings: {{
        secureBootEnabled: true
        vTpmEnabled: true
      }}
    }}
    networkProfile: {{
      networkInterfaces: [
        {{
          id: ccNic.id
        }}
      ]
    }}
  }}
}}
""")

        # Confidential AKS
        if include_aks:
            sections.append(f"""// ── Confidential AKS ────────────────────────────────────────────────────
resource aksCluster 'Microsoft.ContainerService/managedClusters@2024-02-01' = {{
  name: '${{namePrefix}}-aks'
  location: location
  identity: {{
    type: 'SystemAssigned'
  }}
  properties: {{
    kubernetesVersion: '1.29'
    dnsPrefix: '${{namePrefix}}-aks-dns'
    agentPoolProfiles: [
      {{
        name: 'systempool'
        count: {node_count}
        vmSize: '{vm_sku}'
        osType: 'Linux'
        mode: 'System'
        enableEncryptionAtHost: true
      }}
      {{
        name: 'confpool'
        count: {node_count}
        vmSize: '{vm_sku}'
        osType: 'Linux'
        mode: 'User'
        enableEncryptionAtHost: true
        workloadRuntime: 'KataCcIsolation'
      }}
    ]
    networkProfile: {{
      networkPlugin: 'azure'
      networkPolicy: 'azure'
    }}
  }}
}}
""")

        # Always Encrypted SQL
        if include_sql:
            sections.append("""// ── Always Encrypted SQL ────────────────────────────────────────────────
@secure()
param sqlAdminPassword string

resource sqlServer 'Microsoft.Sql/servers@2023-08-01-preview' = {
  name: '${namePrefix}-sql'
  location: location
  properties: {
    administratorLogin: 'sqladmin'
    administratorLoginPassword: sqlAdminPassword
    minimalTlsVersion: '1.2'
  }
}

resource sqlDatabase 'Microsoft.Sql/servers/databases@2023-08-01-preview' = {
  parent: sqlServer
  name: '${namePrefix}-db'
  location: location
  sku: {
    name: 'S0'
    tier: 'Standard'
  }
  properties: {
    preferredEnclaveType: 'VBS'
  }
}
""")

        return "\n".join(sections)

    def _get_os_image(self, os_type: str) -> dict:
        """Return OS image reference for the given type."""
        if os_type.lower() == "windows":
            return {
                "publisher": "MicrosoftWindowsServer",
                "offer": "WindowsServer",
                "sku": "2022-datacenter-smalldisk-g2",
            }
        return {
            "publisher": "Canonical",
            "offer": "0001-com-ubuntu-confidential-vm-jammy",
            "sku": "22_04-lts-cvm",
        }


confidential_bicep_service = ConfidentialBicepService()
