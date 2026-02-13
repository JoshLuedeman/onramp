# OnRamp — Copilot Instructions

## Project Overview

OnRamp is an AI-powered Azure Landing Zone Architect & Deployer. It guides Azure customers through Microsoft's Cloud Adoption Framework (CAF) via an adaptive questionnaire, generates compliant landing zone architectures, scores them against compliance frameworks, and deploys them to customer Azure subscriptions via Bicep templates.

**Target users:** Azure customers (IT architects, cloud engineers, platform teams) who need to stand up a governance-compliant Azure landing zone.

**Core workflow:** Questionnaire → Architecture Generation → Compliance Scoring → Bicep Preview → Deployment

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | React + TypeScript + Vite | React 18+, TS 5.9+, Vite 7+ |
| UI Framework | Fluent UI React v9 (`@fluentui/react-components`) | v9 only — never v8 |
| Backend | Python + FastAPI | Python 3.12+, FastAPI latest |
| ORM | SQLAlchemy 2.0 (async) + Alembic | SQLAlchemy 2.0+ |
| Database | Azure SQL (production), SQLite (dev) | via aiosqlite / aioodbc |
| AI/LLM | Azure AI Foundry via OpenAI-compatible client | openai package |
| Auth | Microsoft Entra ID / MSAL | msal-browser, msal-react, msal-python |
| IaC | Bicep | Azure-native |
| Hosting | Azure Container Apps | Containerized |
| CI/CD | GitHub Actions | Node 22, Python 3.12 |
| Linting (backend) | Ruff | 0.5+ |
| Linting (frontend) | ESLint + typescript-eslint | ESLint 9+ |
| Testing (backend) | pytest + pytest-asyncio + pytest-cov | pytest 8+ |

---

## Project Structure

```
onramp/
├── .github/
│   ├── copilot-instructions.md   # This file
│   └── workflows/
│       ├── ci.yml                 # Build, lint, test on push/PR
│       └── deploy.yml             # Deploy to Azure Container Apps
├── frontend/                      # React + Fluent UI v9
│   ├── src/
│   │   ├── auth/                  # MSAL config, AuthProvider, useAuth hook
│   │   ├── components/
│   │   │   ├── wizard/            # QuestionCard, ProgressBar, WizardComplete
│   │   │   ├── visualizer/        # ArchitectureDiagram, DetailPanel
│   │   │   └── shared/            # Layout, Header, AuthButton
│   │   ├── pages/                 # HomePage, WizardPage, ArchitecturePage,
│   │   │                          # CompliancePage, BicepPage, DeployPage
│   │   └── services/              # API client (api.ts) — single source for all API calls
│   ├── eslint.config.js
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── Dockerfile
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app entry, lifespan, router registration
│   │   ├── config.py              # Pydantic Settings with ONRAMP_ prefix
│   │   ├── api/routes/            # Route modules (questionnaire, architecture, etc.)
│   │   ├── services/              # Business logic singletons
│   │   ├── models/                # SQLAlchemy ORM models
│   │   ├── schemas/               # Pydantic request/response schemas
│   │   ├── db/                    # Engine, session factory, seed script
│   │   ├── auth/                  # Entra ID token validation, RBAC middleware
│   │   └── templates/bicep/       # Bicep template library
│   ├── alembic/                   # Database migrations
│   ├── tests/                     # pytest test suite (94+ tests)
│   ├── pyproject.toml
│   └── Dockerfile
├── infra/                         # Bicep modules for OnRamp's own Azure infrastructure
│   ├── main.bicep
│   ├── modules/                   # container-apps, sql, ai-foundry, keyvault, monitoring
│   └── azuredeploy.json           # ARM template for Deploy to Azure button
├── docs/                          # Architecture, API, and development documentation
├── dev.sh                         # One-command dev environment (up/down/reset/logs/test)
└── docker-compose.yml             # Dev containers (backend + frontend)
```

---

## Development Environment

