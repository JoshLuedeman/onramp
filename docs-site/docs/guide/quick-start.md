# Quick Start

Get OnRamp running locally in minutes using Docker.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

## Start OnRamp

Run a single command from the project root:

```bash
./dev.sh
```

This builds and starts everything in containers:

| Service  | URL                          | Hot Reload? |
| -------- | ---------------------------- | ----------- |
| Frontend | http://localhost:5173         | ✅ Edit `frontend/src/` |
| Backend  | http://localhost:8000         | ✅ Edit `backend/app/` |
| API Docs | http://localhost:8000/docs    | —           |

## Development Mode

When `ONRAMP_AZURE_TENANT_ID` is not set, the application runs in **development mode**:

- Authentication returns a mock user (no Entra ID required)
- AI calls return mock architecture responses
- Deployment validation simulates success

This means you can explore the full workflow without any Azure credentials.

## Dev Script Commands

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

If you prefer to run services directly:

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install && npm run dev
```

Visit `http://localhost:5173` — the app runs in development mode with mock data.

## Next Steps

- [Questionnaire Guide](./questionnaire) — Walk through the adaptive questionnaire
- [Architecture Guide](./architecture) — Understand architecture generation
- [API Reference](/api/) — Explore the REST API
