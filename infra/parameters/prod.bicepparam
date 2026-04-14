using '../main.bicep'

// Production environment parameters
// Deploy: az deployment sub create -l eastus2 -f infra/main.bicep -p infra/parameters/prod.bicepparam \
//         -p sqlAdminPassword=<value> -p aiFoundryKey=<value> -p clientSecret=<value>
// All secrets MUST be passed at deployment time — never store them in this file.
// For CI/CD, use pipeline secrets or Key Vault references.

param environment = 'prod'
param location = 'eastus2'
param baseName = 'onramp'
param sqlAdminLogin = 'onrampadmin'

// Required — pass at deployment time:
//   -p sqlAdminPassword=<value>    (SQL admin password)
//   -p aiFoundryKey=<value>        (Azure AI Foundry API key)
//   -p clientSecret=<value>        (Entra ID client secret)
