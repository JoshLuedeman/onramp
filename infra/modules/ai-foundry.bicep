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
    publicNetworkAccess: 'Enabled'
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
