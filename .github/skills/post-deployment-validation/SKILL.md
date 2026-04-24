---
name: post-deployment-validation
description: "Post-deployment validation workflow for verifying deployments to staging or production. Use after a deployment to confirm health, performance, security, and observability before declaring success."
---

# Post-Deployment Validation Workflow

## Overview

Workflow for validating a deployment to any environment (staging or production) after it
completes. Use this workflow immediately after a deployment to confirm the application is
healthy, performant, secure, and observable before declaring the deployment successful. If
validation fails, the workflow includes rollback decision criteria to minimize user impact.

## Trigger

A deployment to staging or production has completed — whether triggered by a CI/CD pipeline,
a manual deployment, or the release workflow. The trigger must include the environment name,
deployed version, and deployment timestamp.

## Steps

| # | Role | Action | Inputs | Outputs | Success Criteria |
|---|------|--------|--------|---------|------------------|
| 0 | **Orchestrator** | Initialize workflow: create state file, record deployment metadata (environment, version, timestamp) | Trigger event, deployment metadata | `.teamwork/state/<id>.yaml`, metrics log entry | State file created with status `active`; deployment metadata recorded |
| 1 | **DevOps** | Run smoke tests: health endpoint checks, critical API path validation, database connectivity verification | Deployment metadata, health endpoints list | Smoke test report with pass/fail per endpoint and response times | All health endpoints return 200; critical paths respond within SLA; database connections succeed |
| 2 | **DevOps** | Validate error rates and latency: check error rate delta vs pre-deployment baseline, measure p50/p95/p99 latency | Monitoring dashboards, pre-deployment baseline metrics | Error rate report, latency percentile report, baseline comparison | Error rate < 1% (or no increase from baseline); p99 latency < 2s; no latency regression > 20% |
| 3 | **QA Lead** | Validate monitoring and alerting: confirm logs are flowing, metrics are reporting, alerts are armed | Monitoring configuration, log aggregation endpoints | Monitoring validation report: log flow, metric ingestion, alert status | Logs ingesting from new deployment; key metrics reporting; alerts configured and not firing |
| 4 | **DevOps** | Validate feature flags and configuration: confirm new features are gated correctly, environment-specific config is applied | Feature flag configuration, environment config | Feature flag validation report, config verification | Feature flags match expected state per environment; no dev-only flags enabled in production |
| 5 | **Security Auditor** | Post-deployment security check: verify TLS certificates, security headers, auth endpoints, exposed ports | Deployment URL, security baseline | Security validation report: TLS status, header audit, port scan, auth verification | TLS valid and not expiring within 30 days; security headers present; no unexpected open ports; auth endpoints functional |
| 6 | **Orchestrator** | Evaluate rollback decision: aggregate all validation results against rollback criteria | All validation reports from steps 1–5 | Rollback decision (proceed or rollback) with rationale | Decision made based on criteria; if rollback needed, trigger rollback-workflow |
| 7 | **Documenter** | Update deployment log: record deployment version, environment, validation results, and any issues found | All validation reports, rollback decision | Deployment log entry, changelog update (if needed) | Deployment log updated; issues documented for follow-up |
| 8 | **Orchestrator** | Complete workflow: validate all gates passed, update state | All step outputs, quality gate results | State file with status `completed`, final metrics | All completion criteria verified |

## Handoff Contracts

Each step must produce specific artifacts before the next step can begin.

The orchestrator validates each handoff artifact before dispatching the next role. Handoffs are stored in `.teamwork/handoffs/<workflow-id>/` following the format in `.teamwork/docs/protocols.md`.

**Deployment trigger → Orchestrator**
- Deployment metadata: environment (staging/production), deployed version, deployment timestamp
- Deployment method (CI/CD pipeline, manual, release workflow)
- Pre-deployment baseline metrics (error rate, latency percentiles) if available

**Orchestrator → DevOps (Step 1)**
- List of health endpoints to check
- Expected response codes and maximum acceptable response times
- Database connectivity check targets

**DevOps (smoke tests) → DevOps (error rates)**
- Smoke test report with per-endpoint results (status code, response time, pass/fail)
- Any immediate failures that warrant early rollback

**DevOps (error rates) → QA Lead**
- Error rate report with pre/post deployment comparison
- Latency percentile report (p50, p95, p99) with baseline comparison
- Flag if any metric exceeds rollback threshold

**QA Lead → DevOps (feature flags)**
- Monitoring validation report confirming observability is operational
- List of any monitoring gaps or silent alerts

**DevOps (feature flags) → Security Auditor**
- Feature flag state verification per environment
- Configuration diff between expected and actual

**Security Auditor → Orchestrator (rollback decision)**
- Security validation report with TLS, headers, ports, and auth status
- Any critical security findings requiring immediate action

