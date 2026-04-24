targetScope = 'resourceGroup'

// ---------------------------------------------------------------------------
// VPN Gateway
// Deploys an Azure VPN Gateway for site-to-site (S2S) or point-to-site (P2S)
// hybrid connectivity.  Requires a GatewaySubnet in the target VNet.
// ---------------------------------------------------------------------------

@description('Azure region')
param location string

@description('Environment name (e.g. dev, prod)')
param environment string

@description('Resource tags')
param tags object = {}

@description('Resource ID of the GatewaySubnet where the VPN Gateway will be deployed')
param gatewaySubnetId string

@description('VPN Gateway SKU')
@allowed([
  'VpnGw1'
  'VpnGw2'
  'VpnGw3'
  'VpnGw1AZ'
  'VpnGw2AZ'
  'VpnGw3AZ'
])
param gatewaySku string = 'VpnGw1'

@description('VPN type')
@allowed(['RouteBased', 'PolicyBased'])
param vpnType string = 'RouteBased'

@description('Enable active-active mode for high availability')
param enableActiveActive bool = false

@description('Enable BGP for dynamic routing')
param enableBgp bool = false

@description('BGP ASN (Autonomous System Number) — required when enableBgp is true')
param bgpAsn int = 65515

@description('On-premises VPN device public IP address for site-to-site connection (optional)')
param onPremGatewayIp string = ''

@description('On-premises address prefixes reachable through the VPN tunnel')
param onPremAddressPrefixes array = []

@description('Pre-shared key for the site-to-site VPN connection')
@secure()
param vpnSharedKey string = ''

// ---- Public IP for VPN Gateway ----
resource vpnGatewayPip 'Microsoft.Network/publicIPAddresses@2024-01-01' = {
  name: 'pip-vpngw-${environment}'
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

// ---- Secondary PIP for active-active mode ----
resource vpnGatewayPip2 'Microsoft.Network/publicIPAddresses@2024-01-01' = if (enableActiveActive) {
  name: 'pip-vpngw-${environment}-2'
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

// ---- VPN Gateway ----
var baseIpConfigs = [
  {
    name: 'ipconfig1'
    properties: {
      publicIPAddress: {
        id: vpnGatewayPip.id
      }
      subnet: {
        id: gatewaySubnetId
      }
    }
  }
]

var activeActiveIpConfigs = enableActiveActive
  ? [
      {
        name: 'ipconfig2'
        properties: {
          publicIPAddress: {
            id: vpnGatewayPip2.id
          }
          subnet: {
            id: gatewaySubnetId
          }
        }
      }
    ]
  : []

resource vpnGateway 'Microsoft.Network/virtualNetworkGateways@2024-01-01' = {
  name: 'vpngw-${environment}'
  location: location
  tags: tags
  properties: {
    gatewayType: 'Vpn'
    vpnType: vpnType
    activeActive: enableActiveActive
    enableBgp: enableBgp
    bgpSettings: enableBgp
      ? {
          asn: bgpAsn
        }
      : null
    sku: {
      name: gatewaySku
      tier: gatewaySku
    }
    ipConfigurations: concat(baseIpConfigs, activeActiveIpConfigs)
  }
}

// ---- Local Network Gateway (on-premises representation) ----
resource localNetworkGateway 'Microsoft.Network/localNetworkGateways@2024-01-01' = if (!empty(onPremGatewayIp)) {
  name: 'lgw-onprem-${environment}'
  location: location
  tags: tags
  properties: {
    gatewayIpAddress: onPremGatewayIp
    localNetworkAddressSpace: {
      addressPrefixes: onPremAddressPrefixes
    }
  }
}

// ---- Site-to-Site VPN Connection ----
resource vpnConnection 'Microsoft.Network/connections@2024-01-01' = if (!empty(onPremGatewayIp) && !empty(vpnSharedKey)) {
  name: 'cn-s2s-${environment}'
  location: location
  tags: tags
  properties: {
    connectionType: 'IPsec'
    virtualNetworkGateway1: {
      id: vpnGateway.id
      properties: {}
    }
    localNetworkGateway2: {
      id: localNetworkGateway.id
      properties: {}
    }
    sharedKey: vpnSharedKey
    enableBgp: enableBgp
  }
}

// ---- Outputs ----

@description('Resource ID of the VPN Gateway')
output vpnGatewayId string = vpnGateway.id

@description('Public IP address of the VPN Gateway')
output vpnGatewayPublicIp string = vpnGatewayPip.properties.ipAddress

@description('Resource ID of the local network gateway (empty if not created)')
output localNetworkGatewayId string = !empty(onPremGatewayIp) ? localNetworkGateway.id : ''
