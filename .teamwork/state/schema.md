# Workflow State Validation Schema

This document defines the schema for workflow state files stored in `.teamwork/state/`.
All state files must conform to this schema to ensure consistency, enable corruption
detection, and support automated recovery.

## YAML Schema Definition

```yaml
# .teamwork/state/<workflow-id>.yaml
# All fields marked [required] must be present. Fields marked [optional] may be omitted.

id: string                    # [required] Unique workflow identifier (e.g., "feat-wizard-back-button-a1b2")
workflow: string              # [required] Skill name that created this state (e.g., "feature-workflow")
status: string                # [required] Current workflow status (see Valid Status Values)
created_at: string            # [required] ISO 8601 timestamp of workflow creation (e.g., "2025-01-15T10:30:00Z")
updated_at: string            # [required] ISO 8601 timestamp of last state change (e.g., "2025-01-15T14:22:00Z")
trigger: string               # [required] Description of what initiated the workflow
branch: string                # [optional] Git branch associated with this workflow
pr_number: integer            # [optional] GitHub PR number if a PR exists
milestone: string             # [optional] Associated GitHub milestone name

current_step: integer         # [required] Index of the current active step (0-based)
current_role: string          # [required] Role executing the current step

steps:                        # [required] Array of step status objects
  - step: integer             # [required] Step index (0-based, matches workflow step #)
    role: string              # [required] Role responsible for this step
    status: string            # [required] Step status: pending | in_progress | completed | failed | skipped
    started_at: string        # [optional] ISO 8601 timestamp when step began
    completed_at: string      # [optional] ISO 8601 timestamp when step finished
    output_ref: string        # [optional] Path to handoff artifact (e.g., ".teamwork/handoffs/<id>/step-4.md")
    failure_reason: string    # [optional] Reason for failure (required when status is "failed")

# Corruption detection fields
checksum: string              # [required] SHA-256 hash of all fields above this line, hex-encoded
last_valid_state: string      # [required] Copy of the previous checksum before the latest update
```

## Valid Status Values

### Workflow Status (`status` field)

| Value | Description |
|-------|-------------|
| `active` | Workflow is in progress; a role is currently executing a step |
| `paused` | Workflow is temporarily suspended; waiting for external input or a dependency |
| `completed` | All steps finished successfully; workflow is done |
| `failed` | Workflow encountered an unrecoverable error; see step `failure_reason` |
| `cancelled` | Workflow was explicitly cancelled by a human or the orchestrator |

### Step Status (`steps[].status` field)

| Value | Description |
|-------|-------------|
| `pending` | Step has not started yet |
| `in_progress` | Step is currently being executed |
| `completed` | Step finished successfully; outputs are available |
| `failed` | Step failed; see `failure_reason` field |
| `skipped` | Step was intentionally skipped (e.g., UX review when no frontend changes) |

## Field Validation Rules

1. **`id`** — Must be a non-empty string. Use kebab-case with a short random suffix (e.g., `feat-auth-refactor-x7k9`). Must be unique across all active workflows.
2. **`workflow`** — Must match a skill name from `.github/skills/*/SKILL.md` (e.g., `feature-workflow`, `bugfix-workflow`).
3. **`status`** — Must be one of: `active`, `paused`, `completed`, `failed`, `cancelled`.
4. **`created_at` / `updated_at`** — Must be valid ISO 8601 timestamps in UTC. `updated_at` must be ≥ `created_at`.
5. **`current_step`** — Must be a non-negative integer within the range of the `steps` array.
6. **`steps`** — Must contain at least one entry. Step indices must be sequential starting from 0.
7. **`steps[].status`** — Must be one of: `pending`, `in_progress`, `completed`, `failed`, `skipped`.
8. **`checksum`** — Must be a valid 64-character hex string (SHA-256). Computed over all fields except `checksum` and `last_valid_state`.
9. **`last_valid_state`** — Must be a valid 64-character hex string or `"none"` for the initial state file creation.

## Status Transition Rules

### Workflow Status Transitions

```
  ┌──────────┐
  │  active   │──────────────────────────────────┐
  └────┬──────┘                                  │
       │                                         │
       ├──→ paused ──→ active (resume)           │
       │                                         │
       ├──→ completed (all steps done)           │
       │                                         │
       ├──→ failed (unrecoverable error)         │
       │                                         │
       └──→ cancelled (human or orchestrator)    │
                                                 │
  paused ──→ cancelled                           │
  failed ──→ active (retry after recovery)  ◄────┘
```

**Valid transitions:**
- `active` → `paused`, `completed`, `failed`, `cancelled`
- `paused` → `active`, `cancelled`
- `failed` → `active` (only after documented recovery)
- `completed` and `cancelled` are terminal — no transitions out

### Step Status Transitions

- `pending` → `in_progress`, `skipped`
- `in_progress` → `completed`, `failed`
- `failed` → `in_progress` (retry)
- `completed` and `skipped` are terminal for that step

## Corruption Detection

### Checksum Computation

