using '../main.bicep'

// Production environment parameters
// Deploy: az deployment sub create -l eastus2 -f infra/main.bicep -p infra/parameters/prod.bicepparam \
//         -p sqlAdminGroupName=<value> -p sqlAdminGroupObjectId=<value> \
//         -p aiFoundryKey=<value> -p clientSecret=<value>
// All secrets MUST be passed at deployment time — never store them in this file.
// For CI/CD, use pipeline secrets or Key Vault references.

param environment = 'prod'
param location = 'eastus2'
param baseName = 'onramp'

// Private endpoints enabled in prod — disables public network access on SQL Server
// and AI Foundry, routing all traffic through private links for network isolation.
param enablePrivateEndpoints = true

// Required — pass at deployment time:
//   -p sqlAdminGroupName=<value>       (Entra ID group display name for SQL admin)
//   -p sqlAdminGroupObjectId=<value>   (Entra ID group object ID for SQL admin)
//   -p aiFoundryKey=<value>            (Azure AI Foundry API key)
//   -p clientSecret=<value>            (Entra ID client secret)
