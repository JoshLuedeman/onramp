# Deployment

OnRamp can deploy your generated Bicep templates directly to Azure subscriptions with real-time tracking and rollback support.

## Pre-Deployment Validation

Before any deployment begins, OnRamp validates:

- **Subscription access** — Confirms you have the required permissions
- **Resource quotas** — Checks that your subscription has capacity for the planned resources
- **Policy compliance** — Ensures the deployment won't violate existing Azure policies
- **Naming conflicts** — Verifies resource names are available

## Step-by-Step Deployment

The deployment process follows these steps:

1. **Validate** — Pre-deployment checks (see above)
2. **Create plan** — Generate a deployment plan showing what will be created
3. **Review** — Preview all resources and changes before committing
4. **Deploy** — Execute the Bicep deployment against your Azure subscription
5. **Monitor** — Track real-time progress of each resource deployment

## Rollback Support

If a deployment fails or needs to be reverted:

- OnRamp tracks the state of each deployed resource
- You can initiate a rollback to undo changes
- The rollback process removes resources created during the failed deployment
- An audit trail records all rollback actions

## Audit Logging

Every deployment action is logged for compliance and troubleshooting:

- Who initiated the deployment
- What resources were created, modified, or deleted
- When each action occurred
- The outcome (success/failure) of each step

## API Endpoints

| Method | Path                              | Description             |
| ------ | --------------------------------- | ----------------------- |
| POST   | `/api/deployment/validate`        | Validate subscription   |
| POST   | `/api/deployment/create`          | Create deployment plan  |
| POST   | `/api/deployment/{id}/start`      | Start deployment        |
| GET    | `/api/deployment/{id}`            | Get deployment status   |
| POST   | `/api/deployment/{id}/rollback`   | Rollback deployment     |
| GET    | `/api/deployment/{id}/audit`      | Get audit log           |
| GET    | `/api/deployment/`                | List deployments        |

See the [Deployment API Reference](/api/deployment) for full details.

## Next Steps

- [API Reference](/api/) — Full API documentation
- [Development Guide](/development/) — Set up a local development environment
