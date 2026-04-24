# Troubleshooting Guide

## Common Issues

### CORS Errors

**Symptoms:** Browser console shows `Access to fetch has been blocked by CORS policy`. API calls fail from the frontend but work via `curl`.

**Cause:** The `ONRAMP_CORS_ORIGINS` environment variable does not include the frontend's origin.

**Resolution:**
1. Check the current CORS configuration:
   ```bash
   # In development, CORS allows all origins by default.
   # In production, verify the allowed origins:
   az containerapp show --name onramp-backend --resource-group <rg-name> \
     --query "properties.template.containers[0].env[?name=='ONRAMP_CORS_ORIGINS'].value" -o tsv
   ```
2. Update the allowed origins to include the frontend URL:
   ```bash
   az containerapp update --name onramp-backend --resource-group <rg-name> \
     --set-env-vars "ONRAMP_CORS_ORIGINS=https://your-frontend-url.azurecontainerapps.io"
   ```
3. Multiple origins can be separated by commas.
4. In development mode (`ONRAMP_AZURE_TENANT_ID` not set), CORS allows all origins and methods automatically.

---

### Authentication Failures

**Symptoms:** API returns 401 Unauthorized. Frontend shows "Login failed" or redirects to login repeatedly.

**Diagnosis:**
1. **Check development mode:** If `ONRAMP_AZURE_TENANT_ID` is not set, the app runs in dev mode with mock authentication — no token is required.
2. **Verify Entra ID configuration:**
   ```bash
   # Ensure these are set in production:
   az containerapp show --name onramp-backend --resource-group <rg-name> \
     --query "properties.template.containers[0].env[?contains(name, 'AZURE')].{name: name, value: value}" -o table
   ```
