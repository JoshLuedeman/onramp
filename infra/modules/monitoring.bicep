// ---------------------------------------------------------------------------
// Production-grade monitoring module
// Deploys Log Analytics, Application Insights, alert rules, and an action
// group for email notification.  Diagnostic settings for Container Apps, SQL,
// and Key Vault are created in their respective modules; this module owns the
// shared observability infrastructure.
// ---------------------------------------------------------------------------

@description('Azure region')
param location string

@description('Base name for resource naming')
param baseName string

@description('Environment name (dev | prod)')
param environment string

@description('Resource tags')
param tags object

@description('Email address for alert notifications. When empty, the action group is created but has no email receiver.')
param alertEmail string = ''

// ---- Naming helpers ----
var logAnalyticsName = 'log-${baseName}-${environment}'
var appInsightsName = 'appi-${baseName}-${environment}'
var actionGroupName = 'ag-${baseName}-${environment}'
var isProd = environment == 'prod'

// ---- Log Analytics workspace ----
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: isProd ? 90 : 30
  }
}

// ---- Application Insights (connected to Log Analytics) ----
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// ---- Action group for alert notifications ----
resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: actionGroupName
  location: 'global'
  tags: tags
  properties: {
    groupShortName: take('ag-${baseName}', 12) // short name max 12 chars
    enabled: true
    emailReceivers: !empty(alertEmail)
      ? [
          {
            name: 'PrimaryEmail'
            emailAddress: alertEmail
            useCommonAlertSchema: true
          }
        ]
      : []
  }
}

// ---- Alert rules ----
// Each alert targets the Application Insights resource via scopes and uses
// Kusto-based scheduled query rules or metric alerts.

// 1. CPU utilisation > 80 %  (metric alert on Container Apps environment — uses
//    a scheduled-query against performanceCounters as a portable approach)
resource cpuAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'alert-cpu-${baseName}-${environment}'
  location: 'global'
  tags: tags
  properties: {
    description: 'Fires when average CPU utilisation exceeds 80 % for 5 minutes'
    severity: 2
    enabled: isProd
    scopes: [appInsights.id]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'HighCpu'
          metricName: 'performanceCounters/processCpuPercentage'
          metricNamespace: 'microsoft.insights/components'
          operator: 'GreaterThan'
          threshold: 80
          timeAggregation: 'Average'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

// 2. Memory utilisation > 80 %
resource memoryAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'alert-memory-${baseName}-${environment}'
  location: 'global'
  tags: tags
  properties: {
    description: 'Fires when average memory utilisation exceeds 80 % for 5 minutes'
    severity: 2
    enabled: isProd
    scopes: [appInsights.id]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'HighMemory'
          metricName: 'performanceCounters/processPrivateBytes'
          metricNamespace: 'microsoft.insights/components'
          operator: 'GreaterThan'
          threshold: 858993459 // ~80 % of 1 GiB container
          timeAggregation: 'Average'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

// 3. HTTP 5xx errors > 10 per minute
resource http5xxAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: 'alert-http5xx-${baseName}-${environment}'
  location: location
  tags: tags
  properties: {
    description: 'Fires when HTTP 5xx responses exceed 10 per minute'
    severity: 1
    enabled: isProd
    scopes: [appInsights.id]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT1M'
    criteria: {
      allOf: [
        {
          query: 'requests | where resultCode startswith "5" | summarize count() by bin(timestamp, 1m)'
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 10
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: {
      actionGroups: [actionGroup.id]
    }
  }
}

// 4. Average response time > 5 seconds
resource responseTimeAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'alert-responsetime-${baseName}-${environment}'
  location: 'global'
  tags: tags
  properties: {
    description: 'Fires when average server response time exceeds 5 seconds for 5 minutes'
    severity: 2
    enabled: isProd
    scopes: [appInsights.id]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'SlowResponse'
          metricName: 'requests/duration'
          metricNamespace: 'microsoft.insights/components'
          operator: 'GreaterThan'
          threshold: 5000 // milliseconds
          timeAggregation: 'Average'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

// ---- Outputs ----

@description('Resource ID of the Log Analytics workspace')
output logAnalyticsId string = logAnalytics.id

@description('Name of the Log Analytics workspace')
output logAnalyticsName string = logAnalytics.name

@description('Application Insights connection string')
output appInsightsConnectionString string = appInsights.properties.ConnectionString

@description('Application Insights instrumentation key')
output appInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey

@description('Resource ID of the action group for alert notifications')
output actionGroupId string = actionGroup.id

@description('Resource ID of the Application Insights instance')
output appInsightsId string = appInsights.id
