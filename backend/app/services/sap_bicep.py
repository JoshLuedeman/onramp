"""Bicep template generation for SAP on Azure resources.

Generates Bicep modules for HANA VMs, SAP application servers,
ASCS/SCS clusters, Standard Load Balancers, Azure NetApp Files,
proximity placement groups, and Azure Backup for SAP HANA.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class SapBicepService:
    """Service for generating Bicep templates for SAP on Azure."""

    def generate_hana_vm(self, config: dict) -> str:
        """Generate Bicep template for an SAP HANA database VM.

        Args:
            config: Dict with keys: name, location, vm_sku,
                admin_username, enable_hsr, enable_accelerated_networking.

        Returns:
            Bicep template string for the HANA VM resource.
        """
        name = config.get("name", "sapHanaVm")
        location = config.get("location", "eastus")
        vm_sku = config.get("vm_sku", "Standard_M64s")
        admin_username = config.get("admin_username", "azureadmin")
        accel_net = config.get(
            "enable_accelerated_networking", True
        )

        return f"""// SAP HANA Database VM — certified for production HANA
param location string = '{location}'
param vmName string = '{name}'
param adminUsername string = '{admin_username}'
@secure()
param adminPasswordOrKey string
param proximityPlacementGroupId string = ''

resource hanaNic 'Microsoft.Network/networkInterfaces@2023-11-01' = {{
  name: '${{vmName}}-nic'
  location: location
  properties: {{
    ipConfigurations: [
      {{
        name: 'ipconfig1'
        properties: {{
          subnet: {{
            id: dbSubnet.id
          }}
          privateIPAllocationMethod: 'Dynamic'
        }}
      }}
    ]
    enableAcceleratedNetworking: {str(accel_net).lower()}
  }}
}}

resource hanaVm 'Microsoft.Compute/virtualMachines@2024-03-01' = {{
  name: vmName
  location: location
  properties: {{
    hardwareProfile: {{
      vmSize: '{vm_sku}'
    }}
    proximityPlacementGroup: proximityPlacementGroupId != '' ? {{
      id: proximityPlacementGroupId
    }} : null
    osProfile: {{
      computerName: vmName
      adminUsername: adminUsername
      adminPassword: adminPasswordOrKey
    }}
    storageProfile: {{
      imageReference: {{
        publisher: 'SUSE'
        offer: 'sles-sap-15-sp5'
        sku: 'gen2'
        version: 'latest'
      }}
      osDisk: {{
        createOption: 'FromImage'
        managedDisk: {{
          storageAccountType: 'Premium_LRS'
        }}
      }}
      dataDisks: [
        {{
          lun: 0
          createOption: 'Empty'
          diskSizeGB: 512
          managedDisk: {{
            storageAccountType: 'Premium_LRS'
          }}
        }}
      ]
    }}
    networkProfile: {{
      networkInterfaces: [
        {{
          id: hanaNic.id
        }}
      ]
    }}
  }}
}}

output vmId string = hanaVm.id
output vmName string = hanaVm.name
"""

    def generate_app_server(self, config: dict) -> str:
        """Generate Bicep template for SAP application server VMs.

        Args:
            config: Dict with keys: name, location, vm_sku, vm_count,
                admin_username, enable_accelerated_networking.

        Returns:
            Bicep template string for SAP app server resources.
        """
        name = config.get("name", "sapAppServer")
        location = config.get("location", "eastus")
        vm_sku = config.get("vm_sku", "Standard_E16s_v5")
        vm_count = config.get("vm_count", 2)
        admin_username = config.get("admin_username", "azureadmin")
        accel_net = config.get(
            "enable_accelerated_networking", True
        )

        return f"""// SAP Application Server cluster
param location string = '{location}'
param namePrefix string = '{name}'
param vmCount int = {vm_count}
param adminUsername string = '{admin_username}'
@secure()
param adminPasswordOrKey string
param proximityPlacementGroupId string = ''

resource appNic 'Microsoft.Network/networkInterfaces@2023-11-01' = [
  for i in range(0, vmCount): {{
    name: '${{namePrefix}}-${{i}}-nic'
    location: location
    properties: {{
      ipConfigurations: [
        {{
          name: 'ipconfig1'
          properties: {{
            subnet: {{
              id: appSubnet.id
            }}
            privateIPAllocationMethod: 'Dynamic'
          }}
        }}
      ]
      enableAcceleratedNetworking: {str(accel_net).lower()}
    }}
  }}
]

resource appVm 'Microsoft.Compute/virtualMachines@2024-03-01' = [
  for i in range(0, vmCount): {{
    name: '${{namePrefix}}-${{i}}'
    location: location
    properties: {{
      hardwareProfile: {{
        vmSize: '{vm_sku}'
      }}
      proximityPlacementGroup: proximityPlacementGroupId != '' ? {{
        id: proximityPlacementGroupId
      }} : null
      osProfile: {{
        computerName: '${{namePrefix}}-${{i}}'
        adminUsername: adminUsername
        adminPassword: adminPasswordOrKey
      }}
      storageProfile: {{
        imageReference: {{
          publisher: 'SUSE'
          offer: 'sles-sap-15-sp5'
          sku: 'gen2'
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
            id: appNic[i].id
          }}
        ]
      }}
    }}
  }}
]

