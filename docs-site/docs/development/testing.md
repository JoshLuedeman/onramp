# Testing Guide

OnRamp maintains quality through automated testing on both the backend and frontend, enforced via CI.

## Backend Testing

The backend uses [pytest](https://docs.pytest.org/) for testing.

### Running Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

### With Coverage

```bash
cd backend
pytest tests/ -v --cov=app --cov-fail-under=75
```

### Coverage Requirements

- **Minimum coverage: 75%** — enforced in CI
- Coverage is measured against the `app/` package
- All new code should include corresponding tests

### Test Structure

```
backend/
└── tests/
    ├── conftest.py          # Shared fixtures
    ├── test_health.py       # Health endpoint tests
    ├── test_questionnaire.py # Questionnaire API tests
    ├── test_architecture.py  # Architecture API tests
    ├── test_compliance.py    # Compliance API tests
    ├── test_bicep.py         # Bicep API tests
    └── test_deployment.py    # Deployment API tests
```

### Writing Tests

Use FastAPI's `TestClient` for endpoint testing:

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
```

## Frontend Testing

The frontend uses [Vitest](https://vitest.dev/) for testing.

### Running Tests

```bash
cd frontend
npm run test
```

### With Coverage

```bash
cd frontend
npm run test:coverage
```

### Coverage Requirements

- **Minimum coverage: 75%** — enforced in CI
- All new components should include corresponding tests

## CI Pipeline

The CI pipeline runs on every pull request and push to `main`:

1. **Lint** — `ruff check app/` (backend), `npm run lint` (frontend)
2. **Test** — `pytest` (backend), `vitest` (frontend)
3. **Build** — `npm run build` (frontend)
4. **Coverage** — Fails if below 75% on either backend or frontend

### Running CI Checks Locally

Before opening a PR, run the same checks CI will run:

```bash
# Backend
cd backend
ruff check app/
pytest tests/ -v --cov=app --cov-fail-under=75

# Frontend
cd frontend
npm run lint
npm run test:coverage
npm run build
```
