targetScope = 'subscription'

@description('Environment name')
@allowed(['dev', 'prod'])
param environment string = 'dev'

@description('Azure region for resources')
param location string = 'eastus2'

@description('Base name for resources')
param baseName string = 'onramp'

@description('Display name of the Entra ID group to set as SQL admin')
param sqlAdminGroupName string

@description('Object ID of the Entra ID group to set as SQL admin')
param sqlAdminGroupObjectId string

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

// User-assigned managed identity for the application — created at the top level
// so it can be referenced by both the SQL module (for DB user setup) and the
// Container Apps module (for runtime Key Vault / DB access).
module appIdentity 'modules/identity.bicep' = {
  scope: rg
  name: 'app-identity'
  params: {
    location: location
    baseName: baseName
    environment: environment
    tags: tags
  }
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
    entraAdminGroupName: sqlAdminGroupName
    entraAdminGroupObjectId: sqlAdminGroupObjectId
    appIdentityName: appIdentity.outputs.identityName
    appIdentityClientId: appIdentity.outputs.identityClientId
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
    managedIdentityId: appIdentity.outputs.identityResourceId
    managedIdentityPrincipalId: appIdentity.outputs.identityPrincipalId
    managedIdentityClientId: appIdentity.outputs.identityClientId
    sqlServerFqdn: sql.outputs.serverFqdn
    sqlDatabaseName: sql.outputs.databaseName
    tags: tags
  }
}

output resourceGroupName string = rg.name
output containerAppsEnvironmentId string = containerApps.outputs.environmentId
output sqlServerFqdn string = sql.outputs.serverFqdn
output keyVaultUri string = keyVault.outputs.vaultUri
