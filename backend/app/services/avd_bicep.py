"""Bicep template generation for Azure Virtual Desktop resources.

Generates Bicep modules for AVD host pools, session hosts, workspaces,
application groups, FSLogix storage, networking, and monitoring.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class AvdBicepService:
    """Service for generating Bicep templates for AVD resources."""

    def generate_host_pool(self, config: dict) -> str:
        """Generate Bicep template for an AVD host pool.

        Args:
            config: Dict with keys: name, location, pool_type,
                load_balancer_type, max_session_limit.

        Returns:
            Bicep template string for the host pool resource.
        """
        name = config.get("name", "avd-hp")
        location = config.get("location", "eastus")
        pool_type = config.get("pool_type", "Pooled")
        lb_type = config.get("load_balancer_type", "BreadthFirst")
        max_session = config.get("max_session_limit", 12)

        return f"""// AVD Host Pool
param location string = '{location}'
param hostPoolName string = '{name}'

resource hostPool 'Microsoft.DesktopVirtualization/hostPools@2024-04-03' = {{
  name: hostPoolName
  location: location
  properties: {{
    hostPoolType: '{pool_type}'
    loadBalancerType: '{lb_type}'
    maxSessionLimit: {max_session}
    preferredAppGroupType: 'Desktop'
    validationEnvironment: false
    startVMOnConnect: true
    registrationInfo: {{
      registrationTokenOperation: 'Update'
      expirationTime: dateTimeAdd(utcNow(), 'PT24H')
    }}
  }}
}}

output hostPoolId string = hostPool.id
output hostPoolName string = hostPool.name
"""

    def generate_session_hosts(self, config: dict) -> str:
        """Generate Bicep template for AVD session host VMs.

        Args:
            config: Dict with keys: name_prefix, location, count,
                vm_sku, subnet_id, admin_username.

        Returns:
            Bicep template string for session host VMs.
        """
        prefix = config.get("name_prefix", "avd-sh")
        location = config.get("location", "eastus")
        count = config.get("count", 2)
        vm_sku = config.get("vm_sku", "Standard_D4s_v5")
        admin = config.get("admin_username", "avdadmin")

        return f"""// AVD Session Hosts
param location string = '{location}'
param namePrefix string = '{prefix}'
param vmCount int = {count}
param vmSize string = '{vm_sku}'
param adminUsername string = '{admin}'
@secure()
param adminPassword string
param subnetId string

resource nics 'Microsoft.Network/networkInterfaces@2023-11-01' = [
  for i in range(0, vmCount): {{
    name: '${{namePrefix}}-${{i}}-nic'
    location: location
    properties: {{
      ipConfigurations: [
        {{
          name: 'ipconfig1'
          properties: {{
            subnet: {{
              id: subnetId
            }}
            privateIPAllocationMethod: 'Dynamic'
          }}
        }}
      ]
    }}
  }}
]

resource sessionHosts 'Microsoft.Compute/virtualMachines@2024-03-01' = [
  for i in range(0, vmCount): {{
    name: '${{namePrefix}}-${{i}}'
    location: location
    zones: [
      string((i % 3) + 1)
    ]
    properties: {{
      hardwareProfile: {{
        vmSize: vmSize
      }}
      osProfile: {{
        computerName: '${{namePrefix}}-${{i}}'
        adminUsername: adminUsername
        adminPassword: adminPassword
      }}
      storageProfile: {{
        imageReference: {{
          publisher: 'MicrosoftWindowsDesktop'
          offer: 'windows-11'
          sku: 'win11-23h2-avd'
          version: 'latest'
        }}
        osDisk: {{
          createOption: 'FromImage'
          managedDisk: {{
            storageAccountType: 'Premium_LRS'
          }}
        }}
      }}
      networkProfile: {{
        networkInterfaces: [
          {{
            id: nics[i].id
          }}
        ]
      }}
      licenseType: 'Windows_Client'
    }}
  }}
]

output sessionHostIds array = [for i in range(0, vmCount): sessionHosts[i].id]
"""

    def generate_workspace(self, config: dict) -> str:
        """Generate Bicep template for an AVD workspace.

        Args:
            config: Dict with keys: name, location, friendly_name,
                app_group_ids.

        Returns:
            Bicep template string for the workspace resource.
        """
        name = config.get("name", "avd-ws")
        location = config.get("location", "eastus")
        friendly = config.get("friendly_name", "AVD Workspace")

        return f"""// AVD Workspace
param location string = '{location}'
param workspaceName string = '{name}'

resource workspace 'Microsoft.DesktopVirtualization/workspaces@2024-04-03' = {{
  name: workspaceName
  location: location
  properties: {{
    friendlyName: '{friendly}'
    applicationGroupReferences: []
  }}
}}

output workspaceId string = workspace.id
"""

    def generate_app_group(self, config: dict) -> str:
        """Generate Bicep template for an AVD application group.

        Args:
            config: Dict with keys: name, location, host_pool_id,
                group_type, friendly_name.

        Returns:
            Bicep template string for the application group.
        """
        name = config.get("name", "avd-dag")
        location = config.get("location", "eastus")
        group_type = config.get("group_type", "Desktop")
        friendly = config.get("friendly_name", "Desktop")

        return f"""// AVD Application Group