**Orchestrator → Documenter**
- Aggregated validation results with rollback decision
- List of issues found (if any) for follow-up tracking

## Quality Gates

Each validation step has pass/fail criteria that feed into the rollback decision:

| Check | Pass | Fail (triggers rollback evaluation) |
|-------|------|-------------------------------------|
| Health endpoints | All return 200 within timeout | Any endpoint returns non-200 or times out |
| Error rate | < 1% overall; no increase > 0.5% from baseline | ≥ 1% error rate OR > 0.5% increase from baseline |
| p99 latency | < 2s for all critical paths | ≥ 2s for any critical path |
| Latency regression | < 20% increase from baseline | ≥ 20% increase from baseline |
| Log ingestion | Logs flowing within 5 minutes of deployment | No logs from new deployment after 5 minutes |
| Metrics reporting | Key metrics (request count, error count, latency) reporting | Any key metric missing or stale |
| Alerts | Configured and not firing false positives | Alerts missing or firing on healthy state |
| Feature flags | Match expected state per environment | Mismatch between expected and actual flag state |
| TLS certificates | Valid and not expiring within 30 days | Expired, invalid, or expiring within 30 days |
| Security headers | All required headers present (HSTS, CSP, X-Frame-Options) | Any required header missing |
| Auth endpoints | Login/logout/token refresh functional | Any auth endpoint returning errors |

## Error Handling

### Smoke Tests Fail (Step 1)

- **Health endpoint returns non-200**: Retry 3 times with 10-second intervals. If still failing after retries, check if the deployment is still rolling out (wait for rollout completion). If the endpoint is genuinely down, proceed directly to rollback decision (step 6) with recommendation to rollback.
- **Database connectivity failure**: Verify connection strings and network rules match the environment. Check if a migration failed. If unresolvable within 5 minutes, recommend rollback.
- **Timeout on critical paths**: Check if the service is under unusual load from deployment traffic. If response times don't stabilize within 5 minutes, flag for rollback evaluation.

### Monitoring Shows Errors (Step 2–3)

- **Error rate spike after deployment**: Compare error types — if errors are new error codes not present pre-deployment, this is a strong rollback signal. If errors match pre-existing patterns, investigate further before deciding.
- **Latency regression**: Determine if the regression is transient (cold start, cache warming) or persistent. Wait 10 minutes for stabilization. If p99 remains above threshold, recommend rollback.
- **Missing logs or metrics**: Check log pipeline health independently of the deployment. If the log pipeline itself is down, this is not a deployment issue — escalate to the DevOps team separately.

### Rollback Criteria

Rollback is recommended when **any** of the following are true:
- Error rate > 1% sustained for more than 5 minutes after deployment
- p99 latency > 2s sustained for more than 5 minutes after deployment
- Any health endpoint is unreachable after retries
- Critical security finding (expired TLS, missing auth, open ports)
- Feature flags in wrong state in production (e.g., experimental feature enabled for all users)

Rollback is **not** recommended when:
- Issues are transient and self-resolving (cache warming, cold starts)
- Problems pre-date the deployment (baseline was already degraded)
- Only non-critical monitoring gaps exist (e.g., a dashboard widget is broken)

### Escalation to Human

Escalate immediately when:
- Rollback decision is ambiguous (metrics are borderline)
- The rollback itself fails or causes additional issues
- Security findings indicate active exploitation
- Data integrity concerns are raised (potential data corruption or loss)

## Notes

- **Staging vs production**: Run the full validation in both environments. Staging validation
  acts as a gate before production deployment. Production validation confirms the live system.
- **Baseline metrics**: Pre-deployment baseline metrics should be captured automatically by
  the CI/CD pipeline or the release workflow. If no baseline exists, use the last 24 hours
  of metrics as the comparison period.
- **Parallel validation**: Steps 1 and 3 can begin in parallel since smoke tests and monitoring
  validation are independent. Step 5 (security) can also run in parallel with steps 2–4.
  The orchestrator should maximize parallelism to minimize validation time.
- **Rollback integration**: If the rollback decision at step 6 is "rollback", the orchestrator
  invokes the rollback-workflow skill and sets this workflow's state to `failed` with the
  rollback reason. The deployment log (step 7) still runs to record what happened.
- **Gradual rollouts**: For canary or blue-green deployments, run validation against the canary
  or new environment before shifting traffic. Adjust error rate and latency thresholds to
  account for the smaller traffic sample on the canary.
- **Orchestrator coordination:** The orchestrator manages workflow state throughout. If any
  quality gate fails, the orchestrator keeps the workflow at the current step and notifies
  the responsible role. If a blocker is raised, the orchestrator sets the workflow to
  `blocked` and escalates to the human.
