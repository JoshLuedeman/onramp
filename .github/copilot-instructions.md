# OnRamp — Copilot Instructions

## Project Overview
OnRamp is an AI-powered Azure Landing Zone Architect & Deployer. It guides Azure customers through Microsoft's Cloud Adoption Framework (CAF) via an adaptive questionnaire, generates compliant landing zone architectures, and deploys them via Bicep templates.

## Architecture
- **Frontend:** React 18 + TypeScript + Vite + Fluent UI v9 (`@fluentui/react-components`)
- **Backend:** Python 3.12+ / FastAPI (async)
- **Database:** Azure SQL (SQLAlchemy 2.0 async + Alembic migrations; SQLite in dev mode)
- **AI:** Azure AI Foundry via OpenAI-compatible client (mock fallback in dev mode)
- **Auth:** Microsoft Entra ID / MSAL (bypassed in dev mode when no client ID configured)
- **IaC:** Bicep templates for customer landing zones
- **Hosting:** Azure Container Apps
- **CI/CD:** GitHub Actions

## Project Structure
```
onramp/
├── frontend/          # React + Fluent UI v9
│   └── src/
│       ├── auth/      # MSAL config, AuthProvider, useAuth hook
│       ├── components/# wizard/, visualizer/, shared/
│       ├── pages/     # HomePage, WizardPage, ArchitecturePage, CompliancePage, BicepPage, DeployPage
│       └── services/  # API client (api.ts)
├── backend/
│   └── app/
│       ├── api/routes/ # FastAPI route modules
│       ├── services/   # Business logic (questionnaire, architecture, bicep, compliance, deployment)
│       ├── models/     # SQLAlchemy ORM models
│       ├── schemas/    # Pydantic request/response schemas
│       ├── db/         # Database engine, session, seed script, migrations
│       ├── auth/       # Entra ID token validation, RBAC
│       └── templates/bicep/  # Bicep template library
├── infra/             # Bicep modules for OnRamp's own Azure infrastructure
├── docs/              # Architecture, API, and development documentation
├── dev.sh             # One-command dev environment (Docker)
└── docker-compose.yml # Dev containers (backend + frontend)
```

## Development Environment
- Run `./dev.sh up` to start the full dev environment in Docker containers
- Frontend: Vite dev server on port 5173 with HMR and `/api` proxy to backend
- Backend: Uvicorn on port 8000 with auto-reload
- No Azure credentials needed for dev mode (mock auth, mock AI, SQLite DB)

## Coding Standards

### Frontend
- Use Fluent UI v9 components (`@fluentui/react-components`), NOT v8
- Use `makeStyles` for styling (Griffel), not CSS modules or inline styles
- Use `tokens` from Fluent UI for colors, spacing, typography
- All pages must be lazy-loaded with `React.lazy` and `Suspense`
- TypeScript strict mode — no `any` types unless absolutely necessary
- API calls go through `frontend/src/services/api.ts` using relative URLs (Vite proxies `/api`)

### Backend
- All routes go in `backend/app/api/routes/` and are registered in `main.py`
- Use Pydantic v2 models for request/response validation
- Use async/await for all database and I/O operations
- Environment variables use `ONRAMP_` prefix (managed via `config.py` Settings class)
- `ONRAMP_CORS_ORIGINS` must be JSON array format: `'["http://localhost:5173"]'`
- Services are singletons instantiated at module level

### Database
- SQLAlchemy 2.0 async with `aiosqlite` in dev, `aioodbc` in production
- Alembic for migrations (`backend/alembic/`)
- Seed data is idempotent — `backend/app/db/seed.py` checks before inserting

### Testing
- Backend: pytest with httpx AsyncClient (`backend/tests/`)
- Run tests: `./dev.sh test`

## Key Patterns
- **Dev mode detection:** Empty `ONRAMP_AZURE_TENANT_ID` → dev mode (mock auth, SQLite, mock AI)
- **Question data:** `recommended: true` on best-practice options; `_unsure` value for "make a recommendation" fallback
- **Architecture flow:** Wizard answers → `get_archetype_for_answers()` → customize → JSON → Bicep generation
- **Compliance scoring:** Maps architecture properties to framework controls (6 frameworks seeded)

## What NOT to Do
- Don't use `@fluentui/react` (v8) — only use `@fluentui/react-components` (v9)
- Don't hardcode `localhost` in API URLs — use relative paths for Vite proxy
- Don't add ODBC driver dependencies to the dev Dockerfile
- Don't use `require()` in frontend code — use ES module imports
- Don't commit `.env` files or Azure credentials