The `checksum` field is a SHA-256 hash computed over a canonical string representation of all
state fields **except** `checksum` and `last_valid_state`. The canonical form is:

1. Serialize all fields (except `checksum` and `last_valid_state`) as sorted-key YAML
2. Normalize line endings to LF
3. Strip trailing whitespace from each line
4. Compute SHA-256 over the resulting UTF-8 bytes
5. Encode as lowercase hex

### Detecting Corruption

A state file is **corrupt** if any of the following are true:

1. **Checksum mismatch** — Recompute the checksum from the file contents; if it does not match the stored `checksum`, the file has been modified outside the workflow system.
2. **Invalid status transition** — The current status is not reachable from the previous status via valid transitions (e.g., `completed` → `active` without a `failed` intermediate).
3. **Schema violation** — Any required field is missing, has the wrong type, or contains an invalid value.
4. **Temporal inconsistency** — `updated_at` < `created_at`, or a step's `completed_at` < `started_at`.
5. **Step array inconsistency** — `current_step` points to a step whose status is not `in_progress`, or multiple steps have `in_progress` status simultaneously.

### Corruption Severity

| Severity | Condition | Impact |
|----------|-----------|--------|
| **Low** | Checksum mismatch but all fields are valid | File was hand-edited; recompute checksum |
| **Medium** | Missing optional fields or minor temporal inconsistency | Some metadata lost; workflow can continue |
| **High** | Required fields missing or invalid status values | Workflow state is unreliable; recovery needed |
| **Critical** | File is unparseable YAML or completely empty | State is lost; must reconstruct from artifacts |

## Recovery Procedures

### Procedure 1: Checksum Mismatch (Low Severity)

1. Validate all fields against the schema
2. If all fields are valid, recompute the checksum and update `last_valid_state` with the old checksum
3. Log the correction in the metrics file
4. Resume the workflow normally

### Procedure 2: Missing or Invalid Fields (Medium/High Severity)

1. Compare the current file with `last_valid_state` — if a previous valid checkpoint exists, load it
2. Cross-reference with handoff artifacts in `.teamwork/handoffs/<workflow-id>/` to determine the last completed step
3. Reconstruct the state by:
   - Setting `current_step` to the last step with a valid handoff artifact
   - Setting `status` to `active`
   - Marking completed steps based on artifact existence
   - Marking the current step as `in_progress`
4. Recompute the checksum
5. Log the recovery in the metrics file and notify the orchestrator

### Procedure 3: Unparseable or Missing File (Critical Severity)

1. Check if a backup exists in `.teamwork/state/backups/<workflow-id>.yaml`
2. If no backup, reconstruct from external sources:
   - Git branch existence confirms workflow was started
   - PR existence and status indicates progress through code steps
   - Handoff artifacts in `.teamwork/handoffs/<workflow-id>/` indicate step completion
   - Metrics log entries provide timestamps and role dispatches
3. Create a new state file from reconstructed data
4. Set `last_valid_state` to `"none"` (fresh start)
5. Compute and set the checksum
6. Set workflow status to `paused` and escalate to the human for confirmation before resuming

### Procedure 4: Preventing Corruption

- Always update state files atomically — write to a temp file, validate, then rename
- Create a backup in `.teamwork/state/backups/` before each state update
- Validate the schema after every write operation
- Never hand-edit state files — always use the orchestrator's state management functions

## Example State File

```yaml
id: feat-wizard-back-button-a1b2
workflow: feature-workflow
status: active
created_at: "2025-01-15T10:30:00Z"
updated_at: "2025-01-15T14:22:00Z"
trigger: "Feature request: Add back button to wizard questionnaire (#42)"
branch: feat/wizard-back-button
pr_number: 45
current_step: 4
current_role: Coder

steps:
  - step: 0
    role: Orchestrator
    status: completed
    started_at: "2025-01-15T10:30:00Z"
    completed_at: "2025-01-15T10:30:05Z"
  - step: 1
    role: Human
    status: completed
    started_at: "2025-01-15T10:30:05Z"
    completed_at: "2025-01-15T10:35:00Z"
  - step: 2
    role: Planner
    status: completed
    started_at: "2025-01-15T10:35:00Z"
    completed_at: "2025-01-15T11:00:00Z"
    output_ref: ".teamwork/handoffs/feat-wizard-back-button-a1b2/step-2.md"
  - step: 3
    role: Architect
    status: completed
    started_at: "2025-01-15T11:00:00Z"
    completed_at: "2025-01-15T11:30:00Z"
    output_ref: ".teamwork/handoffs/feat-wizard-back-button-a1b2/step-3.md"
  - step: 4
    role: Coder
    status: in_progress
    started_at: "2025-01-15T14:22:00Z"
  - step: 5
    role: Tester
    status: pending
  - step: 6
    role: Security Auditor
    status: pending
  - step: 7
    role: Reviewer
    status: pending
  - step: 8
    role: Human
    status: pending
  - step: 9
    role: Documenter
    status: pending
  - step: 10
    role: Orchestrator
    status: pending

checksum: "a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1"
last_valid_state: "b4c9d3e2f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2"
```
