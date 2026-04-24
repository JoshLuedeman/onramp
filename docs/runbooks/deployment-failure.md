# Deployment Failure Runbook

## Symptoms and Detection

### How Failures Surface

| Signal | Source | Typical Delay |
|--------|--------|---------------|
| Deployment status stuck at `in_progress` | `GET /api/deployment/{id}` | Real-time |
| Health endpoint returns non-200 | `GET /health` | 30–60 s after deploy |
| Container App revision not receiving traffic | Azure Portal → Container Apps → Revisions | 1–5 min |
| CI/CD pipeline reports failure | GitHub Actions `deploy.yml` workflow | Real-time |
| Application Insights alerts fire | Azure Monitor alert rules | 1–5 min |

### Key Metrics to Watch

- **Revision provision status** — should transition to `Provisioned` within 5 minutes.
- **Health probe success rate** — must be 100 % before traffic shifts.
- **Error rate spike** in Application Insights after a new revision activates.

---

## Diagnosis Steps

### 1. Check the Deployment Record

```bash
# Via API (dev mode or with a valid token)
curl -s http://localhost:8000/api/deployment/{deployment_id} | jq .
```

Look at `status`, `error_message`, and `steps` to identify which stage failed.

### 2. Check Container Apps Logs

```bash
# Stream live logs for the backend container
az containerapp logs show \
  --name onramp-backend \
  --resource-group <rg-name> \
  --type console \
  --follow

# Query recent log entries
az containerapp logs show \
  --name onramp-backend \
  --resource-group <rg-name> \
  --type console \
  --tail 100
```

### 3. Check Health Endpoint

```bash
# Production
curl -sf https://<app-url>/health

# Expected response
# {"status": "healthy"}

# Dev mode returns extended info:
# {"status": "healthy", "service": "onramp-api", "mode": "development", ...}
```

If health returns an error or times out, the application did not start correctly.

### 4. Check Revision Status

```bash
az containerapp revision list \
  --name onramp-backend \
  --resource-group <rg-name> \
  --output table
```

Look for the latest revision's `provisioningState` and `healthState`.

### 5. Query Application Insights

```kql
// Exceptions in the last hour
exceptions
| where timestamp > ago(1h)
| order by timestamp desc
| project timestamp, problemId, outerMessage, innermostMessage

// Failed requests
requests
| where timestamp > ago(1h) and success == false
| summarize count() by resultCode, name
| order by count_ desc
```

---

## Common Failures and Resolutions

### Image Pull Failure

**Symptoms:** Revision stuck in `Provisioning`, logs show `ImagePullBackOff` or ACR authentication errors.

**Resolution:**
1. Verify the image tag exists in the container registry:
   ```bash
   az acr repository show-tags --name <acr-name> --repository onramp-backend
   ```
2. Confirm the Container App has a managed identity with `AcrPull` role on the registry:
   ```bash
   az role assignment list --scope /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.ContainerRegistry/registries/<acr> --output table
   ```
3. If using admin credentials, verify they are current in the Container App's registry configuration.

### Health Probe Failure

**Symptoms:** Revision provisions but never receives traffic. Azure Portal shows health probe failures.

**Resolution:**
1. Confirm the `/health` endpoint is accessible on port 8000 inside the container:
   ```bash
   az containerapp exec --name onramp-backend --resource-group <rg-name> --command "curl -s http://localhost:8000/health"
   ```
2. Check that the Container App ingress configuration targets port 8000.
3. Verify environment variables are set — missing `ONRAMP_DATABASE_URL` or `ONRAMP_AZURE_TENANT_ID` can cause startup failures that prevent the health endpoint from responding.

### Cold Start Timeout

**Symptoms:** First request after scaling from zero takes >30 s and times out.

**Resolution:**
1. Set minimum replicas to 1 to avoid cold starts:
   ```bash
   az containerapp update --name onramp-backend --resource-group <rg-name> --min-replicas 1
   ```
2. Increase the health probe `initialDelaySeconds` in the Bicep template to give the Python process time to start.
3. Review application startup logs — large database seed operations during `lifespan` can delay readiness.

### Database Connection Failure

**Symptoms:** Application starts but returns 500 errors. Logs show `OperationalError` or connection timeout messages.

**Resolution:**
1. Verify `ONRAMP_DATABASE_URL` is set and correctly formatted.
2. Test connectivity from the container:
   ```bash
   az containerapp exec --name onramp-backend --resource-group <rg-name> --command "python -c \"from app.db.session import engine; print(engine.url)\""
   ```
3. Check that the Azure SQL firewall allows connections from the Container App's outbound IPs or VNet.
4. Confirm the managed identity has the `db_datareader` and `db_datawriter` roles on the database.

### Environment Variable Misconfiguration

**Symptoms:** Application starts in development mode unexpectedly, or authentication fails.

**Resolution:**
1. List current environment variables:
   ```bash
   az containerapp show --name onramp-backend --resource-group <rg-name> --query "properties.template.containers[0].env" --output table
   ```
2. Cross-reference with the required variables listed in `docs/development.md`.
3. Update missing variables:
   ```bash
   az containerapp update --name onramp-backend --resource-group <rg-name> --set-env-vars "KEY=value"
   ```

---

## Escalation Path

| Level | Who | When |
|-------|-----|------|
| L1 — Self-service | Deploying engineer | First 15 minutes. Follow this runbook. |
| L2 — Platform team | Infrastructure / DevOps lead | After 15 min or if the issue is infrastructure-related (networking, DNS, ACR). |
| L3 — Azure Support | Microsoft support ticket | Azure platform issues (Container Apps service outage, ARM failures). |

**When escalating, include:**
- Deployment ID and timestamp
- Container App revision name
- Relevant log snippets (last 50 lines of console logs)
- Application Insights correlation ID if available
