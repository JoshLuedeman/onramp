using '../main.bicep'

// Development environment parameters
// Deploy: az deployment sub create -l eastus2 -f infra/main.bicep -p infra/parameters/dev.bicepparam \
//         -p sqlAdminGroupName=<value> -p sqlAdminGroupObjectId=<value>
// Secrets are passed as deployment parameters (never stored in this file).

param environment = 'dev'
param location = 'eastus2'
param baseName = 'onramp'

// Private endpoints disabled in dev for ease of local development and lower cost.
// Enable in prod via prod.bicepparam for network isolation.
param enablePrivateEndpoints = false

// Required — pass at deployment time:
//   -p sqlAdminGroupName=<value>       (Entra ID group display name for SQL admin)
//   -p sqlAdminGroupObjectId=<value>   (Entra ID group object ID for SQL admin)
//   -p aiFoundryKey=<value>            (optional for dev — mock AI used when empty)
//   -p clientSecret=<value>            (optional for dev — mock auth used when empty)
