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

// ----- Network Security Group with default security rules -----
// Rules enforce a deny-by-default posture with explicit allows for required traffic.
resource nsg 'Microsoft.Network/networkSecurityGroups@2024-01-01' = {
  name: 'nsg-${spokeName}'
  location: location
  tags: tags
  properties: {
    securityRules: [
      // Allow HTTPS inbound from within the virtual network (app traffic)
      {
        name: 'AllowHttpsInbound'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '443'
          description: 'Allow HTTPS traffic from within the virtual network'
        }
      }
      // Allow all internal VNet-to-VNet traffic (inter-subnet / peered traffic)
      {
        name: 'AllowVnetInternalInbound'
        properties: {
          priority: 200
          direction: 'Inbound'
          access: 'Allow'
          protocol: '*'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: 'VirtualNetwork'
          destinationPortRange: '*'
          description: 'Allow all internal VNet-to-VNet traffic'
        }
      }
      // Allow Azure Load Balancer health probes
      {
        name: 'AllowAzureLoadBalancerInbound'
        properties: {
          priority: 300
          direction: 'Inbound'
          access: 'Allow'
          protocol: '*'
          sourceAddressPrefix: 'AzureLoadBalancer'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
          description: 'Allow Azure Load Balancer health probes'
        }
      }
      // Deny all other inbound traffic from the Internet (catch-all)
      {
        name: 'DenyAllInternetInbound'
        properties: {
          priority: 4096
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourceAddressPrefix: 'Internet'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
          description: 'Deny all inbound traffic from the Internet'
        }
      }
    ]
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
