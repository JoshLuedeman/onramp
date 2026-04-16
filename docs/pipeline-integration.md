# Pipeline Integration Guide

OnRamp generates CI/CD pipeline definitions for deploying Azure Landing Zones. This guide
covers how to integrate the generated pipelines into your repository and configure the
required cloud credentials, environments, and approval gates.

## Supported Formats

OnRamp produces pipelines for two CI/CD platforms, each targeting four IaC formats:

| Pipeline Platform | IaC Formats | Generated Files |
|-------------------|-------------|-----------------|
| GitHub Actions | Bicep, Terraform, ARM, Pulumi | `.github/workflows/deploy-{iac}.yml`, `validate.yml`, `env-{env}.yml` |
| Azure DevOps | Bicep, Terraform, ARM, Pulumi | `azure-pipelines.yml`, `pipelines/variables.{env}.yml`, `pipelines/README.md` |

Query available formats programmatically:

```bash
curl https://<onramp-host>/api/pipelines/formats
```

```json
{
  "pipeline_formats": ["github_actions", "azure_devops"],
  "iac_formats": ["bicep", "terraform", "arm", "pulumi"]
}
```

## GitHub Actions Setup

Generated workflows use **workload identity federation (OIDC)** to authenticate with Azure.
No long-lived secrets are stored in the repository.

### Prerequisites

1. An Azure AD app registration with federated credentials for your GitHub repository.
2. A resource group or subscription-level RBAC assignment granting the app `Contributor`
   (or a custom role) on the target scope.

### Required Secrets

Add three repository secrets under **Settings → Secrets and variables → Actions**:

| Secret | Description |
|--------|-------------|
| `AZURE_CLIENT_ID` | Application (client) ID of the app registration |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Target subscription ID |

For Pulumi pipelines, also add:

