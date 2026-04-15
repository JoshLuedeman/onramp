# Questionnaire API

The Questionnaire API provides access to OnRamp's adaptive questionnaire that covers all 8 Cloud Adoption Framework design areas.

## Endpoints

### List Categories

```
GET /api/questionnaire/categories
```

Returns the list of questionnaire categories (CAF design areas).

**Response:**

```json
[
  {
    "id": "billing",
    "name": "Azure Billing & Entra Tenant",
    "description": "Subscription structure and tenant configuration",
    "order": 1
  }
]
```

### List All Questions

```
GET /api/questionnaire/questions
```

Returns all questions across all categories.

**Response:**

```json
[
  {
    "id": "org-size",
    "category": "billing",
    "text": "What is your organization size?",
    "type": "single-select",
    "options": [
      { "value": "small", "label": "1-50 employees", "recommended": false },
      { "value": "medium", "label": "51-500 employees", "recommended": false },
      { "value": "enterprise", "label": "500+ employees", "recommended": false }
    ]
  }
]
```

### Get Next Question

```
POST /api/questionnaire/next
```

Returns the next unanswered question based on current progress and adaptive logic.

**Request Body:**

```json
{
  "project_id": "uuid",
  "answers": {
    "org-size": "medium"
  }
}
```

**Response:**

```json
{
  "question": { ... },
  "progress": 0.25
}
```

### Validate Answer

```
POST /api/questionnaire/validate
```

Validates a single answer before saving.

**Request Body:**

```json
{
  "question_id": "org-size",
  "value": "medium"
}
```

**Response:**

```json
{
  "valid": true,
  "message": null
}
```

### Get Progress

```
POST /api/questionnaire/progress
```

Returns the current completion progress for a set of answers.

**Request Body:**

```json
{
  "project_id": "uuid",
  "answers": { ... }
}
```

**Response:**

```json
{
  "total_questions": 24,
  "answered": 8,
  "percentage": 33.3,
  "by_category": {
    "billing": { "total": 3, "answered": 3, "complete": true },
    "identity": { "total": 4, "answered": 2, "complete": false }
  }
}
```
