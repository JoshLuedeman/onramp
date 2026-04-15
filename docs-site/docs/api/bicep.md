# Bicep API

The Bicep API handles Infrastructure as Code generation and template management.

## Endpoints

### List Templates

```
GET /api/bicep/templates
```

Returns the available Bicep template modules.

**Response:**

```json
[
  {
    "name": "management-groups",
    "description": "Management group hierarchy",
    "category": "organization"
  },
  {
    "name": "hub-network",
    "description": "Hub virtual network with firewall",
    "category": "networking"
  },
  {
    "name": "spoke-network",
    "description": "Spoke virtual network with peering",
    "category": "networking"
  },
  {
    "name": "policy-assignments",
    "description": "Azure Policy assignments for governance",
    "category": "governance"
  }
]
```

### Preview Template

```
GET /api/bicep/templates/{name}
```

Returns the source code of a specific Bicep template.

**Path Parameters:**

| Parameter | Type   | Description   |
| --------- | ------ | ------------- |
| `name`    | string | Template name |

**Response:**

```json
{
  "name": "hub-network",
  "description": "Hub virtual network with firewall",
  "content": "targetScope = 'resourceGroup'\n\nparam location string\n...",
  "parameters": [
    {
      "name": "location",
      "type": "string",
      "description": "Azure region for deployment"
    }
  ]
}
```

### Generate Bicep

```
POST /api/bicep/generate
```

Generates Bicep templates from an architecture definition.

**Request Body:**

```json
{
  "project_id": "uuid",
  "architecture": { ... }
}
```

**Response:**

```json
{
  "files": [
    {
      "path": "main.bicep",
      "content": "targetScope = 'managementGroup'\n..."
    },
    {
      "path": "modules/hub-network.bicep",
      "content": "..."
    }
  ],
  "total_files": 8
}
```

### Download Bicep

```
POST /api/bicep/download
```

Downloads generated Bicep templates as a ZIP archive.

**Request Body:**

```json
{
  "project_id": "uuid"
}
```

**Response:** Binary ZIP file with `Content-Type: application/zip`
