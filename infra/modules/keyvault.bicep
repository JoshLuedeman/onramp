@description('Azure region')
param location string

@description('Base name')
param baseName string

@description('Environment')
param environment string

@description('SQL admin password to store as secret')
@secure()
param sqlAdminPassword string = ''

@description('AI Foundry API key to store as secret')
@secure()
param aiFoundryKey string = ''

@description('Azure AD client secret to store as secret')
@secure()
param clientSecret string = ''

@description('Resource tags')
param tags object

var vaultName = 'kv-${baseName}-${environment}'

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: vaultName
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enablePurgeProtection: environment == 'prod'
  }
}

// Store secrets — only created when values are provided
resource sqlPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(sqlAdminPassword)) {
  parent: keyVault
  name: 'sql-admin-password'
  properties: {
    value: sqlAdminPassword
    contentType: 'text/plain'
  }
}

resource aiKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(aiFoundryKey)) {
  parent: keyVault
  name: 'ai-foundry-key'
  properties: {
    value: aiFoundryKey
    contentType: 'text/plain'
  }
}

resource clientSecretSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(clientSecret)) {
  parent: keyVault
  name: 'client-secret'
  properties: {
    value: clientSecret
    contentType: 'text/plain'
  }
}

output vaultUri string = keyVault.properties.vaultUri
output vaultName string = keyVault.name
output vaultId string = keyVault.id
