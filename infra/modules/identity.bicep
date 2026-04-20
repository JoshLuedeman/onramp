@description('Azure region')
param location string

@description('Base name')
param baseName string

@description('Environment')
param environment string

@description('Resource tags')
param tags object

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${baseName}-${environment}'
  location: location
  tags: tags
}

@description('Display name of the managed identity')
output identityName string = managedIdentity.name

@description('Resource ID of the managed identity')
output identityResourceId string = managedIdentity.id

@description('Principal (object) ID of the managed identity')
output identityPrincipalId string = managedIdentity.properties.principalId

@description('Client (application) ID of the managed identity')
output identityClientId string = managedIdentity.properties.clientId
