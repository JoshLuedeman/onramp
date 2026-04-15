# API Reference

OnRamp exposes a RESTful API built with [FastAPI](https://fastapi.tiangolo.com/). All endpoints are prefixed with `/api` and return JSON responses.

**Base URL:** `/api`

## Authentication

All endpoints require Entra ID authentication via Bearer token. Include the token in the `Authorization` header:

```
Authorization: Bearer <token>
```

In development mode (when `ONRAMP_AZURE_TENANT_ID` is not set), a mock user is automatically provided — no token required.

## Interactive Docs

When running locally, FastAPI's auto-generated interactive API docs are available at:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Endpoint Groups

### Health

| Method | Path      | Description  |
| ------ | --------- | ------------ |
| GET    | `/health` | Health check |

### Users

| Method | Path                    | Description             |
| ------ | ----------------------- | ----------------------- |
| GET    | `/api/users/me`         | Get current user profile |
| GET    | `/api/users/me/projects`| List user's projects    |

### [Questionnaire](/api/questionnaire)

Adaptive questionnaire for CAF design areas.

### [Architecture](/api/architecture)

Architecture generation and AI recommendations.

### [Compliance](/api/compliance)

Compliance frameworks and scoring.

### [Bicep](/api/bicep)

Bicep template generation and downloads.

### [Deployment](/api/deployment)

Deployment orchestration, validation, and rollback.

### [Projects](/api/projects)

Project management and state tracking.

## Error Responses

All endpoints return standard HTTP error codes with JSON error bodies:

```json
{
  "detail": "Description of what went wrong"
}
```

Common error codes:

| Code | Meaning               |
| ---- | --------------------- |
| 400  | Bad Request           |
| 401  | Unauthorized          |
| 403  | Forbidden             |
| 404  | Not Found             |
| 422  | Validation Error      |
| 500  | Internal Server Error |
