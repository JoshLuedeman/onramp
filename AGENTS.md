# Copilot Coding Agent Instructions

## Task Workflow

When assigned a GitHub issue, follow these steps:

1. **Read the issue completely** — Understand the problem, requirements, and acceptance criteria.
2. **Check dependencies** — If the issue depends on another issue, verify it is completed first.
3. **Create a feature branch** — Use the naming convention: `feat/<short-description>` for features, `fix/<short-description>` for bugs.
4. **Implement the changes** — Follow the coding standards in `.github/copilot-instructions.md` and the path-scoped instructions in `.github/instructions/`.
5. **Write tests** — Every code change MUST include tests. This is non-negotiable.
6. **Run the test suite** — Backend: `cd backend && pytest tests/ -v --cov=app`. Frontend: `cd frontend && npm run test:coverage`. Both must pass.
7. **Run linters** — Backend: `cd backend && ruff check app/`. Frontend: `cd frontend && npm run lint`.
8. **Commit with Conventional Commits** — `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
9. **Open a pull request** — Reference the issue number. Include a clear description of changes.

## PR Requirements

- All CI checks must pass (lint, test, build, coverage thresholds)
- Tests cover all new/modified code
- No `any` types in TypeScript
- No `print()` statements in Python
- No hardcoded secrets or credentials
- Conventional commit message format

## Code Quality Checklist

Before opening a PR, verify:

- [ ] Backend tests pass: `cd backend && pytest tests/ -v`
- [ ] Frontend tests pass: `cd frontend && npm run test`
- [ ] Backend lint passes: `cd backend && ruff check app/`
- [ ] Frontend lint passes: `cd frontend && npm run lint`
- [ ] Frontend builds: `cd frontend && npm run build`
- [ ] Coverage maintained above 75% for both frontend and backend
- [ ] No new `any` types in TypeScript
- [ ] No `print()` in Python code
- [ ] Pydantic schemas defined for new API endpoints
- [ ] New routes registered in `backend/app/main.py`

## Dev Mode

The app runs in dev mode when `ONRAMP_AZURE_TENANT_ID` is empty. In dev mode:
- Auth is mocked (no Entra ID required)
- Database uses SQLite (no Azure SQL required)
- AI responses are mocked (no Azure AI Foundry required)
- No Azure SDK calls are made

Always test in dev mode. Do not assume Azure credentials are available.

## File Locations

| What | Where |
|------|-------|
| Backend routes | `backend/app/api/routes/` |
| Backend services | `backend/app/services/` |
| Backend models | `backend/app/models/` |
| Backend schemas | `backend/app/schemas/` |
| Backend tests | `backend/tests/test_*.py` |
| Frontend pages | `frontend/src/pages/` |
| Frontend components | `frontend/src/components/` |
| Frontend API client | `frontend/src/services/api.ts` |
| Frontend tests | `frontend/src/**/*.test.{ts,tsx}` |
| Bicep modules | `infra/modules/` |
| Customer Bicep templates | `backend/app/templates/bicep/` |
