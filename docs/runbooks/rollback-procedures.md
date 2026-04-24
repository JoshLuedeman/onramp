# Rollback Procedures

## Overview

OnRamp supports rollback at three levels: automatic (CI/CD), manual application rollback (Azure CLI), and database rollback (Alembic). Choose the appropriate level based on what failed.

---

## Automatic Rollback (CI/CD)

The `deploy.yml` GitHub Actions workflow includes a post-deployment health check. If the health check fails, the workflow automatically shifts traffic back to the previous stable revision.

**How it works:**
1. A new container image is built and pushed to ACR.
2. A new Container App revision is created with zero traffic.
3. The workflow probes `/health` on the new revision.
4. If healthy, traffic shifts 100 % to the new revision.
5. If unhealthy, the new revision is deactivated and traffic remains on the previous revision.

**To verify automatic rollback occurred:**
```bash
# Check workflow run status
gh run list --workflow=deploy.yml --limit 5

# Check which revision is active
az containerapp revision list \
  --name onramp-backend \
  --resource-group <rg-name> \
  --output table
```

---

## Manual Rollback via Azure CLI

Use manual rollback when you need to revert to a specific previous revision outside of the CI/CD pipeline.

### Step 1: List Available Revisions

```bash
az containerapp revision list \
  --name onramp-backend \
  --resource-group <rg-name> \
  --output table
```

Note the revision name you want to roll back to (e.g., `onramp-backend--abc1234`).

### Step 2: Activate the Target Revision

If the target revision is deactivated, reactivate it:

```bash
az containerapp revision activate \
  --name onramp-backend \
  --resource-group <rg-name> \
  --revision <target-revision-name>
```

### Step 3: Shift Traffic

Move all traffic to the target revision:

```bash
az containerapp ingress traffic set \
  --name onramp-backend \
  --resource-group <rg-name> \
  --revision-weight <target-revision-name>=100
```

For a gradual rollback (canary), shift traffic incrementally:

```bash
# 50/50 split
az containerapp ingress traffic set \
  --name onramp-backend \
  --resource-group <rg-name> \
  --revision-weight <target-revision-name>=50 <current-revision-name>=50

# Then shift fully once confirmed stable
az containerapp ingress traffic set \
  --name onramp-backend \
  --resource-group <rg-name> \
  --revision-weight <target-revision-name>=100
```

### Step 4: Deactivate the Bad Revision

```bash
az containerapp revision deactivate \
  --name onramp-backend \
  --resource-group <rg-name> \
  --revision <bad-revision-name>
```

### Frontend Rollback

The frontend is a static build served by a separate container. Follow the same revision-based process:

```bash
az containerapp revision list --name onramp-frontend --resource-group <rg-name> --output table
az containerapp ingress traffic set --name onramp-frontend --resource-group <rg-name> --revision-weight <target>=100
```

---

## Database Rollback with Alembic

Use database rollback when a migration introduced schema changes that need to be reverted. **Always roll back the database before rolling back the application if the old code is incompatible with the new schema.**

### Check Current Migration State

```bash
cd backend
alembic current
```

### View Migration History

```bash
alembic history --verbose
```

### Roll Back One Migration

```bash
alembic downgrade -1
```

### Roll Back to a Specific Revision

```bash
alembic downgrade <revision-id>
```

### Roll Back All Migrations (Nuclear Option)

```bash
alembic downgrade base
```

> ⚠️ **Warning:** Rolling back migrations can cause data loss if the downgrade function drops columns or tables. Always check the migration's `downgrade()` function before running it.

### Production Database Rollback

For Azure SQL in production:

1. **Take a backup first** (Azure SQL provides automatic backups, but confirm the retention policy covers your recovery window).
2. Run the Alembic downgrade from within the container:
   ```bash
   az containerapp exec \
     --name onramp-backend \
     --resource-group <rg-name> \
     --command "alembic downgrade -1"
   ```
3. Or connect to the database directly using the connection string and run migrations from a local environment with access.

---

## Verification Steps After Rollback

After any rollback, verify the system is healthy:

### 1. Health Check

```bash
curl -sf https://<app-url>/health
# Expected: {"status": "healthy"}
```

### 2. API Smoke Test

```bash
# Verify core endpoints respond
curl -sf https://<app-url>/api/questionnaire/categories | jq '.[] | .name'
curl -sf https://<app-url>/api/compliance/frameworks | jq '.[].short_name'
curl -sf https://<app-url>/api/bicep/templates | jq '.[].name'
```

### 3. Database Consistency

```bash
# Check current migration version matches the running code
cd backend
alembic current
```

### 4. Frontend Connectivity

Open the application in a browser and verify:
- Login flow completes (or mock auth in dev mode)
- Questionnaire loads and navigates
- Architecture generation returns results

### 5. Monitor for Errors

After rollback, watch Application Insights for 15–30 minutes:

```kql
// Error rate after rollback
requests
| where timestamp > ago(30m)
| summarize total = count(), errors = countif(success == false) by bin(timestamp, 1m)
| extend error_rate = round(100.0 * errors / total, 1)
| order by timestamp desc
```

---

## Decision Matrix

| Scenario | Rollback Type | Steps |
|----------|---------------|-------|
| Bad deploy, no DB changes | Manual revision rollback | Shift traffic to previous revision |
| Bad deploy with DB migration | Database rollback → revision rollback | Alembic downgrade, then shift traffic |
| CI/CD caught the failure | Automatic | Verify previous revision is active |
| Data corruption | Database restore from backup | Azure SQL point-in-time restore |
| Frontend-only issue | Frontend revision rollback | Shift frontend container traffic |