| Command | Purpose |
|---------|---------|
| `./dev.sh up` | Start frontend + backend in Docker containers |
| `./dev.sh down` | Stop all containers |
| `./dev.sh logs` | Tail container logs |
| `./dev.sh test` | Run backend pytest suite in container |
| `./dev.sh reset` | Rebuild containers from scratch |
| `./dev.sh status` | Show container status |
| `./dev.sh shell backend` | Open a shell in the backend container |

- **Frontend:** Vite dev server on port `5173` with HMR. `/api` requests are proxied to the backend container.
- **Backend:** Uvicorn on port `8000` with `--reload` for auto-restart on file changes.
- **No Azure credentials required** for local dev — mock auth, mock AI, and SQLite are used automatically.
- **Dev mode detection:** When `ONRAMP_AZURE_TENANT_ID` is empty, the app runs in dev mode.

---

## Coding Standards

### General

- Write clear, self-documenting code. Only add comments for non-obvious logic.
- Prefer composition over inheritance.
- Keep functions focused — one responsibility per function.
- Use descriptive variable and function names that convey intent.
- No magic numbers or strings — use named constants.
- Handle errors explicitly — never silently swallow exceptions.

### Naming Conventions

| Context | Convention | Example |
|---------|-----------|---------|
| Python files | `snake_case` | `questionnaire.py`, `bicep_generator.py` |
| Python classes | `PascalCase` | `QuestionnaireService`, `DeploymentOrchestrator` |
| Python functions/vars | `snake_case` | `get_next_question()`, `org_size` |
| Python constants | `UPPER_SNAKE_CASE` | `CAF_QUESTIONS`, `DEFAULT_REGION` |
| TypeScript files | `PascalCase` for components, `camelCase` for utilities | `QuestionCard.tsx`, `api.ts` |
| TypeScript components | `PascalCase` | `WizardPage`, `ArchitectureDiagram` |
| TypeScript functions/vars | `camelCase` | `fetchNext()`, `selectedValue` |
| TypeScript interfaces | `PascalCase` | `Question`, `Architecture`, `Progress` |
| CSS classes (Griffel) | `camelCase` | `questionText`, `recommendedOption` |
| Environment variables | `ONRAMP_UPPER_SNAKE_CASE` | `ONRAMP_CORS_ORIGINS`, `ONRAMP_AZURE_TENANT_ID` |
| API routes | `kebab-case` paths | `/api/questionnaire/next`, `/api/architecture/generate` |
| Database tables | `snake_case`, plural | `users`, `projects`, `compliance_frameworks` |
| Database columns | `snake_case` | `created_at`, `org_size`, `management_group_id` |
| Git branches | `kebab-case` with prefix | `feat/wizard-back-button`, `fix/cors-proxy` |
| Commit messages | Conventional Commits | `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:` |

### Frontend Standards

- **Fluent UI v9 only** — use `@fluentui/react-components`. Never use `@fluentui/react` (v8).
- **Styling:** Use `makeStyles` (Griffel) for all component styles. Use `tokens` from Fluent UI for colors, spacing, font sizes, and typography. Do not use CSS modules, inline styles, or raw CSS values.
- **Pages:** All page components must be lazy-loaded with `React.lazy()` and wrapped in `<Suspense>`.
- **TypeScript:** Strict mode enabled. No `any` types unless absolutely necessary and justified with a comment.
- **API calls:** All backend communication goes through `frontend/src/services/api.ts` using relative URLs (e.g., `/api/questionnaire/next`). Never hardcode `localhost` or absolute URLs.
- **Imports:** Use ES module imports only. Never use `require()`.
- **State management:** React hooks (`useState`, `useEffect`, `useCallback`). No external state library unless complexity demands it.
- **Routing:** React Router v6 (`react-router-dom`). Route definitions live in `App.tsx`.
- **Icons:** Import from `@fluentui/react-icons`. Verify the icon name exists before using — not all v8 icon names exist in the current package.

### Backend Standards

