targetScope = 'resourceGroup'

@description('Azure region')
param location string

@description('Hub VNet CIDR')
param hubCidr string = '10.0.0.0/16'

@description('Enable Azure Firewall')
param enableFirewall bool = true

@description('Enable Bastion')
param enableBastion bool = true

@description('Resource tags')
param tags object = {}

resource hubVnet 'Microsoft.Network/virtualNetworks@2024-01-01' = {
  name: 'vnet-hub'
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [hubCidr]
    }
    subnets: [
      {
        name: 'AzureFirewallSubnet'
        properties: {
          addressPrefix: cidrSubnet(hubCidr, 24, 1)
        }
      }
      {
        name: 'GatewaySubnet'
        properties: {
          addressPrefix: cidrSubnet(hubCidr, 24, 2)
        }
      }
      {
        name: 'AzureBastionSubnet'
        properties: {
          addressPrefix: cidrSubnet(hubCidr, 24, 3)
        }
      }
    ]
  }
}

resource firewallPip 'Microsoft.Network/publicIPAddresses@2024-01-01' = if (enableFirewall) {
  name: 'pip-firewall'
  location: location
  tags: tags
  sku: {
    name: 'Standard'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
  }
}

resource firewall 'Microsoft.Network/azureFirewalls@2024-01-01' = if (enableFirewall) {
  name: 'afw-hub'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'AZFW_VNet'
      tier: 'Standard'
    }
    ipConfigurations: [
      {
        name: 'ipconfig1'
        properties: {
          subnet: {
            id: hubVnet.properties.subnets[0].id
          }
          publicIPAddress: {
            id: firewallPip.id
          }
        }
      }
    ]
  }
}

resource bastionPip 'Microsoft.Network/publicIPAddresses@2024-01-01' = if (enableBastion) {
  name: 'pip-bastion'
  location: location
  tags: tags
  sku: {
    name: 'Standard'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
  }
}

resource bastion 'Microsoft.Network/bastionHosts@2024-01-01' = if (enableBastion) {
  name: 'bas-hub'
  location: location
  tags: tags
  sku: {
    name: 'Standard'
  }
  properties: {
    ipConfigurations: [
      {
        name: 'ipconfig1'
        properties: {
          subnet: {
            id: hubVnet.properties.subnets[2].id
          }
          publicIPAddress: {
            id: bastionPip.id
          }
        }
      }
    ]
  }
}

output hubVnetId string = hubVnet.id
output firewallPrivateIp string = enableFirewall ? firewall.properties.ipConfigurations[0].properties.privateIPAddress : ''
