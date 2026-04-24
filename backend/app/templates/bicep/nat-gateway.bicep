targetScope = 'resourceGroup'

// ---------------------------------------------------------------------------
// NAT Gateway
// Provides deterministic outbound SNAT connectivity for subnets.  All
// outbound traffic from associated subnets uses the NAT Gateway's public IP,
// eliminating port exhaustion risks of default SNAT.
// ---------------------------------------------------------------------------

@description('Azure region')
param location string

@description('Name suffix for the NAT Gateway resources')
param name string

@description('Environment name (e.g. dev, prod)')
param environment string

@description('Resource tags')
param tags object = {}

@description('Idle timeout in minutes for outbound flows (4–120)')
@minValue(4)
@maxValue(120)
param idleTimeoutMinutes int = 10

@description('Number of public IP addresses to associate (1–16)')
@minValue(1)
@maxValue(16)
param publicIpCount int = 1

// ---- Public IP addresses for the NAT Gateway ----
resource publicIps 'Microsoft.Network/publicIPAddresses@2024-01-01' = [
  for i in range(0, publicIpCount): {
    name: 'pip-natgw-${name}-${environment}-${i}'
    location: location
    tags: tags
    sku: {
      name: 'Standard'
    }
    properties: {
      publicIPAllocationMethod: 'Static'
      publicIPAddressVersion: 'IPv4'
    }
  }
]

// ---- NAT Gateway ----
resource natGateway 'Microsoft.Network/natGateways@2024-01-01' = {
  name: 'natgw-${name}-${environment}'
  location: location
  tags: tags
  sku: {
    name: 'Standard'
  }
  properties: {
    idleTimeoutInMinutes: idleTimeoutMinutes
    publicIpAddresses: [
      for i in range(0, publicIpCount): {
        id: publicIps[i].id
      }
    ]
  }
}

// ---- Outputs ----

@description('Resource ID of the NAT Gateway')
output natGatewayId string = natGateway.id

@description('Name of the NAT Gateway')
output natGatewayName string = natGateway.name

@description('Public IP addresses allocated to the NAT Gateway')
output publicIpAddresses array = [for i in range(0, publicIpCount): publicIps[i].properties.ipAddress]
