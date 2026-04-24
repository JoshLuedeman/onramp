# Security Practices for Contributors

Security guidelines for humans and agents contributing to OnRamp. This document covers the controls, tools, and conventions that keep the application and its users safe.

## Secrets Management

### Rules

1. **Never commit secrets.** API keys, tokens, passwords, private keys, connection strings — none of these belong in the repository. Not even temporarily. Not even in test files.
2. **Use environment variables.** All secrets are provided via environment variables prefixed with `ONRAMP_` (e.g., `ONRAMP_AZURE_TENANT_ID`, `ONRAMP_DATABASE_URL`). Local development uses `.env` files, which are listed in `.gitignore`.
3. **Azure Key Vault for production.** Production secrets are stored in Azure Key Vault and injected into the application at runtime. Never hardcode production values anywhere in the codebase.
4. **Agent credential isolation.** Each tool manages its own authentication separately (GitHub CLI uses `gh auth`, Claude CLI uses its own login). Agents do not share credentials with each other or store them in the repository.
5. **Escalate when blocked.** If a secret is needed to complete work, stop and ask the human. Never attempt to find, guess, or extract secrets from other sources.

### Pre-Commit Protection

The project uses a pre-commit hook (`detect-private-key` from [pre-commit-hooks](https://github.com/pre-commit/pre-commit-hooks)) that blocks commits containing private keys. This is a safety net — contributors should never reach the point where the hook needs to catch something.

Install with:

```bash
pre-commit install
```

### If a Secret Is Accidentally Committed

1. **Rotate** the exposed credential immediately.
2. **Remove** it from Git history (not just the working tree).
3. **File an incident report** documenting what was exposed and for how long.
4. The **Security Auditor** agent reviews the incident and recommends preventive measures.

For full details, see [Secrets Policy](secrets-policy.md).

## Dependency Scanning

### Automated Tools

| Tool | Scope | Integration |
|------|-------|-------------|
| **pip-audit** | Python dependencies | CI pipeline — runs on every PR |
| **npm audit** | Node.js dependencies | CI pipeline — runs on every PR |
| **Dependabot** | All dependencies | GitHub-native — opens PRs for updates automatically |

### Contributor Responsibilities

- Run `pip-audit` locally before opening a PR with Python dependency changes.
- Run `npm audit` locally before opening a PR with Node.js dependency changes.
- Review Dependabot PRs promptly — don't let security updates languish.
- When adding a new dependency, justify the choice. Prefer standard library when reasonable.
- Pin versions and always commit lockfiles (`package-lock.json`, `requirements.txt`).

### The Dependency Manager Agent

The **Dependency Manager** agent monitors, evaluates, and updates dependencies for security, compatibility, and health. It handles vulnerability remediation and license compliance through the `dependency-update` workflow skill.

## Code Scanning

### CodeQL (SAST)

GitHub CodeQL runs static analysis security testing on every pull request, scanning for:

- SQL injection
- Cross-site scripting (XSS)
- Path traversal
- Insecure deserialization
- Hard-coded credentials
- Other language-specific vulnerability patterns

### Semgrep

The **Security Auditor** agent uses Semgrep (via `semgrep-mcp`) for on-demand SAST scanning during code review. The **Coder** and **Reviewer** agents also have access to Semgrep for self-auditing code before opening or approving PRs.

### Contributor Responsibilities

- Review CodeQL alerts on your PRs before requesting review.
- Do not dismiss CodeQL alerts without documented justification.
- If the Security Auditor flags a finding, address it before the PR can advance.

## Authentication

### Production: MSAL / Entra ID

OnRamp uses **Microsoft Entra ID** (formerly Azure AD) for authentication:

- The frontend uses **MSAL.js** to obtain OAuth 2.0 access tokens from Entra ID.
- The backend validates tokens using **PyJWT** with JWKS (JSON Web Key Set) verification against the Entra ID tenant.
- Tokens are validated for issuer, audience, expiration, and signature on every API request.

### Development: Mock Auth

When `ONRAMP_AZURE_TENANT_ID` is empty, the application runs in **dev mode**:

- Authentication is mocked — no Entra ID configuration required.
- A mock user is injected for all API requests.
- No Azure SDK calls are made.

**Important:** Always test in dev mode. Do not assume Azure credentials are available in development environments.

### Contributor Responsibilities

- Never bypass token validation in production code paths.
- Test both authenticated and unauthenticated scenarios.
- Do not store tokens in localStorage or expose them in URLs.

## Authorization

### RBAC Model

OnRamp implements role-based access control with three roles:

| Role | Permissions |
|------|-------------|
| **Admin** | Full access — manage users, deployments, all configurations |
| **Architect** | Create and modify architectures, run deployments |
| **Viewer** | Read-only access to architectures and compliance reports |

### Implementation

- Authorization is enforced via a **RoleChecker** dependency in FastAPI routes.
- Every route that modifies data must specify the required role.
- Follow the **principle of least privilege** — request the minimum role needed for each operation.

### Contributor Responsibilities

- Add `RoleChecker` dependencies to all new routes that modify state.
- Never grant broader access than an endpoint requires.
- Test that unauthorized users receive `403 Forbidden` responses.

## Network Security

### NSG Rules

Azure Network Security Groups restrict traffic to OnRamp infrastructure:

- Only required ports are open (HTTPS 443 for the application).
- Management ports are restricted to known IP ranges.
- Outbound traffic is limited to required Azure services.

### Private Endpoints

Production Azure resources (SQL Database, Key Vault, AI Foundry) use **private endpoints** to keep traffic on the Azure backbone network, never traversing the public internet.

### CORS Configuration

CORS is restricted to allowed origins only. The backend FastAPI application:

- Specifies exact allowed origins (no wildcards in production).
- Restricts allowed methods and headers to what the frontend actually uses.
- Does not allow credentials from unknown origins.

### Contributor Responsibilities

- Do not add `*` to CORS allowed origins.
- When adding new Azure resources in Bicep, configure private endpoints.
- Review NSG rules in `infra/modules/` when modifying network configuration.

## Input Validation

### Pydantic Schemas

All API input is validated through **Pydantic models** before reaching business logic:

- Every API endpoint must define a Pydantic schema for request bodies, query parameters, and path parameters.
- Schemas enforce type constraints, value ranges, string lengths, and required fields.
- Invalid input returns `422 Unprocessable Entity` with descriptive error messages.

### Rules

- **Never trust raw data.** All input from users, external APIs, and even internal services must be validated.
- Define schemas in `backend/app/schemas/` following existing patterns.
- Use Pydantic's built-in validators for common patterns (email, URL, UUID).
- Add custom validators for domain-specific constraints.

### Contributor Responsibilities

- Create a Pydantic schema for every new API endpoint.
- Register new routes in `backend/app/main.py`.
- Test validation with both valid and invalid inputs.

## Security Headers

The application sets the following security headers on all responses:

| Header | Value | Purpose |
|--------|-------|---------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Enforce HTTPS for all connections |
| `Content-Security-Policy` | Restrictive policy | Prevent XSS and data injection attacks |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME type sniffing |

### Contributor Responsibilities

- Do not weaken or remove security headers.
- When adding new frontend resources (scripts, styles, fonts), update the CSP policy rather than disabling it.
- Test that security headers are present in API responses.

## Container Security

### Health Checks

All containers must implement health check endpoints that:

- Verify the application is running and responsive.
- Check connectivity to required dependencies (database, Key Vault).
- Return appropriate status codes (`200` for healthy, `503` for unhealthy).

### Resource Limits

Azure Container Apps are configured with:

- **CPU and memory limits** to prevent resource exhaustion.
- **Replica scaling rules** based on HTTP traffic and CPU utilization.
- **Request timeouts** to prevent hanging connections.

### Additional Practices

- Use **read-only filesystems** where possible — containers should not write to their own filesystem except for designated temp directories.
- Run containers as **non-root users**.
- Use **minimal base images** to reduce attack surface.
- Keep container images up to date with security patches.

### Contributor Responsibilities

- Add health check endpoints to new services.
- Set resource limits in Bicep container definitions (`infra/modules/`).
- Do not run containers as root in production configurations.

## Incident Response

### Reporting Vulnerabilities

**Do NOT open a public issue** for security vulnerabilities.

Use GitHub's private vulnerability reporting:

👉 [Report a vulnerability](https://github.com/joshluedeman/onramp/security/advisories/new)

### What to Expect

1. **Acknowledgment** within 48 hours.
2. **Initial assessment** within 7 days.
3. **Collaboration** to understand and reproduce the issue.
4. **Coordinated disclosure** timing.
5. **Credit** in the security advisory (unless you prefer anonymity).

For full details, see [SECURITY.md](../SECURITY.md).

### If You Discover a Vulnerability While Contributing

1. **Stop.** Do not attempt to fix it in a public PR.
2. **Report** it through the private vulnerability reporting link above.
3. **Do not discuss** the vulnerability in public channels (issues, PRs, Slack) until disclosure is coordinated.
4. The **Security Auditor** agent and the security-response workflow handle remediation.

## Security Checklist for PRs

Before opening a PR, verify:

- [ ] No secrets, credentials, or tokens in the code (including test files)
- [ ] All API input validated through Pydantic schemas
- [ ] New routes have `RoleChecker` dependencies for authorization
- [ ] CodeQL alerts reviewed and addressed
- [ ] Dependencies are pinned and lockfiles committed
- [ ] CORS configuration unchanged (or change justified)
- [ ] Security headers not weakened or removed
- [ ] Container health checks present for new services
- [ ] No `print()` statements that could leak sensitive data in logs

## Related Documentation

- [SECURITY.md](../SECURITY.md) — Vulnerability reporting policy
- [Secrets Policy](secrets-policy.md) — Detailed secrets management rules
- [Architecture](architecture.md) — System architecture and security components
- [Conventions](conventions.md) — Coding standards including security-related conventions
- [Agent Lifecycle](agent-lifecycle.md) — Security Auditor agent role and responsibilities
