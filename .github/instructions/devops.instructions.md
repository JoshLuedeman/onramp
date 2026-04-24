---
applyTo: ".github/workflows/**,docker-compose.yml,**/Dockerfile"
---

# DevOps Instructions (CI/CD, Docker, Deployment)

## GitHub Actions Best Practices

- Pin action versions to full SHA or major version tag (e.g., `actions/checkout@v4`). Never use `@main` or `@latest`.
- Use `concurrency` groups to cancel redundant workflow runs on the same branch.
- Cache dependencies (`actions/cache` or built-in caching in `actions/setup-node`, `actions/setup-python`) to speed up builds.
- Store secrets in GitHub repository secrets. Never hardcode credentials in workflow files.
- Use `environment` protection rules for production deployments requiring approval.
- Keep workflow files focused — one workflow per concern (CI, deploy, release).
- Use `if: failure()` and `if: always()` for cleanup steps that must run regardless of job status.

## CI Pipeline Requirements

Every push to `main` and every PR must run:

1. **Frontend:** `npm ci` → `npm run lint` → `npm run test:coverage` → `npm run build`
2. **Backend:** `pip install -e ".[dev]"` → `ruff check app/` → `pytest tests/ -v --cov=app --cov-fail-under=75`
3. **Infrastructure:** `az bicep build --file infra/main.bicep`

Coverage thresholds are enforced — builds fail if coverage drops below minimums.

## Docker Image Optimization

- Use multi-stage builds to separate build dependencies from runtime.
- Use specific base image tags (e.g., `python:3.12-slim`), not `latest`.
- Order `COPY` and `RUN` instructions from least-frequently to most-frequently changed for optimal layer caching.
- Copy dependency manifests (`package.json`, `pyproject.toml`) and install before copying source code.
- Use `.dockerignore` to exclude `node_modules/`, `.venv/`, `__pycache__/`, `.git/`, and test files from build context.
- Run containers as non-root users in production.
- Set `HEALTHCHECK` instructions for container orchestrator health probes.

## Security Scanning

- Run `ruff check` (backend) and `eslint` (frontend) on every CI run.
- Enable Dependabot for automated dependency vulnerability alerts.
- Never install packages with `--force` or `--legacy-peer-deps` without documenting why.
- Use `npm audit` and `pip audit` in CI for known vulnerability detection.
- Scan Docker images for vulnerabilities before pushing to a registry.

## Deployment Workflow Conventions

- Deploy only from `main` branch after CI passes.
- Use Azure Container Apps for hosting (frontend + backend containers).
- Tag images with the git SHA for traceability: `ghcr.io/joshluedeman/onramp-backend:${{ github.sha }}`.
- Use `azd` (Azure Developer CLI) or Bicep for infrastructure provisioning.
- Separate provisioning (`azd provision`) from code deployment (`azd deploy`) to reduce blast radius.
- Roll back by redeploying the previous known-good image tag, not by reverting code.

## Docker Compose (Development)

- `docker-compose.yml` is for local development only. Never use it for production.
- Service names must match what Vite proxy and backend expect (e.g., `backend`, `frontend`).
- Use `healthcheck` on services so `depends_on` with `condition: service_healthy` works correctly.
- Mount source directories as volumes for hot reload during development.