3. **Check token validity:** Decode the JWT at [jwt.ms](https://jwt.ms) and verify:
   - `aud` matches `ONRAMP_AZURE_CLIENT_ID`
   - `tid` matches `ONRAMP_AZURE_TENANT_ID`
   - `exp` has not passed
4. **MSAL configuration:** Ensure the frontend's `VITE_AZURE_CLIENT_ID` and `VITE_AZURE_TENANT_ID` match the backend's configuration.
5. **App registration:** Verify the app registration in Entra ID has the correct redirect URIs for both local development and production.

---

### Database Connection Failures

**Symptoms:** API returns 500 errors. Backend logs show `sqlalchemy.exc.OperationalError` or connection timeouts.

**Diagnosis:**

1. **Development (SQLite):** The SQLite database is created automatically. If it's corrupted, delete it and restart:
   ```bash
   cd backend
   rm -f onramp.db
   # Restart the backend — init_db() and seed_database() will recreate it.
   ```

2. **Production (Azure SQL):**
   - Verify the connection string format:
     ```
     mssql+aioodbc://user:password@server.database.windows.net:1433/dbname?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes
     ```
   - Check firewall rules allow the Container App's outbound IPs.
   - Verify the managed identity has database access if using passwordless auth.
   - Test connectivity from the container:
     ```bash
     az containerapp exec --name onramp-backend --resource-group <rg-name> \
       --command "python -c \"from app.config import settings; print(settings.database_url[:50])\""
     ```

3. **Docker Compose:** The `docker-compose.yml` includes SQL Server 2022. If it fails to start:
   ```bash
   docker compose logs sqlserver
   # Common issue: not enough memory. SQL Server needs at least 2 GB.
   docker compose down -v  # Reset volumes
   docker compose up -d
   ```

---

### AI Foundry Timeouts

**Symptoms:** Architecture generation, compliance scoring, or Bicep generation hangs or returns a timeout error. Logs show `httpx.TimeoutException` or `asyncio.TimeoutError`.

**Diagnosis:**
1. **Check if running in dev mode:** Without `ONRAMP_AI_FOUNDRY_ENDPOINT` set, the app uses mock AI responses. If you're seeing timeouts, you're connecting to a real endpoint.
2. **Verify the endpoint and key:**
   ```bash
   # Check the configured endpoint (do NOT log the full key)
   az containerapp show --name onramp-backend --resource-group <rg-name> \
     --query "properties.template.containers[0].env[?contains(name, 'AI_FOUNDRY')].name" -o tsv
   ```
3. **Test endpoint reachability:**
   ```bash
   curl -sf https://<ai-foundry-endpoint>/openai/deployments?api-version=2024-02-01 \
     -H "api-key: <key>" | jq .
   ```
4. **Common causes:**
   - AI Foundry model deployment is stopped or not provisioned.
   - Rate limiting (429 responses) — check for `RateLimitError` in logs.
   - Network connectivity if the Container App is in a VNet without proper outbound rules.
5. **Mitigation:** The application falls back to mock responses if the AI service is unavailable in dev mode. For production, consider increasing the HTTP client timeout in `app/services/ai_foundry.py`.

---

### Deployment Validation Failures

**Symptoms:** `POST /api/deployment/validate` returns errors about subscription permissions or resource provider registration.

**Resolution:**
1. Ensure the service principal or managed identity has `Contributor` role on the target subscription.
2. Register required resource providers:
   ```bash
   az provider register --namespace Microsoft.Network
   az provider register --namespace Microsoft.Compute
   az provider register --namespace Microsoft.Storage
   az provider register --namespace Microsoft.KeyVault
   ```
3. In dev mode, deployment validation returns a simulated success.

---

## Debug Tools

### Development Mode

When `ONRAMP_AZURE_TENANT_ID` is not set, the application runs in development mode:

- **Mock authentication** — no Entra ID token required; a mock user is injected.
- **Mock AI responses** — architecture generation returns predefined results.
- **SQLite database** — no external database required.
- **Verbose health endpoint** — `GET /health` returns extended status including auth, AI, and database configuration.
- **Test notifications** — `POST /api/notifications/test` is available for testing.

### Container Logs

```bash
# Live logs (Azure)
az containerapp logs show --name onramp-backend --resource-group <rg-name> --type console --follow

# Docker Compose logs (local)
docker compose logs -f backend

# Filter for errors
docker compose logs backend 2>&1 | grep -i "error\|exception\|traceback"
```

### Application Insights KQL Queries

Access via Azure Portal → Application Insights → Logs.

```kql
// Recent exceptions with stack traces
exceptions
| where timestamp > ago(1h)
| project timestamp, problemId, outerMessage, innermostMessage, details
| order by timestamp desc
| take 20

// Slow requests (> 2 seconds)
requests
| where timestamp > ago(1h) and duration > 2000
| project timestamp, name, duration, resultCode, success
| order by duration desc

// Dependency failures (database, AI Foundry)
dependencies
| where timestamp > ago(1h) and success == false
| summarize count() by target, type, resultCode
| order by count_ desc

// Request volume by endpoint
requests
| where timestamp > ago(1h)
| summarize count() by name
| order by count_ desc

// Error rate over time
requests
| where timestamp > ago(6h)
| summarize total = count(), errors = countif(success == false) by bin(timestamp, 5m)
| extend error_pct = round(100.0 * errors / total, 1)
| order by timestamp desc
```

### FastAPI Interactive Docs

The backend auto-generates interactive API documentation:

| Tool | URL | Description |
|------|-----|-------------|
| Swagger UI | `http://localhost:8000/docs` | Interactive API explorer — try endpoints directly |
| ReDoc | `http://localhost:8000/redoc` | Read-only API reference with schemas |

---

## Environment Variable Checklist

Verify all required variables are set for your environment:

### Required for Production

| Variable | Description | Example |
|----------|-------------|---------|
| `ONRAMP_AZURE_TENANT_ID` | Entra ID tenant ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `ONRAMP_AZURE_CLIENT_ID` | App registration client ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `ONRAMP_DATABASE_URL` | Azure SQL connection string | `mssql+aioodbc://...` |
| `ONRAMP_AI_FOUNDRY_ENDPOINT` | Azure AI Foundry endpoint URL | `https://xxx.openai.azure.com/` |
| `ONRAMP_AI_FOUNDRY_KEY` | AI Foundry API key | (secret) |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `ONRAMP_CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `*` in dev mode |

### Frontend (Build-time)

| Variable | Description |
|----------|-------------|
| `VITE_AZURE_CLIENT_ID` | Must match backend's `ONRAMP_AZURE_CLIENT_ID` |
| `VITE_AZURE_TENANT_ID` | Must match backend's `ONRAMP_AZURE_TENANT_ID` |
| `VITE_API_BASE_URL` | Backend API URL (e.g., `http://localhost:8000`) |

### Quick Validation

```bash
# Check which production variables are set
env | grep ONRAMP_ | sed 's/=.*/=***/'

# Check if running in dev mode
curl -s http://localhost:8000/health | jq '.mode // "production (no mode field)"'
```
