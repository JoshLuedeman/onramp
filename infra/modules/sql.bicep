@description('Azure region')
param location string

@description('Base name')
param baseName string

@description('Environment')
param environment string

@description('Entra ID admin group display name')
param entraAdminGroupName string

@description('Entra ID admin group object ID')
param entraAdminGroupObjectId string

@description('Application managed identity display name')
param appIdentityName string

@description('Application managed identity client (application) ID')
param appIdentityClientId string

@description('Resource tags')
param tags object

var serverName = 'sql-${baseName}-${environment}'
var dbName = 'sqldb-${baseName}-${environment}'

// Bootstrap identity — used only during deployment to set up the database user.
// Kept separate from the app identity so the runtime app has least-privilege access.
resource bootstrapIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${baseName}-sqlbootstrap-${environment}'
  location: location
  tags: tags
}

// SQL Server with Entra-only authentication.
// The bootstrap identity is the initial admin so the deployment script can create
// the app identity's contained database user. After setup, admin is switched to
// the Entra group.
resource sqlServer 'Microsoft.Sql/servers@2023-08-01-preview' = {
  name: serverName
  location: location
  tags: tags
  properties: {
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    administrators: {
      administratorType: 'ActiveDirectory'
      azureADOnlyAuthentication: true
      login: bootstrapIdentity.name
      sid: bootstrapIdentity.properties.principalId
      tenantId: subscription().tenantId
      principalType: 'Application'
    }
  }
}

resource sqlDatabase 'Microsoft.Sql/servers/databases@2023-08-01-preview' = {
  parent: sqlServer
  name: dbName
  location: location
  tags: tags
  sku: {
    name: environment == 'prod' ? 'S1' : 'Basic'
    tier: environment == 'prod' ? 'Standard' : 'Basic'
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: environment == 'prod' ? 268435456000 : 2147483648
  }
}

resource firewallAllowAzure 'Microsoft.Sql/servers/firewallRules@2023-08-01-preview' = {
  parent: sqlServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// Grant the bootstrap identity Contributor on the SQL server so it can switch the
// admin to the Entra group after creating the app database user.
resource bootstrapContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(sqlServer.id, bootstrapIdentity.id, 'b24988ac-6180-42a0-ab88-20f7382dd24c')
  scope: sqlServer
  properties: {
    principalId: bootstrapIdentity.properties.principalId
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      'b24988ac-6180-42a0-ab88-20f7382dd24c' // Contributor
    )
    principalType: 'ServicePrincipal'
  }
}

// Deployment script: create contained database user for the app identity, then
// hand SQL admin over to the Entra group. Uses SID-based user creation to avoid
// needing Directory Readers on the SQL server.
resource setupEntraDbUser 'Microsoft.Resources/deploymentScripts@2023-08-01' = {
  name: 'setup-sql-entra-users-${environment}'
  location: location
  tags: tags
  kind: 'AzureCLI'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${bootstrapIdentity.id}': {}
    }
  }
  dependsOn: [sqlDatabase, firewallAllowAzure, bootstrapContributor]
  properties: {
    azCliVersion: '2.60.0'
    retentionInterval: 'P1D'
    timeout: 'PT15M'
    environmentVariables: [
      { name: 'SQL_SERVER_FQDN', value: sqlServer.properties.fullyQualifiedDomainName }
      { name: 'DATABASE_NAME', value: dbName }
      { name: 'SQL_SERVER_NAME', value: serverName }
      { name: 'RESOURCE_GROUP', value: resourceGroup().name }
      { name: 'APP_IDENTITY_NAME', value: appIdentityName }
      { name: 'APP_IDENTITY_CLIENT_ID', value: appIdentityClientId }
      { name: 'ADMIN_GROUP_NAME', value: entraAdminGroupName }
      { name: 'ADMIN_GROUP_OID', value: entraAdminGroupObjectId }
    ]
    scriptContent: loadTextContent('../scripts/setup-sql-entra-user.sh')
    cleanupPreference: 'OnSuccess'
  }
}

output serverFqdn string = sqlServer.properties.fullyQualifiedDomainName
output databaseName string = sqlDatabase.name
