@description('Azure region')
param location string

@description('Base name')
param baseName string

@description('Environment')
param environment string

@description('Resource tags')
param tags object

@description('Principal (object) ID of the app managed identity for RBAC')
param managedIdentityPrincipalId string

@description('Enable private endpoint and disable public network access. When false, the resource remains publicly accessible (suitable for dev).')
param enablePrivateEndpoints bool = false

@description('Resource ID of the subnet for private endpoints. Required when enablePrivateEndpoints is true.')
param privateEndpointSubnetId string = ''

@description('Resource ID of the VNet to link private DNS zones to. Required when enablePrivateEndpoints is true.')
param privateEndpointVnetId string = ''

resource cognitiveAccount 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: 'ai-${baseName}-${environment}'
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: 'ai-${baseName}-${environment}'
    // Security: disable public access when private endpoints are enabled.
    // This ensures all traffic flows through the private link.
    publicNetworkAccess: enablePrivateEndpoints ? 'Disabled' : 'Enabled'
    disableLocalAuth: true
  }
}

resource gpt4oDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: cognitiveAccount
  name: 'gpt-4o'
  sku: {
    name: 'Standard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-08-06'
    }
  }
}

// Grant the app MI "Cognitive Services OpenAI User" so it can call the model via Entra auth
resource openAiUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(cognitiveAccount.id, managedIdentityPrincipalId, '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
  scope: cognitiveAccount
  properties: {
    principalId: managedIdentityPrincipalId
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
    )
    principalType: 'ServicePrincipal'
  }
}

output endpoint string = cognitiveAccount.properties.endpoint
output accountName string = cognitiveAccount.name

// --- Private endpoint resources (deployed only when enablePrivateEndpoints is true) ---

// Private DNS zone for Azure Cognitive Services / OpenAI
resource aiDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = if (enablePrivateEndpoints) {
  name: 'privatelink.openai.azure.com'
  location: 'global'
  tags: tags
}

// Link DNS zone to the shared VNet so private endpoint IPs resolve correctly
resource aiDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = if (enablePrivateEndpoints) {
  parent: aiDnsZone
  name: '${cognitiveAccount.name}-dns-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: privateEndpointVnetId }
  }
}

// Private endpoint for AI Foundry (Cognitive Services / OpenAI)
resource aiPrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-11-01' = if (enablePrivateEndpoints) {
  name: '${cognitiveAccount.name}-pe'
  location: location
  tags: tags
  properties: {
    subnet: { id: privateEndpointSubnetId }
    privateLinkServiceConnections: [
      {
        name: 'openai'
        properties: {
          privateLinkServiceId: cognitiveAccount.id
          groupIds: ['account']
        }
      }
    ]
  }
}

// DNS zone group — automatically registers the PE's private IP in the DNS zone
resource aiPeDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = if (enablePrivateEndpoints) {
  parent: aiPrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'openai'
        properties: { privateDnsZoneId: aiDnsZone.id }
      }
    ]
  }
}