- **Route modules:** All API routes go in `backend/app/api/routes/` and must be registered in `main.py` via `app.include_router()`.
- **Request/Response validation:** Use Pydantic v2 models in `backend/app/schemas/` for all API input/output.
- **Async everywhere:** All database operations, HTTP calls, and I/O must use `async`/`await`.
- **Services as singletons:** Business logic services (e.g., `questionnaire_service`, `bicep_generator`) are instantiated once at module level and imported where needed.
- **Configuration:** All environment variables use the `ONRAMP_` prefix and are managed through `backend/app/config.py` (Pydantic Settings). List-type env vars (e.g., `ONRAMP_CORS_ORIGINS`) must be JSON array format: `'["http://localhost:5173"]'`.
- **Logging:** Use Python's `logging` module with `logger = logging.getLogger(__name__)`. No `print()` statements in production code.
- **Error handling:** Raise `HTTPException` with appropriate status codes in route handlers. Services should raise domain-specific exceptions.
- **Line length:** 100 characters max (enforced by Ruff).
- **Import ordering:** stdlib → third-party → local (enforced by Ruff isort).

### Database Standards

- **ORM:** SQLAlchemy 2.0 async. Models in `backend/app/models/`.
- **Migrations:** Alembic in `backend/alembic/`. Always create a migration for schema changes — never modify the database directly.
- **Dev mode:** Uses `aiosqlite` (file-based SQLite). Production uses `aioodbc` with Azure SQL.
- **Seed data:** `backend/app/db/seed.py` populates initial data (questions, compliance frameworks). Seeding is **idempotent** — it checks row count before inserting. Called automatically during app startup via the FastAPI lifespan.
- **Session management:** Use the `get_db` FastAPI dependency which yields an async session (or `None` when no DB is configured).

### Infrastructure Standards

- **Bicep** is the IaC format for all Azure resources.
- Bicep modules live in `infra/modules/` and are composed by `infra/main.bicep`.
- The ARM template (`infra/azuredeploy.json`) powers the "Deploy to Azure" button in the README.
- Customer landing zone Bicep templates live in `backend/app/templates/bicep/`.

---

## Testing Standards

### Coverage Requirements (MANDATORY)

**Every code change must include tests.** This is non-negotiable — PRs without test coverage for new/modified code will not be merged.

- **Backend:** Target **75%+ line coverage** overall, **80%+ for services and routes**. All new code must have corresponding tests.
- **Frontend:** Target **75%+ line coverage** overall, **70%+ branch coverage**, **60%+ function coverage**.
- **Critical paths** (questionnaire flow, architecture generation, compliance scoring, deployment orchestration) must have **90%+ coverage**.
- Tests live in `backend/tests/` named `test_<module>.py` and `frontend/src/**/*.test.{ts,tsx}` colocated with source.
- CI enforces minimum 75% coverage on both frontend and backend — builds fail below this threshold.

### Backend Testing

- **Framework:** pytest + pytest-asyncio + httpx AsyncClient
- **Async mode:** `asyncio_mode = "auto"` in `pyproject.toml` — all async test functions are auto-detected.
- **Test categories:**
  - `test_health.py` — Health check endpoint
  - `test_api_integration.py` — API route integration tests
  - `test_questionnaire.py` — Questionnaire service logic
  - `test_archetypes.py` — Architecture archetype selection
  - `test_compliance.py`, `test_compliance_scoring.py` — Compliance engine
  - `test_bicep_generator.py` — Bicep template generation
  - `test_deployment.py` — Deployment orchestration
  - `test_credentials.py` — Azure credential management
  - `test_e2e_flow.py` — End-to-end flow tests
  - `test_performance.py` — Performance benchmarks
  - `test_startup.py` — App startup validation
  - `test_models.py` — ORM model tests
  - `test_rbac.py` — Role-based access control
  - `test_users.py` — User management

