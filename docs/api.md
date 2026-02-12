# OnRamp API Reference

Base URL: `/api`

## Authentication

All endpoints require Entra ID authentication via Bearer token. In development mode, a mock user is automatically provided.

## Endpoints

### Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |

### Users
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/users/me` | Get current user profile |
| GET | `/api/users/me/projects` | List user's projects |

### Questionnaire
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/questionnaire/categories` | List question categories |
| GET | `/api/questionnaire/questions` | List all questions |
| POST | `/api/questionnaire/next` | Get next unanswered question |
| POST | `/api/questionnaire/validate` | Validate an answer |
| POST | `/api/questionnaire/progress` | Get completion progress |

### Architecture
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/architecture/archetypes` | List landing zone archetypes |
| POST | `/api/architecture/generate` | Generate architecture from answers |
| POST | `/api/architecture/recommend` | Get AI recommendations |

### Compliance
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/compliance/frameworks` | List compliance frameworks |
| GET | `/api/compliance/frameworks/{id}` | Get framework details |
| POST | `/api/compliance/controls` | Get controls for frameworks |

### Scoring
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/scoring/evaluate` | Score architecture against frameworks |

### Bicep
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/bicep/templates` | List Bicep templates |
| GET | `/api/bicep/templates/{name}` | Preview a template |
| POST | `/api/bicep/generate` | Generate Bicep from architecture |
| POST | `/api/bicep/download` | Download generated Bicep |

### Deployment
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/deployment/validate` | Validate subscription |
| POST | `/api/deployment/create` | Create deployment plan |
| POST | `/api/deployment/{id}/start` | Start deployment |
| GET | `/api/deployment/{id}` | Get deployment status |
| POST | `/api/deployment/{id}/rollback` | Rollback deployment |
| GET | `/api/deployment/{id}/audit` | Get audit log |
| GET | `/api/deployment/` | List deployments |