param location string = '{location}'
param appGroupName string = '{name}'
param hostPoolId string

resource appGroup 'Microsoft.DesktopVirtualization/applicationGroups@2024-04-03' = {{
  name: appGroupName
  location: location
  properties: {{
    hostPoolArmPath: hostPoolId
    applicationGroupType: '{group_type}'
    friendlyName: '{friendly}'
  }}
}}

output appGroupId string = appGroup.id
"""

    def generate_storage(self, config: dict) -> str:
        """Generate Bicep template for FSLogix profile storage.

        Args:
            config: Dict with keys: name, location, storage_type,
                share_name, share_quota_gb.

        Returns:
            Bicep template string for the storage resource.
        """
        name = config.get("name", "avdfslogix")
        location = config.get("location", "eastus")
        share_name = config.get("share_name", "fslogix-profiles")
        quota = config.get("share_quota_gb", 100)

        return f"""// FSLogix Profile Storage (Azure Files Premium)
param location string = '{location}'
param storageAccountName string = '{name}'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {{
  name: storageAccountName
  location: location
  kind: 'FileStorage'
  sku: {{
    name: 'Premium_LRS'
  }}
  properties: {{
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowSharedKeyAccess: false
  }}
}}

resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2023-05-01' = {{
  parent: storageAccount
  name: 'default'
}}

resource share 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {{
  parent: fileService
  name: '{share_name}'
  properties: {{
    shareQuota: {quota}
    enabledProtocols: 'SMB'
  }}
}}

output storageId string = storageAccount.id
output shareUrl string = '${{storageAccount.name}}.file.core.windows.net'
"""

    def generate_networking(self, config: dict) -> str:
        """Generate Bicep template for AVD networking.

        Args:
            config: Dict with keys: name_prefix, location,
                vnet_address_space, session_host_subnet,
                private_endpoint_subnet.

        Returns:
            Bicep template string for VNet, subnets, and NSG.
        """
        prefix = config.get("name_prefix", "avd")
        location = config.get("location", "eastus")
        vnet_space = config.get(
            "vnet_address_space", "10.0.0.0/16"
        )
        sh_subnet = config.get(
            "session_host_subnet", "10.0.1.0/24"
        )
        pe_subnet = config.get(
            "private_endpoint_subnet", "10.0.2.0/24"
        )

        return f"""// AVD Networking
param location string = '{location}'
param namePrefix string = '{prefix}'

resource nsg 'Microsoft.Network/networkSecurityGroups@2023-11-01' = {{
  name: '${{namePrefix}}-nsg'
  location: location
  properties: {{
    securityRules: [
      {{
        name: 'AllowRDP'
        properties: {{
          priority: 1000
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '3389'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: '*'
        }}
      }}
      {{
        name: 'DenyAllInbound'
        properties: {{
          priority: 4096
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
        }}
      }}
    ]
  }}
}}

resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {{
  name: '${{namePrefix}}-vnet'
  location: location
  properties: {{
    addressSpace: {{
      addressPrefixes: [
        '{vnet_space}'
      ]
    }}
    subnets: [
      {{
        name: 'SessionHosts'
        properties: {{
          addressPrefix: '{sh_subnet}'
          networkSecurityGroup: {{
            id: nsg.id
          }}
        }}
      }}
      {{
        name: 'PrivateEndpoints'
        properties: {{
          addressPrefix: '{pe_subnet}'
        }}
      }}
    ]
  }}
}}

output vnetId string = vnet.id
output sessionHostSubnetId string = vnet.properties.subnets[0].id
output privateEndpointSubnetId string = vnet.properties.subnets[1].id
"""

    def generate_full_avd_stack(self, config: dict) -> str:
        """Generate a complete AVD landing zone Bicep template.

        Args:
            config: Dict with keys: name_prefix, location, pool_type,
                vm_sku, host_count, max_session_limit,
                storage_type, share_quota_gb.

        Returns:
            Combined Bicep template string for the full AVD stack.
        """
        prefix = config.get("name_prefix", "avd")
        location = config.get("location", "eastus")
        pool_type = config.get("pool_type", "Pooled")
        vm_sku = config.get("vm_sku", "Standard_D4s_v5")
        host_count = config.get("host_count", 2)
        max_session = config.get("max_session_limit", 12)
        quota = config.get("share_quota_gb", 100)

        lb_type = (
            "Persistent" if pool_type == "Personal"
            else "BreadthFirst"
        )

        sections: list[str] = []

        sections.append(f"""// Azure Virtual Desktop Landing Zone — full stack
// Generated by OnRamp AVD Accelerator
targetScope = 'resourceGroup'

param location string = '{location}'
param namePrefix string = '{prefix}'
@secure()
param vmAdminPassword string
""")

        # Host Pool
        sections.append(f"""// ── Host Pool ───────────────────────────────────────────────────────────