- **Running tests:**
  ```bash
  ./dev.sh test                    # In Docker container
  cd backend && pytest tests/ -v   # Local (requires Python 3.12+)
  ```

- **Writing new tests:**
  ```python
  import pytest
  from httpx import AsyncClient, ASGITransport
  from app.main import app

  @pytest.mark.asyncio
  async def test_example():
      transport = ASGITransport(app=app)
      async with AsyncClient(transport=transport, base_url="http://test") as client:
          response = await client.get("/health")
          assert response.status_code == 200
  ```

### Frontend Testing

- **Framework:** Vitest + @testing-library/react + @testing-library/user-event
- **Coverage:** @vitest/coverage-v8 (V8-based). Configured in `frontend/vitest.config.ts`.
- **Environment:** jsdom. Setup file at `frontend/src/test/setup.ts` (imports `@testing-library/jest-dom/vitest`, polyfills `ResizeObserver`).
- **Running tests:**
  ```bash
  cd frontend && npm run test           # Watch mode
  cd frontend && npm run test:coverage  # With coverage report
  ```
- **Writing new tests:**
  ```tsx
  import { render, screen } from '@testing-library/react';
  import { FluentProvider, teamsLightTheme } from '@fluentui/react-components';
  import { MemoryRouter } from 'react-router-dom';
  import MyComponent from './MyComponent';

  function renderWithProviders(ui: React.ReactElement) {
    return render(
      <FluentProvider theme={teamsLightTheme}>
        <MemoryRouter>{ui}</MemoryRouter>
      </FluentProvider>
    );
  }

  describe('MyComponent', () => {
    it('renders heading', () => {
      renderWithProviders(<MyComponent />);
      expect(screen.getByRole('heading')).toBeInTheDocument();
    });
  });
  ```
- **Known gotchas:**
  - Fluent UI components require `FluentProvider` wrapper in tests
  - `document.createElement` mocks break jsdom rendering — mock `URL.createObjectURL` after `render()`
  - Fluent UI Checkbox does not reliably toggle via `userEvent.click` in jsdom
  - Type-only files (`src/types/**`) are excluded from coverage
- **Linting:** ESLint with typescript-eslint and react-hooks plugin. Run with `npm run lint`.
- **Type checking:** `tsc -b` (run as part of `npm run build`).

### CI Pipeline

All of the following run on every push to `main` and every PR:
1. **Frontend:** `npm ci` → `npm run lint` → `npm run test:coverage` → `npm run build`
2. **Backend:** `pip install -e ".[dev]"` → `ruff check app/` → `pytest tests/ -v --cov=app --cov-fail-under=75`
3. **Infrastructure:** `az bicep build --file infra/main.bicep`

Coverage thresholds are enforced in CI — both frontend (vitest.config.ts thresholds) and backend (`--cov-fail-under=75`) will fail the build if coverage drops below minimums.

---

## Security Practices

- **Never commit secrets.** Use environment variables for all credentials. The `.env` file is gitignored.
- **Azure Key Vault** stores all production secrets (connection strings, API keys, client secrets).
- **Auth:** Microsoft Entra ID with MSAL. Tokens are validated server-side in `backend/app/auth/`.
- **RBAC:** Role-based access control via `RoleChecker` dependency (admin, architect, viewer roles).
- **Security headers:** HSTS, X-Frame-Options (DENY), X-Content-Type-Options (nosniff), CSP — applied via middleware in `main.py`.
- **CORS:** Explicitly configured allowed origins. Never use `allow_origins=["*"]` in production.
- **Input validation:** All API inputs are validated through Pydantic schemas. Never trust raw request data.
- **Dependencies:** Keep dependencies minimal. Azure SDK packages are optional extras (`pip install ".[azure]"`).

---