| Secret | Description |
|--------|-------------|
| `PULUMI_ACCESS_TOKEN` | Token from [app.pulumi.com](https://app.pulumi.com) for state management |

### OIDC Authentication

Every job begins with an Azure login step that requests an OIDC token:

```yaml
- name: Azure Login (OIDC)
  uses: azure/login@v2
  with:
    client-id: ${{ secrets.AZURE_CLIENT_ID }}
    tenant-id: ${{ secrets.AZURE_TENANT_ID }}
    subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
```

The workflow declares `id-token: write` and `contents: read` permissions to enable this.

### Environment Protection Rules

Each job targets a GitHub environment (`dev`, `staging`, `prod`). Configure protection rules
under **Settings → Environments**:

- **dev** — No protection (deploys on every push to `main`).
- **staging** — Require reviewer approval before deployment.
- **prod** — Require reviewer approval plus a deployment branch rule limiting to `main`.

Jobs chain via `needs` so that `deploy-staging` waits for `deploy-dev`, and `deploy-prod`
waits for `deploy-staging`:

```yaml
deploy-prod:
  needs: deploy-staging
  environment: prod
  runs-on: ubuntu-latest
```

### Workflow Structure

The generator produces three file types:

**`deploy-{iac}.yml`** — Main deployment workflow with one job per environment.

```text
Trigger: push/PR to main (paths: infra/{iac}/**) + workflow_dispatch
┌─────────────┐     ┌──────────────────┐     ┌───────────────┐
│  deploy-dev  │ ──▶ │  deploy-staging  │ ──▶ │  deploy-prod  │
└─────────────┘     └──────────────────┘     └───────────────┘
```

Each job runs: **checkout → Azure login → validate → plan/what-if → deploy** (deploy
runs only on `main`, not on pull requests).

**`validate.yml`** — Reusable PR validation workflow that lints and validates templates
without deploying.

**`env-{env}.yml`** — Per-environment parameter files with region, project name, CIDR
ranges, and tags:

```yaml
environment: staging
location: eastus2
project_name: onramp-landing-zone
resource_prefix: onramp-landing-zone-staging
tags:
  environment: staging
  managed_by: onramp
  project: onramp-landing-zone
```

## Azure DevOps Setup

Generated pipelines authenticate using **service connections** and manage secrets through
**variable groups**.

### Prerequisites

1. An Azure DevOps project with Pipelines enabled.
2. An Azure Resource Manager service connection (workload identity federation recommended).
3. A variable group containing subscription and tenant IDs.

### Service Connection

Create a service connection under **Project Settings → Service connections → Azure Resource
Manager**. The generated pipeline references it by name (default: `azure-service-connection`):

```yaml
variables:
  - group: landing-zone-secrets
  - name: azureServiceConnection
    value: azure-service-connection
```

Override the default name when generating:

```json
{
  "pipeline_format": "azure_devops",
  "iac_format": "terraform",
  "service_connection": "my-azure-connection",
  "variable_group": "my-secrets"
}
```

### Variable Groups

Create a variable group in **Pipelines → Library** named `landing-zone-secrets` (or your
custom name) with these variables:

| Variable | Description |
|----------|-------------|
| `ARM_SUBSCRIPTION_ID` | Target Azure subscription ID |
| `ARM_TENANT_ID` | Azure AD tenant ID |
| `PULUMI_ACCESS_TOKEN` | Pulumi state token (Pulumi pipelines only) |

### Environment Approval Gates

The generated pipeline uses Azure DevOps environments for deployment targets:

- `landing-zone-dev` — Auto-deploys after the Build stage succeeds.
- `landing-zone-prod` — Deploys only from `main` branch. Configure approval checks under
  **Pipelines → Environments → landing-zone-prod → Approvals and checks**.

### Pipeline Structure

```text
┌──────────────────────┐
│  Build & Validate    │
└──────────┬───────────┘
           │
     ┌─────▼──────┐
     │ Deploy Dev  │
     └─────┬──────┘
           │ (main branch only)
     ┌─────▼──────┐
     │ Deploy Prod │
     └────────────┘
```

**Build stage** — Validates and lints IaC templates. For Terraform, this includes
`init`, `validate`, and `plan`. For Bicep and ARM, it runs `az deployment sub validate`.

**Deploy stages** — One per environment. Each uses a `runOnce` deployment strategy with
the `deploy` lifecycle hook. Production requires the source branch to be `main`:

```yaml
- stage: Deploy_prod
  dependsOn: Deploy_dev
  condition: >-
    and(succeeded(),
        eq(variables['Build.SourceBranch'], 'refs/heads/main'))
```

## IaC Format-Specific Notes

### Bicep

**Prerequisites:** Azure CLI with Bicep extension (bundled in `ubuntu-latest` runners).

**Pipeline behavior:**
1. **Validate** — `az bicep build --file infra/bicep/main.bicep`
2. **What-if** — `az deployment sub what-if` shows planned changes
3. **Deploy** — `az deployment sub create` at subscription scope

**State management:** None required. Bicep deployments are idempotent and Azure tracks
deployment state natively.

**File structure assumed:**

```text
infra/bicep/
├── main.bicep
└── parameters/
    ├── dev.bicepparam
    ├── staging.bicepparam
    └── prod.bicepparam
```

### Terraform

**Prerequisites:** Terraform CLI (GitHub Actions uses `hashicorp/setup-terraform@v3`
with version `1.5.0`; Azure DevOps uses `TerraformInstaller@1` with `1.7.0`).

**Pipeline behavior:**
1. **Init** — Configures the backend. GitHub Actions sets `ARM_USE_OIDC: true` for
   OIDC-based authentication. Azure DevOps uses the service connection.
2. **Plan** — Generates `{env}.tfplan` for review.
3. **Apply** — Executes the plan (skipped on pull requests).

**State management:** Terraform requires a remote backend. Azure DevOps pipelines
configure an Azure Storage backend automatically:

```yaml
backendAzureRmResourceGroupName: rg-terraform-state
backendAzureRmStorageAccountName: stterraformstate
backendAzureRmContainerName: tfstate
backendAzureRmKey: landing-zone-{env}.tfstate
```

For GitHub Actions, configure the backend in your `main.tf`:

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "stterraformstate"
    container_name       = "tfstate"
    key                  = "landing-zone.tfstate"
    use_oidc             = true
  }
}
```

Each environment uses a separate state file key to isolate state.

### ARM

**Prerequisites:** Azure CLI (bundled in `ubuntu-latest` runners).

**Pipeline behavior:**
1. **Validate** — `az deployment sub validate` (GitHub Actions) or
   `AzureResourceManagerTemplateDeployment@3` in validation mode (Azure DevOps).
2. **What-if** — Shows planned resource changes.
3. **Deploy** — `az deployment sub create` with `Incremental` deployment mode.

**State management:** None required. ARM deployments are idempotent.

**File structure assumed:**

```text
infra/
├── azuredeploy.json
├── azuredeploy.parameters.json
├── azuredeploy.parameters.dev.json
└── azuredeploy.parameters.prod.json
```

### Pulumi

**Prerequisites:** Node.js 20+, Pulumi CLI, a Pulumi access token for state management.

**Pipeline behavior:**
1. **Install** — Sets up Node.js and Pulumi CLI, runs `npm ci` in `infra/pulumi`.
2. **Preview** — `pulumi preview` shows planned changes against the target stack.
3. **Up** — `pulumi up --yes` applies changes (skipped on pull requests).

**State management:** Pulumi stores state in the Pulumi Cloud service by default.
Each environment maps to a stack (e.g., `onramp-landing-zone-dev`,
`onramp-landing-zone-prod`). Store `PULUMI_ACCESS_TOKEN` as a secret in your CI system.

**File structure assumed:**

```text
infra/pulumi/
├── package.json
├── Pulumi.yaml
├── Pulumi.dev.yaml
├── Pulumi.prod.yaml
└── index.ts
```

## Version Pinning

OnRamp pins provider and API versions to ensure reproducible deployments. The version
registry is queryable via the `/api/versions/*` endpoints:

| Endpoint | Returns |
|----------|---------|
| `GET /api/versions/terraform` | Recommended Terraform CLI and provider versions |
| `GET /api/versions/bicep` | Recommended Bicep API versions per resource type |
| `GET /api/versions/arm` | ARM template schema and API versions per resource type |
| `GET /api/versions/pulumi/{language}` | Pulumi SDK package versions (`typescript` or `python`) |
| `GET /api/versions/report` | Full freshness report across all formats |

Example — query Terraform versions:

```bash
curl https://<onramp-host>/api/versions/terraform
```

```json
{
  "terraform_version": "1.5.0",
  "providers": {
    "azurerm": "3.85.0",
    "azuread": "2.47.0"
  }
}
```

The freshness report flags versions older than a configurable threshold:

```bash
curl "https://<onramp-host>/api/versions/report?threshold_days=90"
```

Generated IaC templates embed these pinned versions so deployments are deterministic.
Update the version registry and regenerate templates when upgrading provider versions.

## Troubleshooting

### GitHub Actions

| Symptom | Cause | Fix |
|---------|-------|-----|
| `OIDC: No subject claim found` | Missing `id-token: write` permission | Ensure the workflow has `permissions: { id-token: write, contents: read }` |
| `AADSTS700016: Application not found` | Wrong `AZURE_CLIENT_ID` | Verify the app registration client ID in repository secrets |
| `Federated credential not found` | Repo/branch mismatch | Check the federated credential subject matches `repo:<owner>/<repo>:ref:refs/heads/main` |
| Deployment skipped on PR | Expected behavior | Deployments only run on pushes to `main`; PRs run validation only |
| `terraform init` fails with backend error | Missing storage account | Create the Terraform state storage account and container before first run |

### Azure DevOps

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Service connection not found` | Name mismatch | Verify `azureServiceConnection` variable matches the service connection name exactly |
| `Variable group not found` | Missing library entry | Create the variable group in **Pipelines → Library** with the expected name |
| `Environment not found` | First run | Azure DevOps creates environments on first pipeline execution; configure approvals after |
| Prod stage skipped | Not on `main` branch | Prod deploys require `Build.SourceBranch` to be `refs/heads/main` |
| Terraform state lock conflict | Concurrent runs | Enable pipeline queuing or use `terraform force-unlock` (with caution) |

### General

| Symptom | Cause | Fix |
|---------|-------|-----|
| `az bicep build` fails | Outdated Azure CLI | Update Azure CLI: `az upgrade` (runners update monthly) |
| Pulumi stack not found | Stack not initialized | Run `pulumi stack init <project>-<env>` before first pipeline execution |
| Parameter file not found | Wrong file structure | Ensure your IaC files match the expected directory layout for your format |

## API Reference

Quick reference to pipeline-related endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/pipelines/formats` | List supported pipeline and IaC formats |
| `GET` | `/api/pipelines/templates` | List available pipeline templates |
| `POST` | `/api/pipelines/generate` | Generate pipeline files from an architecture |
| `POST` | `/api/pipelines/download` | Download generated pipeline files as a ZIP archive |

### Generate Request

```json
{
  "architecture": { "...": "architecture definition JSON" },
  "iac_format": "terraform",
  "pipeline_format": "github_actions",
  "environments": ["dev", "staging", "prod"],
  "include_approval_gates": true,
  "project_name": "onramp-landing-zone",
  "service_connection": "azure-service-connection",
  "variable_group": "landing-zone-secrets"
}
```

- `iac_format` — Required. One of: `bicep`, `terraform`, `arm`, `pulumi`.
- `pipeline_format` — Default: `github_actions`. Also accepts `azure_devops`.
- `environments` — Default: `["dev", "staging", "prod"]`.
- `include_approval_gates` — Default: `true`. Chains jobs/stages sequentially.
- `service_connection` / `variable_group` — Azure DevOps only.

### Generate Response

```json
{
  "files": [
    {
      "name": "deploy-terraform.yml",
      "content": "...",
      "size_bytes": 4218,
      "environment": "all"
    }
  ],
  "total_files": 5,
  "iac_format": "terraform",
  "pipeline_format": "github_actions",
  "environments": ["dev", "staging", "prod"]
}
```

### Download

`POST /api/pipelines/download` accepts the same request body and returns a ZIP file.
GitHub Actions files are placed under `.github/workflows/`; Azure DevOps files are at the
archive root.
