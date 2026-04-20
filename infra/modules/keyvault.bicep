@description('Azure region')
param location string

@description('Base name')
param baseName string

@description('Environment')
param environment string

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