## Git & Workflow Conventions

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: Add back button to wizard questionnaire
fix: Resolve CORS issue with WSL proxy
docs: Update API documentation for scoring endpoint
refactor: Extract compliance scoring into separate service
test: Add integration tests for deployment orchestrator
chore: Update Python dependencies
```

### Branch Strategy

- `main` — production-ready code, protected
- `feat/<description>` — new features
- `fix/<description>` — bug fixes
- `docs/<description>` — documentation changes
- `refactor/<description>` — code refactoring

### Pull Requests

- PRs must pass all CI checks (lint, build, test, Bicep validation) before merge.
- Include a clear description of what changed and why.
- Reference related issues when applicable.

---

## Key Architectural Patterns

### Dev Mode vs Production Mode

The app detects its environment based on `ONRAMP_AZURE_TENANT_ID`:
- **Empty** → Dev mode: mock auth, SQLite, mock AI responses, no Azure SDK calls
- **Set** → Production mode: Entra ID auth, Azure SQL, real AI Foundry, real Azure deployments

### Service Architecture

Services are singleton instances created at module level:
- `questionnaire_service` — Adaptive question flow, progress tracking
- `ai_client` — Azure AI Foundry / OpenAI client with mock fallback
- `credential_manager` — Azure SDK credential management
- `bicep_generator` — Bicep template generation from architecture JSON
- `compliance_scorer` — Compliance framework scoring engine
- `deployment_orchestrator` — Multi-step Azure deployment with rollback

### Data Flow

1. **Questionnaire:** User answers → `POST /api/questionnaire/next` → adaptive next question
2. **Architecture:** All answers → `POST /api/architecture/generate` → archetype selection → customization → architecture JSON
3. **Compliance:** Architecture JSON → `POST /api/compliance/score` → framework scoring → gaps & remediation
4. **Bicep:** Architecture JSON → `POST /api/bicep/generate` → Bicep template files
5. **Deployment:** Bicep templates → `POST /api/deployment/deploy` → ARM deployment → status tracking

### Question Data Conventions

- Options with `"recommended": true` are highlighted as best-practice choices in the UI.
- Every choice question includes an `"_unsure"` option: "I'm not sure. Make a recommendation based on my requirements."
- Questions may have `"min_org_size"` for adaptive filtering based on organization size.

---

## Documentation

- `docs/architecture.md` — System architecture and design decisions
- `docs/api.md` — API endpoint reference
- `docs/development.md` — Developer setup and contribution guide
- `README.md` — Project overview, quickstart, Deploy to Azure button

### Docstring Standards

**Python:** Use Google-style docstrings for all public functions and classes:

```python
def get_next_question(self, answered_questions: dict[str, str]) -> dict | None:
    """Get the next unanswered question based on current answers and branching logic.

    Args:
        answered_questions: Map of question_id to answer value.

    Returns:
        The next question dict, or None if all questions are answered.
    """
```

**TypeScript:** Use JSDoc for exported functions and components:

```typescript
/**
 * Renders a single questionnaire question with answer input.
 * Highlights recommended options and includes an "unsure" fallback.
 */
export default function QuestionCard({ question, onAnswer }: QuestionCardProps) {
```

---

## Known Pitfalls

- `ONRAMP_CORS_ORIGINS` must be a JSON array string, not comma-separated — Pydantic Settings v2 parses `list[str]` fields as JSON.
- MSAL `PublicClientApplication` crashes with an empty `clientId` — the AuthProvider must skip MSAL entirely in dev mode.
- Vite proxy must point to `http://backend:8000` (Docker service name) when running in containers, not `http://localhost:8000`.
- The `@fluentui/react-icons` package does not contain all icon names from v8 — always verify an icon exists before importing.
- ODBC driver installation fails in clean Docker builds due to Microsoft apt repo issues — ODBC is only needed for production Azure SQL, not dev mode.
- Vite HMR in WSL needs `clientPort: 5173` set in `vite.config.ts` so the browser WebSocket connects correctly.

---

## Additional Resources

- [Azure Cloud Adoption Framework](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/)
- [Azure Landing Zone Accelerator](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/)
- [Fluent UI React v9 Documentation](https://react.fluentui.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Bicep Language Reference](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/)
