# 🚀 OnRamp — Azure Landing Zone Architect & Deployer

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2FYOUR-GITHUB-ORG%2Fonramp%2Fmain%2Finfra%2Fazuredeploy.json)

**OnRamp** is an AI-powered web application that guides Azure customers through designing and deploying Cloud Adoption Framework (CAF) aligned landing zones. Answer questions about your organization, get an AI-generated architecture recommendation, review it visually, and deploy it to Azure with a single click.

## ✨ Features

- **🧭 Guided Questionnaire** — Adaptive wizard covering all 8 CAF design areas
- **🤖 AI Architecture Generation** — Azure AI Foundry powered architecture recommendations
- **🏗️ Interactive Visualizer** — Explore your landing zone hierarchy and network topology
- **📋 Compliance Scoring** — Evaluate against SOC 2, HIPAA, PCI-DSS, FedRAMP, NIST 800-53, ISO 27001
- **📝 Bicep Generation** — Auto-generated, deployable Infrastructure as Code
- **🚀 One-Click Deploy** — Deploy your entire landing zone to Azure subscriptions
- **📊 Deployment Tracking** — Real-time progress, audit logging, and rollback support

## 🏛️ Architecture

```
React + Fluent UI v9  →  FastAPI (Python)  →  Azure SQL
                                           →  Azure AI Foundry
                                           →  Customer Subscriptions (Bicep)
```

Hosted on **Azure Container Apps** with **Entra ID** authentication.

## 🚀 Quick Start

### Prerequisites
- Docker Desktop

### One Command Start
```bash
./dev.sh
```

That's it. This builds and starts everything in containers:
- **Frontend** at `http://localhost:5173` (hot reload)
- **Backend** at `http://localhost:8000` (auto-restart)
- **API Docs** at `http://localhost:8000/docs`

Other commands:
```bash
./dev.sh logs     # Tail logs
./dev.sh test     # Run backend tests
./dev.sh shell    # Backend shell
./dev.sh down     # Stop everything
./dev.sh reset    # Wipe DB and rebuild
```

### Without Docker (manual)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```
```bash
cd frontend
npm install && npm run dev
```

Visit `http://localhost:5173` — the app runs in development mode with mock data.

## 🧪 Testing

```bash
cd backend && source .venv/bin/activate
pytest tests/ -v
```

## 📁 Project Structure

```
onramp/
├── frontend/       # React + TypeScript + Fluent UI v9
├── backend/        # Python FastAPI
├── infra/          # Bicep templates (OnRamp infrastructure)
├── docs/           # Architecture, API, and dev docs
└── .github/        # CI/CD workflows
```

## 📖 Documentation

- [Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [Development Guide](docs/development.md)

## 🏗️ Landing Zone Archetypes

| Size | Employees | Subscriptions | Use Case |
|------|-----------|---------------|----------|
| Small | 1-50 | 2-3 | Startups, small teams |
| Medium | 51-500 | 4-6 | Growing businesses |
| Enterprise | 500+ | 8+ | Large organizations |

## 🔒 Security

- Microsoft Entra ID (Azure AD) authentication
- Role-based access control (Admin, Architect, Viewer)
- Azure Key Vault for secrets
- All deployments audited

## 📜 License

MIT
