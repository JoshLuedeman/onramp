---
applyTo: "backend/**"
---

# Backend Instructions (Python + FastAPI)

## Framework Rules

- Use Python 3.12+ with FastAPI.
- All I/O operations MUST be async (`async`/`await`). Never use synchronous DB calls or blocking I/O.
- Use Pydantic v2 models for all request/response validation. Define in `app/schemas/`.
- Use SQLAlchemy 2.0 async ORM for all database operations. Models in `app/models/`.
- Use `logging.getLogger(__name__)` for logging. Never use `print()` in production code.

## Architecture

- **Routes** go in `app/api/routes/`. Register in `main.py` via `app.include_router()`.
- **Services** are singleton instances at module level in `app/services/`. Import where needed.
- **Models** are SQLAlchemy ORM classes in `app/models/`. Inherit from `Base`.
- **Schemas** are Pydantic models in `app/schemas/`. Use for API input/output validation.
- **Dependencies** go in `app/api/dependencies.py`. Use FastAPI `Depends()` injection.

## Configuration

- All environment variables use the `ONRAMP_` prefix.
- Managed through `app/config.py` (Pydantic BaseSettings).
- List-type env vars (e.g., `ONRAMP_CORS_ORIGINS`) must be JSON array format: `'["http://localhost:5173"]'`.
- Access config via `from app.config import settings`.

## Error Handling

- Raise `HTTPException` with appropriate status codes in route handlers.
- Services should raise domain-specific exceptions, not HTTPException.
- Never silently swallow exceptions.

## Coding Style

- Line length: 100 characters max (enforced by Ruff).
- Import ordering: stdlib → third-party → local (enforced by Ruff isort).
- Ruff rules: E, F, I, N, W, UP.
- Use Google-style docstrings for all public functions and classes.

## Database

- Dev mode uses `aiosqlite` (SQLite). Production uses `aioodbc` (Azure SQL).
- Always create Alembic migrations for schema changes: `alembic revision --autogenerate -m "description"`.
- Seed data in `app/db/seed.py` is idempotent — checks row count before inserting.
- Use `get_db` FastAPI dependency for database sessions.

## Dev Mode vs Production Mode

- When `ONRAMP_AZURE_TENANT_ID` is empty → dev mode: mock auth, SQLite, mock AI, no Azure SDK.
- When set → production mode: Entra ID auth, Azure SQL, real AI Foundry, real deployments.
- Always ensure code works in both modes. Use `if settings.azure_tenant_id:` to branch.

## Testing (MANDATORY)

- Framework: pytest + pytest-asyncio + httpx AsyncClient
- Config: `asyncio_mode = "auto"` in `pyproject.toml`
- Coverage: pytest-cov, minimum 75% line coverage enforced in CI
- Every new route MUST have a test file: `tests/test_<module>.py`
- Every new service MUST have corresponding tests
- Run: `pytest tests/ -v` or `pytest tests/ -v --cov=app --cov-fail-under=75`

### Test Pattern

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/endpoint")
        assert response.status_code == 200
```

### Testing Gotchas

- `use_ai: False` alone does not fall back to archetypes. Also pass `use_archetype: True`.
- Tests run against SQLite (dev mode). Do not assume Azure SQL features.
- Mock external services (Azure SDK, AI Foundry) in tests. Never make real API calls.

## Adding a New Route

1. Create `app/schemas/<feature>.py` with Pydantic request/response models
2. Create `app/services/<feature>.py` with business logic (singleton instance)
3. Create `app/api/routes/<feature>.py` with FastAPI router
4. Register router in `app/main.py`: `app.include_router(feature_router)`
5. Create `tests/test_<feature>.py` with route and service tests
6. If DB models needed: create in `app/models/`, run `alembic revision --autogenerate`
