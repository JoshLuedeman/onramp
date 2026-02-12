using '../main.bicep'

param environment = 'dev'
param location = 'eastus2'
param baseName = 'onramp'
param sqlAdminLogin = 'onrampadmin'
param sqlAdminPassword = '' // Set via deployment parameter
