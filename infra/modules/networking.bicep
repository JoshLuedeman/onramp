// Shared virtual network for service private endpoints.
// Deployed only when enablePrivateEndpoints is true (see main.bicep).
// All private endpoints are placed in the pe-subnet; the VNet ID is used
// for DNS zone virtual-network links so private DNS resolution works.

@description('Azure region')
param location string

@description('Base name')
param baseName string

@description('Environment')
param environment string

@description('Resource tags')
param tags object

resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: 'vnet-${baseName}-${environment}'
  location: location
  tags: tags
  properties: {
    addressSpace: { addressPrefixes: ['10.1.0.0/16'] }
    subnets: [
      {
        name: 'pe-subnet'
        properties: {
          addressPrefix: '10.1.0.0/24'
          // Private endpoints do not require delegations — this subnet is
          // shared by SQL, AI Foundry, and any future service PEs.
        }
      }
    ]
  }
}

@description('Resource ID of the private endpoint subnet')
output privateEndpointSubnetId string = vnet.properties.subnets[0].id

@description('Resource ID of the virtual network')
output vnetId string = vnet.id
