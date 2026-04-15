# Architecture API

The Architecture API handles landing zone architecture generation and AI-powered recommendations.

## Endpoints

### List Archetypes

```
GET /api/architecture/archetypes
```

Returns the available landing zone archetypes.

**Response:**

```json
[
  {
    "id": "small",
    "name": "Small",
    "description": "For organizations with 1-50 employees",
    "subscriptions": "2-3",
    "management_groups": "Simplified hierarchy"
  },
  {
    "id": "medium",
    "name": "Medium",
    "description": "For organizations with 51-500 employees",
    "subscriptions": "4-6",
    "management_groups": "Standard CAF hierarchy"
  },
  {
    "id": "enterprise",
    "name": "Enterprise",
    "description": "For organizations with 500+ employees",
    "subscriptions": "8+",
    "management_groups": "Full enterprise-scale"
  }
]
```

### Generate Architecture

```
POST /api/architecture/generate
```

Generates a landing zone architecture based on questionnaire answers.

**Request Body:**

```json
{
  "project_id": "uuid",
  "answers": {
    "org-size": "medium",
    "compliance-frameworks": ["soc2", "hipaa"],
    "network-topology": "hub-spoke"
  }
}
```

**Response:**

```json
{
  "archetype": "medium",
  "management_groups": [...],
  "subscriptions": [...],
  "networking": {...},
  "security": {...},
  "estimated_monthly_cost": 2500.00
}
```

### Get AI Recommendations

```
POST /api/architecture/recommend
```

Uses Azure AI Foundry to generate tailored recommendations for the architecture.

**Request Body:**

```json
{
  "project_id": "uuid",
  "architecture": { ... },
  "question": "Should I use Azure Firewall or a third-party NVA?"
}
```

**Response:**

```json
{
  "recommendation": "Based on your medium-sized organization...",
  "updated_architecture": { ... }
}
```

::: tip
In development mode (without AI credentials), this endpoint returns a mock recommendation response.
:::