output appVmIds array = [for i in range(0, vmCount): appVm[i].id]
"""

    def generate_full_sap_stack(self, config: dict) -> str:
        """Generate a complete SAP landing zone Bicep template.

        Args:
            config: Dict with keys: name_prefix, location, hana_sku,
                app_sku, app_count, ha_enabled, include_anf,
                include_backup, include_monitoring.

        Returns:
            Combined Bicep template string for the full SAP stack.
        """
        prefix = config.get("name_prefix", "sap")
        location = config.get("location", "eastus")
        hana_sku = config.get("hana_sku", "Standard_M64s")
        app_sku = config.get("app_sku", "Standard_E16s_v5")
        app_count = config.get("app_count", 2)
        ha_enabled = config.get("ha_enabled", True)
        include_anf = config.get("include_anf", True)
        include_backup = config.get("include_backup", True)
        include_monitoring = config.get("include_monitoring", True)

        hana_count = 2 if ha_enabled else 1

        sections: list[str] = []

        # Header
        sections.append(f"""// SAP on Azure Landing Zone — full stack
// Generated by OnRamp SAP Accelerator
targetScope = 'resourceGroup'

param location string = '{location}'
param namePrefix string = '{prefix}'
@secure()
param adminPassword string
""")

        # Proximity placement group
        sections.append("""// ── Proximity Placement Group ───────────────
resource ppg 'Microsoft.Compute/proximityPlacementGroups@2024-03-01' = {
  name: '${namePrefix}-ppg'
  location: location
  properties: {
    proximityPlacementGroupType: 'Standard'
  }
}
""")

        # VNet and subnets
        sections.append("""// ── Virtual Network ─────────────────────────
resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: '${namePrefix}-vnet'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.1.0.0/16'
      ]
    }
    subnets: [
      {
        name: 'sap-db'
        properties: {
          addressPrefix: '10.1.1.0/24'
        }
      }
      {
        name: 'sap-app'
        properties: {
          addressPrefix: '10.1.2.0/24'
        }
      }
      {
        name: 'sap-web'
        properties: {
          addressPrefix: '10.1.3.0/24'
        }
      }
    ]
  }
}

resource dbSubnet 'Microsoft.Network/virtualNetworks/subnets@2023-11-01' existing = {
  parent: vnet
  name: 'sap-db'
}

resource appSubnet 'Microsoft.Network/virtualNetworks/subnets@2023-11-01' existing = {
  parent: vnet
  name: 'sap-app'
}
""")

        # HANA Load Balancer
        if ha_enabled:
            sections.append("""// ── HANA Standard Load Balancer ─────────────
resource hanaLb 'Microsoft.Network/loadBalancers@2023-11-01' = {
  name: '${namePrefix}-hana-lb'
  location: location
  sku: {
    name: 'Standard'
  }
  properties: {
    frontendIPConfigurations: [
      {
        name: 'hana-frontend'
        properties: {
          subnet: {
            id: dbSubnet.id
          }
          privateIPAllocationMethod: 'Dynamic'
        }
      }
    ]
    backendAddressPools: [
      {
        name: 'hana-backend'
      }
    ]
    loadBalancingRules: [
      {
        name: 'hana-ha-rule'
        properties: {
          frontendIPConfiguration: {
            id: resourceId(
              'Microsoft.Network/loadBalancers/frontendIPConfigurations'
              '${namePrefix}-hana-lb'
              'hana-frontend'
            )
          }
          backendAddressPool: {
            id: resourceId(
              'Microsoft.Network/loadBalancers/backendAddressPools'
              '${namePrefix}-hana-lb'
              'hana-backend'
            )
          }
          protocol: 'All'
          frontendPort: 0
          backendPort: 0
          enableFloatingIP: true
          idleTimeoutInMinutes: 30
        }
      }
    ]
    probes: [
      {
        name: 'hana-probe'
        properties: {
          protocol: 'Tcp'
          port: 62503
          intervalInSeconds: 5
          numberOfProbes: 2
        }
      }
    ]
  }
}
""")

        # HANA VMs
        sections.append(f"""// ── HANA Database VMs ───────────────────────
resource hanaNic 'Microsoft.Network/networkInterfaces@2023-11-01' = [
  for i in range(0, {hana_count}): {{
    name: '${{namePrefix}}-hana-${{i}}-nic'
    location: location
    properties: {{
      ipConfigurations: [
        {{
          name: 'ipconfig1'
          properties: {{
            subnet: {{
              id: dbSubnet.id
            }}
            privateIPAllocationMethod: 'Dynamic'
          }}
        }}
      ]
      enableAcceleratedNetworking: true
    }}
  }}
]

