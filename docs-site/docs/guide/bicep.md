# Bicep Templates

OnRamp auto-generates Bicep templates (Infrastructure as Code) from your architecture design, ready for deployment to Azure.

## Auto-Generated IaC

After your architecture is finalized and compliance-scored, OnRamp generates Bicep templates that implement:

- Management group hierarchy
- Subscription placement
- Resource group structure
- Networking (VNets, subnets, peering, firewalls)
- Identity and RBAC assignments
- Azure Policy assignments
- Monitoring and diagnostics configuration

## Template Library

OnRamp includes a library of pre-built Bicep modules for common Azure resources. These modules follow Microsoft best practices and are used as building blocks for the generated templates.

You can browse available templates via the API:

| Method | Path                          | Description              |
| ------ | ----------------------------- | ------------------------ |
| GET    | `/api/bicep/templates`        | List Bicep templates     |
| GET    | `/api/bicep/templates/{name}` | Preview a template       |

## Generate and Download

The full generation and download workflow:

1. **Generate** — Create Bicep templates from your architecture
2. **Preview** — Review the generated code in the UI
3. **Download** — Download as a ZIP archive for local use or manual deployment

| Method | Path                    | Description                      |
| ------ | ----------------------- | -------------------------------- |
| POST   | `/api/bicep/generate`   | Generate Bicep from architecture |
| POST   | `/api/bicep/download`   | Download generated Bicep         |

## Customization

The downloaded Bicep templates are fully customizable. You can:

- Modify parameters for your environment
- Add additional resources or modules
- Integrate with your existing CI/CD pipelines
- Version control the templates in your own repository

See the [Bicep API Reference](/api/bicep) for full endpoint details.

## Next Steps

- [Deployment](./deployment) — Deploy your Bicep templates directly from OnRamp
- [API Reference](/api/) — Full API documentation
