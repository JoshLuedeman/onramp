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

// VNet for deployment script — isolates script storage via private endpoints.
// Only used during deployment; does not affect runtime Container Apps (which remain public).
resource scriptVnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: 'vnet-${baseName}-script-${environment}'
  location: location
  tags: tags
  properties: {
    addressSpace: { addressPrefixes: ['10.0.0.0/16'] }
    subnets: [
      {
        name: 'aci-subnet'
        properties: {
          addressPrefix: '10.0.0.0/24'
          delegations: [
            {
              name: 'aci-delegation'
              properties: { serviceName: 'Microsoft.ContainerInstance/containerGroups' }
            }
          ]
        }
      }
      {
        name: 'pe-subnet'
        properties: {
          addressPrefix: '10.0.1.0/24'
        }
      }
    ]
  }
}

// Keyless storage account for deployment script — no shared key access allowed.
var scriptStorageName = 'stds${uniqueString(resourceGroup().id, baseName, environment)}'

resource scriptStorage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: scriptStorageName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    allowSharedKeyAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'None'
    }
  }
}

// Private DNS zone for file storage
resource fileDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.file.${az.environment().suffixes.storage}'
  location: 'global'
  tags: tags
}

// Link DNS zone to VNet
resource fileDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: fileDnsZone
  name: '${scriptVnet.name}-file-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: scriptVnet.id }
  }
}

// Private endpoint for file storage — placed in pe-subnet (no ACI delegation)
resource filePe 'Microsoft.Network/privateEndpoints@2023-11-01' = {
  name: '${scriptStorageName}-file-pe'
  location: location
  tags: tags
  properties: {
    subnet: { id: scriptVnet.properties.subnets[1].id }
    privateLinkServiceConnections: [
      {
        name: 'file'
        properties: {
          privateLinkServiceId: scriptStorage.id
          groupIds: ['file']
        }
      }
    ]
  }
}

resource filePeDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = {
  parent: filePe
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'file'
        properties: { privateDnsZoneId: fileDnsZone.id }
      }
    ]
  }
}

// Storage File Data Privileged Contributor for bootstrap MI — enables keyless deployment script storage
resource scriptStoragePrivContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(scriptStorage.id, bootstrapIdentity.id, '69566ab7-960f-475b-8e7c-b3118f30c6bd')
  scope: scriptStorage
  properties: {
    principalId: bootstrapIdentity.properties.principalId
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '69566ab7-960f-475b-8e7c-b3118f30c6bd' // Storage File Data Privileged Contributor
    )
    principalType: 'ServicePrincipal'
  }
}

// Deployment script: create contained database user for the app identity, then
// hand SQL admin over to the Entra group. Uses SID-based user creation to avoid
// needing Directory Readers on the SQL server.
// Runs in a VNet-isolated container with keyless storage — no shared key access.
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
  dependsOn: [
    sqlDatabase
    firewallAllowAzure
    bootstrapContributor
    scriptStoragePrivContributor
    filePeDnsGroup
    fileDnsLink
  ]
  properties: {
    azCliVersion: '2.60.0'
    retentionInterval: 'P1D'
    timeout: 'PT15M'
    storageAccountSettings: {
      storageAccountName: scriptStorage.name
    }
    containerSettings: {
      subnetIds: [
        { id: scriptVnet.properties.subnets[0].id }
      ]
    }
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
