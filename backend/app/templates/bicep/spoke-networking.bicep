targetScope = 'resourceGroup'

@description('Azure region')
param location string

@description('Spoke name')
param spokeName string

@description('Spoke VNet CIDR')
param spokeCidr string

@description('Hub VNet ID for peering')
param hubVnetId string

@description('Resource tags')
param tags object = {}

resource spokeVnet 'Microsoft.Network/virtualNetworks@2024-01-01' = {
  name: 'vnet-${spokeName}'
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [spokeCidr]
    }
    subnets: [
      {
        name: 'snet-default'
        properties: {
          addressPrefix: cidrSubnet(spokeCidr, 24, 0)
          networkSecurityGroup: {
            id: nsg.id
          }
        }
      }
    ]
  }
}

resource nsg 'Microsoft.Network/networkSecurityGroups@2024-01-01' = {
  name: 'nsg-${spokeName}'
  location: location
  tags: tags
  properties: {
    securityRules: []
  }
}

resource peerToHub 'Microsoft.Network/virtualNetworks/virtualNetworkPeerings@2024-01-01' = {
  parent: spokeVnet
  name: 'peer-to-hub'
  properties: {
    remoteVirtualNetwork: {
      id: hubVnetId
    }
    allowVirtualNetworkAccess: true
    allowForwardedTraffic: true
    useRemoteGateways: false
  }
}

output spokeVnetId string = spokeVnet.id
