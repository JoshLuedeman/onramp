using '../main.bicep'

// Development environment parameters
// Deploy: az deployment sub create -l eastus2 -f infra/main.bicep -p infra/parameters/dev.bicepparam \
//         -p sqlAdminPassword=<value>
// Secrets are passed as deployment parameters (never stored in this file).

param environment = 'dev'
param location = 'eastus2'
param baseName = 'onramp'
param sqlAdminLogin = 'onrampadmin'

// Required — pass at deployment time:
//   -p sqlAdminPassword=<value>
//   -p aiFoundryKey=<value>      (optional for dev — mock AI used when empty)
//   -p clientSecret=<value>      (optional for dev — mock auth used when empty)
