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

@description('SQL Server FQDN')
param sqlServerFqdn string

@description('SQL Database name')
param sqlDatabaseName string

@description('AI Foundry endpoint URL')
param aiFoundryEndpoint string

@description('Container registry server')
param containerRegistryServer string = ''

@description('Frontend container image')
param frontendImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Backend container image')
param backendImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Resource tags')
param tags object

var envName = 'cae-${baseName}-${environment}'

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: logAnalyticsName
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

// Managed identity for Key Vault access
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${baseName}-${environment}'
  location: location
  tags: tags
}

// Key Vault Secrets User role assignment (role ID: 4633458b-17de-408a-b874-0445c86b69e6)
resource kvRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, managedIdentity.id, '4633458b-17de-408a-b874-0445c86b69e6')
  scope: keyVault
  properties: {
    principalId: managedIdentity.properties.principalId
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
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'ca-${baseName}-frontend-${environment}'
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8080
        transport: 'http'
        corsPolicy: {
          allowedOrigins: ['*']
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
        }
      }
      registries: !empty(containerRegistryServer)
        ? [
            {
              server: containerRegistryServer
              identity: managedIdentity.id
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
        minReplicas: environment == 'prod' ? 1 : 0
        maxReplicas: environment == 'prod' ? 5 : 3
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
      '${managedIdentity.id}': {}
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
      secrets: [
        {
          name: 'sql-admin-password'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/sql-admin-password'
          identity: managedIdentity.id
        }
        {
          name: 'ai-foundry-key'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/ai-foundry-key'
          identity: managedIdentity.id
        }
        {
          name: 'client-secret'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/client-secret'
          identity: managedIdentity.id
        }
      ]
      registries: !empty(containerRegistryServer)
        ? [
            {
              server: containerRegistryServer
              identity: managedIdentity.id
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
          env: [
            {
              name: 'ONRAMP_DATABASE_URL'
              value: 'mssql+aioodbc://onrampadmin@${sqlServerFqdn}/${sqlDatabaseName}?driver=ODBC+Driver+18+for+SQL+Server'
            }
            { name: 'ONRAMP_AI_FOUNDRY_ENDPOINT', value: aiFoundryEndpoint }
            { name: 'ONRAMP_AI_FOUNDRY_KEY', secretRef: 'ai-foundry-key' }
            { name: 'ONRAMP_AZURE_CLIENT_SECRET', secretRef: 'client-secret' }
            { name: 'ONRAMP_AI_FOUNDRY_MODEL', value: 'gpt-4o' }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
            {
              name: 'ONRAMP_CORS_ORIGINS'
              value: '["https://${frontendApp.properties.configuration.ingress.fqdn}"]'
            }
          ]
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
        minReplicas: environment == 'prod' ? 1 : 0
        maxReplicas: environment == 'prod' ? 10 : 5
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
output managedIdentityPrincipalId string = managedIdentity.properties.principalId
