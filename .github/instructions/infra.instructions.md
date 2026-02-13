---
applyTo: "infra/**"
---

# Infrastructure Instructions (Bicep)

## Rules

- Use Bicep for all Azure resource definitions. Never use raw ARM JSON for new resources.
- All modules live in `infra/modules/` and are composed by `infra/main.bicep`.
- Use `@description` decorator on all parameters and outputs.
- Use `@secure()` decorator on all secret parameters.
- Never hardcode secrets in Bicep files. Use Key Vault references or secure parameters.

## Module Structure

```bicep
@description('The Azure region for deployment')
param location string = resourceGroup().location

@description('Environment name')
@allowed(['dev', 'staging', 'prod'])
param environment string

// Resources...

@description('The resource ID of the created resource')
output resourceId string = resource.id
```

## Naming Convention

- Resources: `{resourceType}-{appName}-{environment}` (e.g., `kv-onramp-prod`)
- Use the `uniqueString()` function for globally unique names.

## Parameter Files

- `dev.bicepparam` — Development environment values
- `prod.bicepparam` — Production environment values
- Never put secrets in parameter files. Use Key Vault references.

## Deployment Order (dependsOn)

networking → monitoring → sql → keyvault → ai-foundry → container-apps

## Distinction: OnRamp Infrastructure vs Customer Landing Zone Templates

- `infra/` = OnRamp's own Azure infrastructure (what hosts the app)
- `backend/app/templates/bicep/` = Customer landing zone templates (what the app generates for customers)
- Never mix these two concerns.

## Validation

- Run `az bicep build --file infra/main.bicep` to validate.
- CI validates Bicep on every push and PR.
