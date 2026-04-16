# Compliance API

The Compliance API provides access to compliance frameworks, controls, and scoring.

## Endpoints

### List Frameworks

```
GET /api/compliance/frameworks
```

Returns all supported compliance frameworks.

**Response:**

```json
[
  {
    "id": "soc2",
    "name": "SOC 2",
    "description": "Service Organization Control 2 — trust services criteria"
  },
  {
    "id": "hipaa",
    "name": "HIPAA",
    "description": "Health Insurance Portability and Accountability Act"
  },
  {
    "id": "pci-dss",
    "name": "PCI-DSS",
    "description": "Payment Card Industry Data Security Standard"
  },
  {
    "id": "fedramp",
    "name": "FedRAMP",
    "description": "Federal Risk and Authorization Management Program"
  },
  {
    "id": "nist-800-53",
    "name": "NIST 800-53",
    "description": "NIST security and privacy controls"
  },
  {
    "id": "iso-27001",
    "name": "ISO 27001",
    "description": "International information security management standard"
  }
]
```

### Get Framework Details

```
GET /api/compliance/frameworks/{id}
```

Returns detailed information about a specific framework, including its control families.

**Path Parameters:**

| Parameter | Type   | Description    |
| --------- | ------ | -------------- |
| `id`      | string | Framework ID   |

**Response:**

```json
{
  "id": "soc2",
  "name": "SOC 2",
  "description": "...",
  "control_families": [
    {
      "id": "cc1",
      "name": "Control Environment",
      "controls_count": 5
    }
  ]
}
```

### Get Controls

```
POST /api/compliance/controls
```

Returns the specific controls for selected frameworks.

**Request Body:**

```json
{
  "framework_ids": ["soc2", "hipaa"]
}
```

**Response:**

```json
{
  "controls": [
    {
      "id": "soc2-cc1.1",
      "framework": "soc2",
      "family": "Control Environment",
      "description": "The entity demonstrates a commitment to integrity and ethical values.",
      "azure_services": ["Azure Policy", "Microsoft Defender for Cloud"]
    }
  ]
}
```

### Evaluate Compliance

```
POST /api/scoring/evaluate
```

Scores an architecture against selected compliance frameworks.

**Request Body:**

```json
{
  "project_id": "uuid",
  "architecture": { ... },
  "framework_ids": ["soc2", "hipaa"]
}
```

**Response:**

```json
{
  "overall_score": 78.5,
  "by_framework": {
    "soc2": {
      "score": 82.0,
      "controls_met": 41,
      "controls_total": 50,
      "gaps": [
        {
          "control_id": "soc2-cc6.3",
          "description": "...",
          "recommendation": "...",
          "impact": "high"
        }
      ]
    }
  }
}
```
