# Projects API

The Projects API manages user projects that track the full workflow from questionnaire through deployment.

## Endpoints

### List User Projects

```
GET /api/users/me/projects
```

Returns all projects for the authenticated user.

**Response:**

```json
[
  {
    "id": "uuid",
    "name": "Production Landing Zone",
    "status": "architecture_generated",
    "created_at": "2024-01-10T09:00:00Z",
    "updated_at": "2024-01-15T14:30:00Z"
  }
]
```

## Project Lifecycle

A project moves through the following statuses:

| Status                    | Description                                    |
| ------------------------- | ---------------------------------------------- |
| `questionnaire_started`   | User has begun answering questions              |
| `questionnaire_completed` | All required questions answered                 |
| `architecture_generated`  | Landing zone architecture has been generated    |
| `compliance_scored`       | Architecture has been scored against frameworks |
| `bicep_generated`         | Bicep templates have been generated             |
| `deployment_planned`      | Deployment plan created and ready               |
| `deployment_in_progress`  | Deployment is actively running                  |
| `deployment_completed`    | Deployment finished successfully                |
| `deployment_failed`       | Deployment encountered an error                 |
| `deployment_rolled_back`  | Deployment was rolled back                      |

## User Profile

### Get Current User

```
GET /api/users/me
```

Returns the authenticated user's profile.

**Response:**

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "Jane Doe",
  "role": "architect",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Roles

| Role       | Permissions                                    |
| ---------- | ---------------------------------------------- |
| `admin`    | Full access to all features and user management |
| `architect`| Create and manage projects, deploy              |
| `viewer`   | View projects and architectures (read-only)     |
