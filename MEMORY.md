# Project Memory

This file captures project learnings that persist across agent sessions. It serves as
institutional memory so agents don't repeat mistakes or rediscover established patterns.

**How to update this file:** When you learn something that future agents should know —
a pattern that works well, a mistake to avoid, a key decision — add it to the appropriate
section below. Keep entries concise (one or two lines). Include dates for decisions.
Do not remove entries unless they are explicitly obsolete.

---

## Project Overview

**OnRamp** is an AI-powered Azure Landing Zone Architect & Deployer. It guides Azure
customers through Microsoft's Cloud Adoption Framework (CAF) via an adaptive questionnaire,
generates compliant landing zone architectures, scores them against compliance frameworks,
and deploys them to customer Azure subscriptions via Bicep templates.

**Core workflow:** Questionnaire → Architecture Generation → Compliance Scoring → Bicep Preview → Deployment

**Tech stack:**
- Frontend: React 19 + TypeScript 5.9 + Vite 7 + Fluent UI v9
- Backend: Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) + Alembic
- Database: Azure SQL (production), SQLite (dev)
- AI: Azure AI Foundry via OpenAI-compatible client
- Auth: Microsoft Entra ID / MSAL
- IaC: Bicep (Azure-native)
- Hosting: Azure Container Apps
- CI/CD: GitHub Actions

**Dev mode:** When `ONRAMP_AZURE_TENANT_ID` is empty, the app runs with mock auth, SQLite,
mock AI responses, and no Azure SDK calls. Always test in dev mode first.

---

## Patterns That Work

- **Dev mode detection via empty env var:** `ONRAMP_AZURE_TENANT_ID` empty = dev mode. Clean, simple gate for all Azure dependencies.
- **Services as singletons:** Business logic services instantiated once at module level, imported where needed. Avoids DI complexity.
- **Pydantic v2 for all API validation:** Request/response models in `backend/app/schemas/`. Catches bad input early.
- **`makeStyles` + Fluent UI `tokens`:** Consistent styling across frontend. Never raw CSS values.
- **Lazy-loaded pages with `React.lazy()` + `<Suspense>`:** All page components follow this pattern for code splitting.
- **API client centralization:** All backend calls go through `frontend/src/services/api.ts`. Never direct `fetch()` in components.
- **Idempotent seed data:** `backend/app/db/seed.py` checks row count before inserting. Safe to run repeatedly at startup.
- **`./dev.sh up`** starts the full dev environment with one command. Frontend on :5173, backend on :8000.

## Patterns to Avoid

- **Never use `@fluentui/react` (v8):** Only `@fluentui/react-components` (v9). Icon names differ between versions — always verify.
- **Never hardcode `localhost` in API calls:** Use relative URLs (`/api/...`). Vite proxy handles routing to backend.
- **Never use `print()` in Python:** Use `logging.getLogger(__name__)` instead.
- **Never use `any` in TypeScript:** Use `unknown` with type guards for catch blocks.
- **Never use synchronous DB calls:** All I/O must be `async`/`await`.
- **`ONRAMP_CORS_ORIGINS` must be JSON array:** `'["http://localhost:5173"]'`, not comma-separated. Pydantic v2 parses `list[str]` as JSON.
- **MSAL `PublicClientApplication` crashes with empty `clientId`:** AuthProvider must skip MSAL entirely in dev mode.

## Key Decisions

- **Fluent UI v9 only:** Chose v9 (`@fluentui/react-components`) for consistency with modern Microsoft design. Never mix with v8.
- **SQLAlchemy 2.0 async:** Full async ORM for all database operations. Uses `aiosqlite` in dev, `aioodbc` in production.
- **Bicep over Terraform:** Azure-native IaC. Customer landing zone templates in `backend/app/templates/bicep/`, OnRamp's own infra in `infra/`.
- **Conventional Commits:** All commit messages use `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:` prefixes.
- **75% coverage minimum:** CI enforces on both frontend (vitest) and backend (pytest-cov). Critical paths target 90%+.

## Common Mistakes

- Vite proxy must point to `http://backend:8000` (Docker service name) in containers, not `http://localhost:8000`.
- Vite HMR in WSL needs `clientPort: 5173` in `vite.config.ts`.
- ODBC driver installation fails in clean Docker builds — only needed for production Azure SQL, not dev mode.
- `document.createElement` mocks break jsdom rendering in tests. Mock `URL.createObjectURL` AFTER `render()`.
- Fluent UI Checkbox does not reliably toggle via `userEvent.click` in jsdom.
- `use_ai: False` alone does not fall back to archetypes — also pass `use_archetype: True`.

## Reviewer Feedback

- *(No entries yet — add broadly applicable review feedback here)*