resource hostPool 'Microsoft.DesktopVirtualization/hostPools@2024-04-03' = {{
  name: '${{namePrefix}}-hp'
  location: location
  properties: {{
    hostPoolType: '{pool_type}'
    loadBalancerType: '{lb_type}'
    maxSessionLimit: {max_session}
    preferredAppGroupType: 'Desktop'
    validationEnvironment: false
    startVMOnConnect: true
  }}
}}
""")

        # App Group
        sections.append("""// ── Application Group ───────────────────────────────────────────────────
resource desktopAppGroup 'Microsoft.DesktopVirtualization/applicationGroups@2024-04-03' = {
  name: '${namePrefix}-dag'
  location: location
  properties: {
    hostPoolArmPath: hostPool.id
    applicationGroupType: 'Desktop'
    friendlyName: 'Desktop'
  }
}
""")

        # Workspace
        sections.append("""// ── Workspace ───────────────────────────────────────────────────────────
resource workspace 'Microsoft.DesktopVirtualization/workspaces@2024-04-03' = {
  name: '${namePrefix}-ws'
  location: location
  properties: {
    friendlyName: 'Azure Virtual Desktop'
    applicationGroupReferences: [
      desktopAppGroup.id
    ]
  }
}
""")

        # Networking
        sections.append("""// ── Networking ──────────────────────────────────────────────────────────
resource nsg 'Microsoft.Network/networkSecurityGroups@2023-11-01' = {
  name: '${namePrefix}-nsg'
  location: location
  properties: {
    securityRules: [
      {
        name: 'AllowRDP'
        properties: {
          priority: 1000
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '3389'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: '*'
        }
      }
    ]
  }
}

resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: '${namePrefix}-vnet'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.0.0.0/16'
      ]
    }
    subnets: [
      {
        name: 'SessionHosts'
        properties: {
          addressPrefix: '10.0.1.0/24'
          networkSecurityGroup: {
            id: nsg.id
          }
        }
      }
      {
        name: 'PrivateEndpoints'
        properties: {
          addressPrefix: '10.0.2.0/24'
        }
      }
    ]
  }
}
""")

        # Storage
        sections.append(f"""// ── FSLogix Storage ─────────────────────────────────────────────────────
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {{
  name: '${{namePrefix}}fslogix'
  location: location
  kind: 'FileStorage'
  sku: {{
    name: 'Premium_LRS'
  }}
  properties: {{
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }}
}}

resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2023-05-01' = {{
  parent: storageAccount
  name: 'default'
}}

resource profileShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {{
  parent: fileService
  name: 'fslogix-profiles'
  properties: {{
    shareQuota: {quota}
    enabledProtocols: 'SMB'
  }}
}}
""")

        # Session Hosts
        sections.append(f"""// ── Session Hosts ───────────────────────────────────────────────────────
resource nics 'Microsoft.Network/networkInterfaces@2023-11-01' = [
  for i in range(0, {host_count}): {{
    name: '${{namePrefix}}-sh-${{i}}-nic'
    location: location
    properties: {{
      ipConfigurations: [
        {{
          name: 'ipconfig1'
          properties: {{
            subnet: {{
              id: vnet.properties.subnets[0].id
            }}
            privateIPAllocationMethod: 'Dynamic'
          }}
        }}
      ]
    }}
  }}
]

resource sessionHosts 'Microsoft.Compute/virtualMachines@2024-03-01' = [
  for i in range(0, {host_count}): {{
    name: '${{namePrefix}}-sh-${{i}}'
    location: location
    zones: [
      string((i % 3) + 1)
    ]
    properties: {{
      hardwareProfile: {{
        vmSize: '{vm_sku}'
      }}
      osProfile: {{
        computerName: '${{namePrefix}}-sh-${{i}}'
        adminUsername: 'avdadmin'
        adminPassword: vmAdminPassword
      }}
      storageProfile: {{
        imageReference: {{
          publisher: 'MicrosoftWindowsDesktop'
          offer: 'windows-11'
          sku: 'win11-23h2-avd'
          version: 'latest'
        }}
        osDisk: {{
          createOption: 'FromImage'
          managedDisk: {{
            storageAccountType: 'Premium_LRS'
          }}
        }}
      }}
      networkProfile: {{
        networkInterfaces: [
          {{
            id: nics[i].id
          }}
        ]
      }}
      licenseType: 'Windows_Client'
    }}
  }}
]
""")

        # Monitoring
        sections.append("""// ── Monitoring ──────────────────────────────────────────────────────────
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${namePrefix}-law'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: hostPool
  name: '${namePrefix}-hp-diag'
  properties: {
    workspaceId: logAnalytics.id
    logs: [
      {
        categoryGroup: 'allLogs'
        enabled: true
      }
    ]
  }
}

output hostPoolId string = hostPool.id
output workspaceId string = workspace.id
output logAnalyticsId string = logAnalytics.id
""")

        return "\n".join(sections)


avd_bicep_service = AvdBicepService()
