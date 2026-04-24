targetScope = 'resourceGroup'

// ---------------------------------------------------------------------------
// Network Watcher & NSG Flow Logs
// Enables Network Watcher in the target region and configures NSG flow logs
// that are stored in a Storage Account and optionally forwarded to a Log
// Analytics workspace for traffic analytics.
// ---------------------------------------------------------------------------

@description('Azure region')
param location string

@description('Environment name (e.g. dev, prod)')
param environment string

@description('Resource tags')
param tags object = {}

@description('Resource ID of the NSG to monitor with flow logs')
param nsgId string

@description('Resource ID of the Log Analytics workspace for Traffic Analytics (optional)')
param logAnalyticsWorkspaceId string = ''

@description('Retention period in days for flow log data')
@minValue(1)
@maxValue(365)
param retentionDays int = 30

// ---- Storage account for flow log data ----
var storageAccountName = take('stnw${uniqueString(resourceGroup().id, environment)}', 24)

resource flowLogStorage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
  }
}

// ---- Network Watcher ----
// Network Watcher is automatically created by Azure in most cases, but we
// declare it explicitly to ensure it exists and to own the lifecycle.
resource networkWatcher 'Microsoft.Network/networkWatchers@2024-01-01' = {
  name: 'nw-${environment}-${location}'
  location: location
  tags: tags
}

// ---- NSG Flow Logs ----
resource flowLog 'Microsoft.Network/networkWatchers/flowLogs@2024-01-01' = {
  parent: networkWatcher
  name: 'fl-${environment}'
  location: location
  tags: tags
  properties: {
    targetResourceId: nsgId
    storageId: flowLogStorage.id
    enabled: true
    format: {
      type: 'JSON'
      version: 2
    }
    retentionPolicy: {
      enabled: true
      days: retentionDays
    }
    flowAnalyticsConfiguration: !empty(logAnalyticsWorkspaceId)
      ? {
          networkWatcherFlowAnalyticsConfiguration: {
            enabled: true
            workspaceResourceId: logAnalyticsWorkspaceId
            trafficAnalyticsInterval: 10
          }
        }
      : {
          networkWatcherFlowAnalyticsConfiguration: {
            enabled: false
          }
        }
  }
}

// ---- Outputs ----

@description('Resource ID of the Network Watcher')
output networkWatcherId string = networkWatcher.id

@description('Resource ID of the NSG flow log')
output flowLogId string = flowLog.id

@description('Name of the storage account holding flow log data')
output flowLogStorageAccountName string = flowLogStorage.name
