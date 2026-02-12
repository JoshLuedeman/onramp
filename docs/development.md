# OnRamp Development Guide

## Prerequisites

- Docker Desktop (recommended)
- OR: Python 3.10+ and Node.js 18+ (manual setup)

## Quick Start (Recommended)

```bash
./dev.sh
```

This single command:
1. Builds the backend and frontend containers
2. Starts everything with hot reload
3. Waits for services to be healthy
4. Prints the URLs

| Service | URL | Hot Reload? |
|---------|-----|-------------|
| Frontend | http://localhost:5173 | ✅ Edit `frontend/src/` |
| Backend | http://localhost:8000 | ✅ Edit `backend/app/` |
| API Docs | http://localhost:8000/docs | — |

### Dev Script Commands

```bash
./dev.sh          # Start everything
./dev.sh down     # Stop everything
./dev.sh reset    # Wipe DB, rebuild from scratch
./dev.sh logs     # Tail all logs
./dev.sh test     # Run backend tests in container
./dev.sh status   # Show running containers + health
./dev.sh shell    # Open bash in backend container
```

## Manual Setup (Without Docker)

### Docker Compose (Full Stack)

```bash
# Start all services (SQL Server, Backend, Frontend)
docker compose up -d

# View logs
docker compose logs -f backend

# Stop everything
docker compose down

# Reset database
docker compose down -v
```

The Docker setup includes:
- **SQL Server 2022** Developer Edition on port 1433
- **FastAPI backend** on port 8000 (with hot reload)
- **React frontend** on port 5173 (with HMR)

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
