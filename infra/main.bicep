targetScope = 'subscription'

@description('Environment name')
@allowed(['dev', 'prod'])
param environment string = 'dev'

@description('Azure region for resources')
param location string = 'eastus2'

@description('Base name for resources')
param baseName string = 'onramp'

@description('SQL administrator login')
@secure()
param sqlAdminLogin string

@description('SQL administrator password')
@secure()
param sqlAdminPassword string

@description('Azure AI Foundry API key')
@secure()
param aiFoundryKey string = ''

@description('Azure AD client secret')
@secure()
param clientSecret string = ''

@description('Azure AD tenant ID for authentication')
param azureTenantId string = ''

@description('Azure AD client ID for authentication')
param azureClientId string = ''

var resourceGroupName = 'rg-${baseName}-${environment}'
var tags = {
  application: 'OnRamp'
  environment: environment
  managedBy: 'bicep'
}

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

// Deployment order: monitoring first, then sql/ai-foundry in parallel, then keyvault, then container-apps

module monitoring 'modules/monitoring.bicep' = {
  scope: rg
  name: 'monitoring'
  params: {
    location: location
    baseName: baseName
    environment: environment
    tags: tags
  }
}

module sql 'modules/sql.bicep' = {
  scope: rg
  name: 'sql'
  dependsOn: [monitoring]
  params: {
    location: location
    baseName: baseName
    environment: environment
    sqlAdminLogin: sqlAdminLogin
    sqlAdminPassword: sqlAdminPassword
    tags: tags
  }
}

module keyVault 'modules/keyvault.bicep' = {
  scope: rg
  name: 'keyvault'
  params: {
    location: location
    baseName: baseName
    environment: environment
    sqlAdminPassword: sqlAdminPassword
    sqlAdminLogin: sqlAdminLogin
    sqlServerFqdn: sql.outputs.serverFqdn
    sqlDatabaseName: sql.outputs.databaseName
    aiFoundryKey: aiFoundryKey
    clientSecret: clientSecret
    tags: tags
  }
}

module aiFoundry 'modules/ai-foundry.bicep' = {
  scope: rg
  name: 'ai-foundry'
  dependsOn: [monitoring]
  params: {
    location: location
    baseName: baseName
    environment: environment
    tags: tags
  }
}

module containerApps 'modules/container-apps.bicep' = {
  scope: rg
  name: 'container-apps'
  params: {
    location: location
    baseName: baseName
    environment: environment
    logAnalyticsName: monitoring.outputs.logAnalyticsName
    keyVaultName: keyVault.outputs.vaultName
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    aiFoundryEndpoint: aiFoundry.outputs.endpoint
    azureTenantId: azureTenantId
    azureClientId: azureClientId
    hasAiFoundryKey: !empty(aiFoundryKey)
    hasClientSecret: !empty(clientSecret)
    tags: tags
  }
}

output resourceGroupName string = rg.name
output containerAppsEnvironmentId string = containerApps.outputs.environmentId
output sqlServerFqdn string = sql.outputs.serverFqdn
output keyVaultUri string = keyVault.outputs.vaultUri
