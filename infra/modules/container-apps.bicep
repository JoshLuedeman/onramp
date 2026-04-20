@description('Azure region')
param location string

@description('Base name')
param baseName string

@description('Environment')
param environment string

@description('Log Analytics workspace name')
param logAnalyticsName string

@description('Key Vault name for secret references')
param keyVaultName string

@description('Application Insights connection string')
param appInsightsConnectionString string

@description('AI Foundry endpoint URL')
param aiFoundryEndpoint string

@description('Azure AD tenant ID')
param azureTenantId string = ''

@description('Azure AD client ID')
param azureClientId string = ''

@description('Whether client secret is configured in Key Vault')
param hasClientSecret bool = false

@description('Container registry server')
param containerRegistryServer string = ''

@description('Frontend container image')
param frontendImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Backend container image')
param backendImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Resource ID of the user-assigned managed identity')
param managedIdentityId string

@description('Principal (object) ID of the user-assigned managed identity')
param managedIdentityPrincipalId string

@description('Client (application) ID of the user-assigned managed identity')
param managedIdentityClientId string

@description('SQL Server FQDN for the database connection string')
param sqlServerFqdn string

@description('SQL database name')
param sqlDatabaseName string

@description('Resource tags')
param tags object

var envName = 'cae-${baseName}-${environment}'
var isProd = environment == 'prod'

// Build backend secrets array conditionally — only reference KV secrets that exist
var clientSecretKv = hasClientSecret
  ? [
      {
        name: 'client-secret'
        keyVaultUrl: '${keyVault.properties.vaultUri}secrets/client-secret'
        identity: managedIdentityId
      }
    ]
  : []

// Credential-free connection string — Entra token auth is handled by the backend
var databaseUrl = 'mssql+aioodbc://@${sqlServerFqdn}/${sqlDatabaseName}?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no'

// Build backend env vars conditionally
var baseEnvVars = [
  { name: 'ONRAMP_DATABASE_URL', value: databaseUrl }
  { name: 'ONRAMP_MANAGED_IDENTITY_CLIENT_ID', value: managedIdentityClientId }
  { name: 'ONRAMP_AI_FOUNDRY_ENDPOINT', value: aiFoundryEndpoint }
  { name: 'ONRAMP_AI_FOUNDRY_MODEL', value: 'gpt-4o' }
  { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
  {
    name: 'ONRAMP_CORS_ORIGINS'
    value: '["https://${frontendApp.properties.configuration.ingress.fqdn}"]'
  }
]
var tenantEnvVars = !empty(azureTenantId)
  ? [
      { name: 'ONRAMP_AZURE_TENANT_ID', value: azureTenantId }
    ]
  : []
var clientIdEnvVars = !empty(azureClientId)
  ? [
      { name: 'ONRAMP_AZURE_CLIENT_ID', value: azureClientId }
    ]
  : []
var clientSecretEnvVars = hasClientSecret
  ? [
      { name: 'ONRAMP_AZURE_CLIENT_SECRET', secretRef: 'client-secret' }
    ]
  : []
var backendEnvVars = concat(
  baseEnvVars,
  tenantEnvVars,
  clientIdEnvVars,
  clientSecretEnvVars
)

var allBackendSecrets = clientSecretKv

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: logAnalyticsName
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

// Key Vault Secrets User role assignment (role ID: 4633458b-17de-408a-b874-0445c86b69e6)
resource kvRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, managedIdentityId, '4633458b-17de-408a-b874-0445c86b69e6')
  scope: keyVault
  properties: {
    principalId: managedIdentityPrincipalId
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '4633458b-17de-408a-b874-0445c86b69e6'
    )
    principalType: 'ServicePrincipal'
  }
}

resource containerAppsEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: envName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'azure-monitor'
    }
  }
}

// Route container app logs to Log Analytics via diagnostic settings (Entra auth, no shared key)
resource envDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'logAnalytics'
  scope: containerAppsEnv
  properties: {
    workspaceId: logAnalytics.id
    logs: [
      { category: 'ContainerAppConsoleLogs', enabled: true }
      { category: 'ContainerAppSystemLogs', enabled: true }
    ]
  }
}

resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-${baseName}-frontend-${environment}'
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8080
        transport: 'http'
      }
      registries: !empty(containerRegistryServer)
        ? [
            {
              server: containerRegistryServer
              identity: managedIdentityId
            }
          ]
        : []
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: frontendImage
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            { name: 'BACKEND_URL', value: 'ca-${baseName}-backend-${environment}:8000' }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/'
                port: 8080
              }
              periodSeconds: 30
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/'
                port: 8080
              }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: isProd ? 1 : 0
        maxReplicas: isProd ? 5 : 3
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

resource backendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-${baseName}-backend-${environment}'
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: false
        targetPort: 8000
        transport: 'http'
      }
      secrets: allBackendSecrets
      registries: !empty(containerRegistryServer)
        ? [
            {
              server: containerRegistryServer
              identity: managedIdentityId
            }
          ]
        : []
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: backendImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: backendEnvVars
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              periodSeconds: 30
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 10
              periodSeconds: 10
            }
            {
              type: 'Startup'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 5
              periodSeconds: 5
              failureThreshold: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: isProd ? 1 : 0
        maxReplicas: isProd ? 10 : 5
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '20'
              }
            }
          }
        ]
      }
    }
  }
}

output environmentId string = containerAppsEnv.id
output frontendFqdn string = frontendApp.properties.configuration.ingress.fqdn
output backendFqdn string = backendApp.properties.configuration.ingress.fqdn