resource hanaVm 'Microsoft.Compute/virtualMachines@2024-03-01' = [
  for i in range(0, {hana_count}): {{
    name: '${{namePrefix}}-hana-${{i}}'
    location: location
    properties: {{
      hardwareProfile: {{
        vmSize: '{hana_sku}'
      }}
      proximityPlacementGroup: {{
        id: ppg.id
      }}
      osProfile: {{
        computerName: '${{namePrefix}}-hana-${{i}}'
        adminUsername: 'azureadmin'
        adminPassword: adminPassword
      }}
      storageProfile: {{
        imageReference: {{
          publisher: 'SUSE'
          offer: 'sles-sap-15-sp5'
          sku: 'gen2'
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
            id: hanaNic[i].id
          }}
        ]
      }}
    }}
  }}
]
""")

        # App servers
        sections.append(f"""// ── SAP Application Servers ─────────────────
resource appNic 'Microsoft.Network/networkInterfaces@2023-11-01' = [
  for i in range(0, {app_count}): {{
    name: '${{namePrefix}}-app-${{i}}-nic'
    location: location
    properties: {{
      ipConfigurations: [
        {{
          name: 'ipconfig1'
          properties: {{
            subnet: {{
              id: appSubnet.id
            }}
            privateIPAllocationMethod: 'Dynamic'
          }}
        }}
      ]
      enableAcceleratedNetworking: true
    }}
  }}
]

resource appVm 'Microsoft.Compute/virtualMachines@2024-03-01' = [
  for i in range(0, {app_count}): {{
    name: '${{namePrefix}}-app-${{i}}'
    location: location
    properties: {{
      hardwareProfile: {{
        vmSize: '{app_sku}'
      }}
      proximityPlacementGroup: {{
        id: ppg.id
      }}
      osProfile: {{
        computerName: '${{namePrefix}}-app-${{i}}'
        adminUsername: 'azureadmin'
        adminPassword: adminPassword
      }}
      storageProfile: {{
        imageReference: {{
          publisher: 'SUSE'
          offer: 'sles-sap-15-sp5'
          sku: 'gen2'
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
            id: appNic[i].id
          }}
        ]
      }}
    }}
  }}
]
""")

        # ASCS cluster
        ascs_count = 2 if ha_enabled else 1
        sections.append(f"""// ── ASCS/SCS Cluster ────────────────────────
resource ascsNic 'Microsoft.Network/networkInterfaces@2023-11-01' = [
  for i in range(0, {ascs_count}): {{
    name: '${{namePrefix}}-ascs-${{i}}-nic'
    location: location
    properties: {{
      ipConfigurations: [
        {{
          name: 'ipconfig1'
          properties: {{
            subnet: {{
              id: appSubnet.id
            }}
            privateIPAllocationMethod: 'Dynamic'
          }}
        }}
      ]
      enableAcceleratedNetworking: true
    }}
  }}
]

resource ascsVm 'Microsoft.Compute/virtualMachines@2024-03-01' = [
  for i in range(0, {ascs_count}): {{
    name: '${{namePrefix}}-ascs-${{i}}'
    location: location
    properties: {{
      hardwareProfile: {{
        vmSize: 'Standard_E4s_v5'
      }}
      proximityPlacementGroup: {{
        id: ppg.id
      }}
      osProfile: {{
        computerName: '${{namePrefix}}-ascs-${{i}}'
        adminUsername: 'azureadmin'
        adminPassword: adminPassword
      }}
      storageProfile: {{
        imageReference: {{
          publisher: 'SUSE'
          offer: 'sles-sap-15-sp5'
          sku: 'gen2'
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
            id: ascsNic[i].id
          }}
        ]
      }}
    }}
  }}
]
""")

        # Azure NetApp Files
        if include_anf:
            sections.append("""// ── Azure NetApp Files ──────────────────────
resource anfAccount 'Microsoft.NetApp/netAppAccounts@2023-11-01' = {
  name: '${namePrefix}-anf'
  location: location
  properties: {}
}

resource anfPool 'Microsoft.NetApp/netAppAccounts/capacityPools@2023-11-01' = {
  parent: anfAccount
  name: '${namePrefix}-pool'
  location: location
  properties: {
    serviceLevel: 'Premium'
    size: 4398046511104 // 4 TiB
  }
}
""")

        # Azure Backup
        if include_backup:
            sections.append("""// ── Azure Backup for SAP HANA ───────────────
resource backupVault 'Microsoft.RecoveryServices/vaults@2024-01-01' = {
  name: '${namePrefix}-backup'
  location: location
  sku: {
    name: 'RS0'
    tier: 'Standard'
  }
  properties: {}
}
""")

        # Azure Monitor for SAP
        if include_monitoring:
            sections.append("""// ── Azure Monitor for SAP Solutions ─────────
resource sapMonitor 'Microsoft.Workloads/monitors@2023-04-01' = {
  name: '${namePrefix}-monitor'
  location: location
  properties: {
    appLocation: location
    routingPreference: 'Default'
    managedResourceGroupConfiguration: {
      name: '${namePrefix}-monitor-mrg'
    }
  }
}
""")

        return "\n".join(sections)


sap_bicep_service = SapBicepService()
