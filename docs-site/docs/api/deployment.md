# Deployment API

The Deployment API orchestrates deploying Bicep templates to Azure subscriptions with validation, tracking, and rollback.

## Endpoints

### Validate Subscription

```
POST /api/deployment/validate
```

Validates that a subscription is ready for deployment (permissions, quotas, policies).

**Request Body:**

```json
{
  "subscription_id": "uuid",
  "project_id": "uuid"
}
```

**Response:**

```json
{
  "valid": true,
  "checks": {
    "permissions": { "passed": true },
    "quotas": { "passed": true },
    "policies": { "passed": true, "warnings": [] }
  }
}
```

### Create Deployment Plan

```
POST /api/deployment/create
```

Creates a deployment plan showing what resources will be created.

**Request Body:**

```json
{
  "project_id": "uuid",
  "subscription_id": "uuid"
}
```

**Response:**

```json
{
  "deployment_id": "uuid",
  "status": "planned",
  "resources": [
    {
      "type": "Microsoft.Management/managementGroups",
      "name": "mg-onramp-root",
      "action": "create"
    }
  ],
  "estimated_duration_minutes": 15
}
```

### Start Deployment

```
POST /api/deployment/{id}/start
```

Starts executing a planned deployment.

**Path Parameters:**

| Parameter | Type   | Description   |
| --------- | ------ | ------------- |
| `id`      | string | Deployment ID |

**Response:**

```json
{
  "deployment_id": "uuid",
  "status": "in_progress",
  "started_at": "2024-01-15T10:30:00Z"
}
```

### Get Deployment Status

```
GET /api/deployment/{id}
```

Returns the current status and progress of a deployment.

**Response:**

```json
{
  "deployment_id": "uuid",
  "status": "in_progress",
  "progress": 65.0,
  "resources_completed": 8,
  "resources_total": 12,
  "current_step": "Deploying spoke network...",
  "started_at": "2024-01-15T10:30:00Z"
}
```

### Rollback Deployment

```
POST /api/deployment/{id}/rollback
```

Initiates a rollback of a completed or failed deployment.

**Response:**

```json
{
  "deployment_id": "uuid",
  "status": "rolling_back",
  "rollback_started_at": "2024-01-15T11:00:00Z"
}
```

### Get Audit Log

```
GET /api/deployment/{id}/audit
```

Returns the full audit log for a deployment.

**Response:**

```json
{
  "deployment_id": "uuid",
  "entries": [
    {
      "timestamp": "2024-01-15T10:30:00Z",
      "action": "deployment_started",
      "user": "user@example.com",
      "details": "Deployment initiated for project 'Landing Zone'"
    }
  ]
}
```

### List Deployments

```
GET /api/deployment/
```

Returns all deployments for the current user.

**Response:**

```json
[
  {
    "deployment_id": "uuid",
    "project_name": "Landing Zone",
    "status": "completed",
    "created_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:45:00Z"
  }
]
```
