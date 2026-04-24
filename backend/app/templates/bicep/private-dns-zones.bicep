targetScope = 'resourceGroup'

// ---------------------------------------------------------------------------
// Private DNS Zones
// Creates private DNS zones for Azure Private Link services and links them to
// a virtual network so that resources in the VNet can resolve private endpoint
// FQDNs to their private IP addresses.
// ---------------------------------------------------------------------------

@description('Azure region (unused — DNS zones are global, but kept for template interface consistency)')
#disable-next-line no-unused-params
param location string = resourceGroup().location

@description('Environment name (e.g. dev, prod)')
param environment string

@description('Resource tags')
param tags object = {}

@description('Resource ID of the virtual network to link DNS zones to')
param vnetId string

@description('List of private DNS zone names to create (e.g. privatelink.database.windows.net)')
#disable-next-line no-hardcoded-env-urls
param zoneNames array = [
  #disable-next-line no-hardcoded-env-urls
  'privatelink.database.windows.net'
  'privatelink.vaultcore.azure.net'
  #disable-next-line no-hardcoded-env-urls
  'privatelink.blob.core.windows.net'
  'privatelink.azurewebsites.net'
]

// ---- Private DNS Zones ----
resource dnsZones 'Microsoft.Network/privateDnsZones@2024-06-01' = [
  for zoneName in zoneNames: {
    name: zoneName
    location: 'global'
    tags: tags
  }
]

// ---- VNet Links (one per zone) ----
// Links each DNS zone to the specified VNet so name resolution flows through
// the private DNS zone for resources with private endpoints.
resource vnetLinks 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = [
  for (zoneName, i) in zoneNames: {
    parent: dnsZones[i]
    name: 'vnetlink-${environment}-${i}'
    location: 'global'
    tags: tags
    properties: {
      virtualNetwork: {
        id: vnetId
      }
      registrationEnabled: false
    }
  }
]

// ---- Outputs ----

@description('Resource IDs of the created private DNS zones')
output zoneIds array = [for (zoneName, i) in zoneNames: dnsZones[i].id]

@description('Names of the created private DNS zones')
output zoneNamesOutput array = [for (zoneName, i) in zoneNames: dnsZones[i].name]
