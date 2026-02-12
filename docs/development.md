# OnRamp Development Guide

## Prerequisites

- Python 3.10+
- Node.js 18+
- Git

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server proxies API requests to `http://localhost:8000`.

## Development Mode

When `ONRAMP_AZURE_TENANT_ID` is not set, the application runs in development mode:
- Authentication returns a mock user (no Entra ID required)
- AI calls return mock architecture responses
- Deployment validation simulates success

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ONRAMP_AZURE_TENANT_ID` | Entra ID tenant | Production |
| `ONRAMP_AZURE_CLIENT_ID` | App registration client ID | Production |
| `ONRAMP_AI_FOUNDRY_ENDPOINT` | Azure AI Foundry endpoint | Production |
| `ONRAMP_AI_FOUNDRY_KEY` | AI Foundry API key | Production |
| `ONRAMP_DATABASE_URL` | SQL connection string | Production |
| `ONRAMP_CORS_ORIGINS` | Allowed CORS origins | Optional |

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

## Project Structure

```
onramp/
├── frontend/          # React + Fluent UI v9
├── backend/           # Python FastAPI
│   ├── app/
│   │   ├── api/routes/    # API endpoints
│   │   ├── auth/          # Entra ID auth
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   └── templates/     # Bicep templates
│   └── tests/
├── infra/             # Bicep infrastructure
└── docs/              # Documentation
```
