# Changelog

All notable changes to the OnRamp project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Domain glossary (`docs/glossary.md`)
- Repository governance artifacts (CODEOWNERS, dependabot, releasing guide)
- Path-scoped Copilot instructions for DevOps and database workflows
- Changelog following Keep a Changelog format

### Changed
- Standardized version references across all documentation (Python 3.12+, Node.js 24)

## [0.18.0] — M5 Infrastructure & CI/CD Hardening

### Added
- Bicep validation step in CI pipeline (`az bicep build --file infra/main.bicep`)
- Coverage enforcement in CI (backend 75%, frontend thresholds in vitest.config.ts)
- Security headers middleware (HSTS, X-Frame-Options, CSP, X-Content-Type-Options)
- Pipeline integration documentation (`docs/pipeline-integration.md`)

### Changed
- CI pipeline runs lint, test, and build on every push and PR
- Upgraded CI runners to Node.js 24 and Python 3.12

### Fixed
- Docker build failures from ODBC driver apt repository issues

## [0.17.0] — M4 Frontend Quality & UX

### Added
- Frontend test suite (24 files, 122+ tests) with Vitest and Testing Library
- Coverage reporting with `@vitest/coverage-v8`
- `PageSkeleton` loading component for lazy-loaded pages
- `ErrorBoundary` and `ApiError` shared components
- UX checklist documentation (`docs/ux-checklist.md`)

### Changed
- All page components lazy-loaded with `React.lazy()` and `<Suspense>`
- Migrated styling to Griffel `makeStyles` with Fluent UI `tokens`

### Fixed
- Vite HMR in WSL requiring `clientPort: 5173`
- MSAL `PublicClientApplication` crash when `clientId` is empty in dev mode

## [0.16.0] — M3 Backend Code Quality

### Added
- Ruff linting with rules E, F, I, N, W, UP
- Google-style docstrings on all public functions and classes
- Pydantic v2 schemas for all API request/response validation
- Cost policy and secrets policy documentation

### Changed
- Line length enforced at 100 characters via Ruff
- Import ordering enforced (stdlib → third-party → local)
- Services refactored to singleton pattern at module level

### Fixed
- Silent exception swallowing in deployment orchestrator

## [0.15.0] — M2 Test Coverage & Quality

### Added
- Backend test suite (35 files, 245+ tests) with pytest and pytest-asyncio
- Route, service, model, schema, and integration test categories
- `pytest-cov` with 75% minimum coverage threshold
- E2E flow tests and performance tests

### Changed
- `asyncio_mode = "auto"` in pytest configuration
- Test pattern standardized on `httpx.AsyncClient` with `ASGITransport`

## [0.14.0] — M1 Critical Security & Stability

### Added
- Entra ID authentication with MSAL (frontend + backend token validation)
- RBAC middleware with Admin, Architect, Viewer roles
- Azure Key Vault integration for secrets management
- CORS configuration restricted to explicit allowed origins

### Security
- All production secrets stored in Azure Key Vault
- Token validation via PyJWT + JWKS
- Input validation enforced through Pydantic schemas on all endpoints

## [0.13.0] — M0 UX Agent Setup

### Added
- Core application scaffold: React 19 + TypeScript + Vite frontend
- FastAPI backend with SQLAlchemy 2.0 async ORM
- Guided questionnaire covering 8 CAF design areas
- AI architecture generation via Azure AI Foundry
- Interactive architecture visualizer with Fluent UI v9
- Compliance scoring against SOC 2, HIPAA, PCI-DSS, FedRAMP, NIST 800-53, ISO 27001
- Bicep template generation from architecture JSON
- One-click deployment to Azure via ARM
- Dev mode with mock auth, SQLite, and mock AI responses
- Docker Compose development environment (`dev.sh`)
- Landing zone archetypes (Small, Medium, Enterprise)
- Project structure documentation and README
