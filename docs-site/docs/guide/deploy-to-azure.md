# Deploy to Azure

Deploy OnRamp to your Azure subscription using the Deploy to Azure button or manually via Bicep templates.

## One-Click Deploy

The fastest way to deploy OnRamp:

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FJoshLuedeman%2Fonramp%2Fmain%2Finfra%2Fazuredeploy.json)

This will:

1. Open the Azure Portal with a custom deployment template
2. Prompt you for required parameters (resource group, location, etc.)
3. Provision all required Azure resources
4. Deploy the OnRamp application

## Azure Resources Created

The deployment creates the following resources:

- **Azure Container Apps** — Hosts the frontend and backend containers
- **Azure SQL Database** — Persistent storage for projects, questionnaire answers, and deployments
- **Azure Key Vault** — Secrets management for API keys and connection strings
- **Azure AI Foundry** — LLM model hosting for architecture generation
- **Azure Monitor + Application Insights** — Observability and logging

## Prerequisites

- An Azure subscription with **Contributor** access
- Permission to create **App Registrations** in Microsoft Entra ID
- A resource group (or permission to create one)

## Environment Variables

Configure these after deployment:

| Variable                      | Description                    | Required   |
| ----------------------------- | ------------------------------ | ---------- |
| `ONRAMP_AZURE_TENANT_ID`     | Entra ID tenant                | Yes        |
| `ONRAMP_AZURE_CLIENT_ID`     | App registration client ID     | Yes        |
| `ONRAMP_AI_FOUNDRY_ENDPOINT` | Azure AI Foundry endpoint      | Yes        |
| `ONRAMP_AI_FOUNDRY_KEY`      | AI Foundry API key             | Yes        |
| `ONRAMP_DATABASE_URL`        | SQL connection string           | Yes        |
| `ONRAMP_CORS_ORIGINS`        | Allowed CORS origins            | Optional   |

## Manual Deployment

If you prefer to deploy manually using the Azure CLI:

```bash
az deployment group create \
  --resource-group <your-resource-group> \
  --template-file infra/azuredeploy.json \
  --parameters location=eastus
```

## Next Steps

- [Development Guide](/development/) — Set up a local development environment
- [Architecture Guide](./architecture) — How architecture generation works
