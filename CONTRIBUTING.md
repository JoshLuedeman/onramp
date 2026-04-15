# Contributing to OnRamp

Thank you for your interest in contributing to OnRamp! This guide will help you get started.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (recommended)
- OR: Python 3.12+ and Node.js 18+ for manual setup

## Development Setup

The fastest way to get started:

```bash
./dev.sh up
```

This builds and starts everything in containers:

| Service  | URL                          | Hot Reload |
|----------|------------------------------|------------|
| Frontend | http://localhost:5173        | ✅         |
| Backend  | http://localhost:8000        | ✅         |
| API Docs | http://localhost:8000/docs   | —          |

For detailed setup options, see [docs/development.md](docs/development.md).

## Running Tests

### Backend

```bash
cd backend && pytest tests/ -v
```

With coverage:

```bash
cd backend && pytest tests/ -v --cov=app --cov-fail-under=75
```

### Frontend

```bash
cd frontend && npm run test:coverage
```

## Linting

### Backend

```bash
cd backend && ruff check app/
```

### Frontend

```bash
cd frontend && npm run lint
```

## Coding Standards

### Python (Backend)

- Use `snake_case` for functions, variables, and modules
- All database operations must be `async`
- Use Pydantic schemas for all API request/response models
- No `print()` — use `logging` instead
- Type hints on all function signatures

### TypeScript (Frontend)

- Use `PascalCase` for React components
- Use `camelCase` for functions and variables
- No `any` types — always define proper types
- Use **Fluent UI React v9** exclusively for UI components — no other UI libraries

### General

- Every public function should have a doc comment
- Inline comments explain **why**, not **what**
- Keep nesting shallow — three levels deep maximum

## Branch Naming

Use prefixed branch names with lowercase kebab-case:

- `feat/<short-description>` — new functionality
- `fix/<short-description>` — bug fixes
- `docs/<short-description>` — documentation-only changes
- `refactor/<short-description>` — restructuring without behavior change

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`

- Keep the summary under 72 characters
- Use imperative mood: "add feature" not "added feature"
- Reference issues: `fix(auth): handle expired tokens (#42)`

## Pull Request Process

1. Create a branch from `main` following the naming convention above
2. Make your changes, keeping them minimal and focused
3. Write or update tests for any behavioral changes
4. Ensure all checks pass locally:
   - `cd backend && ruff check app/` (lint)
   - `cd backend && pytest tests/ -v` (tests)
   - `cd frontend && npm run lint` (lint)
   - `cd frontend && npm run test:coverage` (tests)
   - `cd frontend && npm run build` (build)
5. Open a PR with a clear title in Conventional Commit format
6. Reference the related issue using `Closes #<number>`
7. Fill out the PR template completely
8. Wait for CI to pass and a reviewer to approve

## How to Contribute Content

### Adding Questionnaire Questions

Questions are managed as seed data. Add new questions to:

```
backend/app/db/seed.py
```

Follow the existing question format, ensuring each question is assigned to one of the 8 CAF design areas.

### Adding Compliance Frameworks

Compliance scoring logic lives in:

```
backend/app/services/compliance_scorer.py
```

Add new framework definitions following the existing pattern for SOC 2, HIPAA, PCI-DSS, etc.

### Adding Bicep Templates

Landing zone Bicep templates are stored in:

```
backend/app/templates/bicep/
```

Add new `.bicep` files following the existing naming and parameterization patterns.

## Getting Help

- Check [docs/development.md](docs/development.md) for detailed development setup
- Check [docs/architecture.md](docs/architecture.md) for system design
- Check [docs/api.md](docs/api.md) for API reference
- Open an issue if you're stuck — we're happy to help!
