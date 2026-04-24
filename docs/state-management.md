# State Management

How workflow state, progress, and artifacts are tracked in the OnRamp Teamwork system.

## Overview

The Teamwork system tracks state across multiple layers: SQL databases for operational task tracking, plan files for prose-based context, checkpoints for session recovery, session artifacts for intermediate results, and Git branches for code-level state. Each layer serves a distinct purpose, and together they provide full traceability from a human goal to merged code.

## SQL Todo Tracking

### Purpose

SQL-based todo tracking is used for operational data during agent sessions — task lists, dependency tracking, test case management, and batch item processing. It provides queryable, structured state that agents can update incrementally as they work.

### Pre-Built Tables

Every agent session has access to pre-built tables:

```sql
-- Task tracking
CREATE TABLE todos (
    id TEXT PRIMARY KEY,       -- Descriptive kebab-case ID (e.g., 'user-auth')
    title TEXT NOT NULL,
    description TEXT,          -- Detailed enough to execute without external context
    status TEXT DEFAULT 'pending',  -- pending | in_progress | done | blocked
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Dependency tracking
CREATE TABLE todo_deps (
    todo_id TEXT,
    depends_on TEXT,
    PRIMARY KEY (todo_id, depends_on)
);
```

### Usage Conventions

**Descriptive IDs:** Use kebab-case identifiers that describe the work, not generic labels:

```sql
-- Good
INSERT INTO todos (id, title, description) VALUES
  ('user-auth', 'Create user auth module',
   'Implement JWT auth in src/auth/ with bcrypt password hashing.');

-- Bad
INSERT INTO todos (id, title) VALUES ('t1', 'Auth');
```

**Status workflow:** Agents update status as they work:

```sql
-- Before starting
UPDATE todos SET status = 'in_progress' WHERE id = 'user-auth';

-- After completing
UPDATE todos SET status = 'done' WHERE id = 'user-auth';

-- When blocked
UPDATE todos SET status = 'blocked',
    description = description || ' BLOCKED: waiting on API schema decision'
WHERE id = 'user-auth';
```

**Dependency queries:** Find tasks that are ready to work on (no pending dependencies):

```sql
SELECT t.* FROM todos t
WHERE t.status = 'pending'
AND NOT EXISTS (
    SELECT 1 FROM todo_deps td
    JOIN todos dep ON td.depends_on = dep.id
    WHERE td.todo_id = t.id AND dep.status != 'done'
);
```

### Additional Table Patterns

Agents can create custom tables as needed:

| Pattern | Use Case | Example |
|---------|----------|---------|
| **Test case tracking** | TDD workflows | `test_cases (id, name, status)` — status: `not_written`, `written`, `passing` |
| **Batch processing** | PR comments, file migrations | `review_items (id, file_path, comment, status)` |
| **Session state** | Key-value store | `session_state (key, value)` for tracking phase, config |

## Plan File Conventions

### Purpose

Plan files (`plan.md`) are used for prose content — problem statements, approach notes, high-level planning, and design rationale. They complement SQL tables: SQL stores structured operational data, plan files store unstructured reasoning.

### When to Use

| Content Type | Use Plan File | Use SQL |
|-------------|---------------|---------|
| Problem statement | ✅ | ❌ |
| Approach notes and tradeoffs | ✅ | ❌ |
| High-level design sketch | ✅ | ❌ |
| Task list with statuses | ❌ | ✅ |
| Dependency graph | ❌ | ✅ |
| Test case tracking | ❌ | ✅ |
| Batch item processing | ❌ | ✅ |

### Format

Plan files use standard Markdown with clear section headings:

```markdown
# Plan: <Feature or Task Name>

## Problem
What we're solving and why.

## Approach
How we're solving it, including key decisions and tradeoffs.

## Out of Scope
What we're explicitly not doing in this task.

## Open Questions
Unresolved items that may need human input.
```

## Checkpoint System

### Purpose

Checkpoints capture snapshots of workflow progress at significant moments, enabling session recovery and providing observability into long-running agent work.

### When Checkpoints Are Created

- After each workflow step completes and the handoff is validated
- After significant sub-tasks within a step (e.g., after implementing each task in a multi-task feature)
- Before and after risky operations (e.g., large refactors, database migrations)

### Checkpoint Content

Each checkpoint includes:

| Field | Description |
|-------|-------------|
| **Title** | Short description of what was just completed |
| **Overview** | Summary of the current state and what comes next |
| **Timestamp** | When the checkpoint was created |
| **Session ID** | Links the checkpoint to the originating session |

### Recovery

If a session is interrupted, checkpoints allow the next session to:

1. Identify where the workflow was when it stopped
2. Understand what has been completed and what remains
3. Resume from the last validated checkpoint instead of starting over

## Session Artifacts

### Purpose

Session artifacts are intermediate files produced during agent work — generated code, analysis results, configuration files, and other outputs that may be needed by subsequent steps.

### Storage

Artifacts are stored in context-appropriate locations:

| Artifact Type | Location |
|--------------|----------|
| Workflow state files | `.teamwork/state/<workflow-id>.yaml` |
| Handoff artifacts | `.teamwork/handoffs/<workflow-id>/` |
| Metrics and logs | `.teamwork/metrics/` |
| Memory entries | `.teamwork/memory/` |
| Architecture decisions | `docs/decisions/` |
| Generated code | Standard project directories (`backend/`, `frontend/`, `infra/`) |

### Memory System

The `.teamwork/memory/` directory stores learned facts about the codebase:

| File | Purpose |
|------|---------|
| `index.yaml` | Master index of all memory entries |
| `patterns.yaml` | Recurring patterns observed in the codebase |
| `antipatterns.yaml` | Patterns to avoid (with reasons) |
| `decisions.yaml` | Key technical decisions and their rationale |
| `feedback.yaml` | Human feedback on agent behavior |

Memory entries are:
- **Accumulated over time** as agents work and learn about the codebase
- **Synced to `MEMORY.md`** when configured (`memory.sync_to_memory_md: true` in config)
- **Archived** when the entry count exceeds the threshold (`memory.archive_threshold: 50`)
- **Votable** — agents can upvote useful memories and downvote outdated ones

## Git Branch State

### Purpose

Git branches track the code-level state of work in progress. Branch conventions ensure that multiple agents and humans can work concurrently without confusion.

### Branch Naming Conventions

Branches follow prefixed, lowercase kebab-case naming:

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feat/` or `feature/` | New functionality | `feat/questionnaire-scoring` |
| `fix/` or `bugfix/` | Bug fixes | `fix/token-expiry-handling` |
| `refactor/` | Code restructuring | `refactor/service-layer-cleanup` |
| `docs/` | Documentation changes | `docs/api-reference-update` |
| `chore/` | Tooling, dependencies, CI | `chore/upgrade-vite-7` |

### Branch Lifecycle

1. **Create** — Branch from `main` (or the appropriate base branch) with a descriptive name.
2. **Implement** — Agents commit work incrementally using selective staging (`git add <specific-files>`).
3. **Push** — Push to the remote for CI checks and PR creation.
4. **Review** — The PR goes through the workflow steps (test, security, review).
5. **Merge** — After approval, the human merges the PR.
6. **Clean up** — The branch is deleted after merge.

### Parallel Branch Safety

When multiple agents work on the same branch:

- **Selective staging is mandatory.** Use `git add <specific-files>` — never `git add .` or `git add -A`.
- **Sequential dispatch** is safest when changes overlap in the same files.
- **Separate branches** provide full isolation when required, with the Orchestrator merging them.

### Commit Conventions

All commits follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`

## State Flow Diagram

The following shows how state flows through a typical workflow:

```
Human Goal
    ↓
┌─────────────────────────┐
│  Orchestrator            │
│  Creates state file      │──→ .teamwork/state/<id>.yaml
│  Dispatches first role   │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│  Agent (e.g., Planner)   │
│  Reads state + context   │
│  Updates SQL todos       │──→ Session SQL database
│  Produces handoff        │──→ .teamwork/handoffs/<id>/
│  Creates checkpoint      │──→ Session checkpoint
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│  Orchestrator            │
│  Validates handoff       │
│  Updates state file      │──→ .teamwork/state/<id>.yaml
│  Logs metrics            │──→ .teamwork/metrics/
│  Dispatches next role    │
└─────────────────────────┘
    ↓
   ... (repeat for each step)
    ↓
┌─────────────────────────┐
│  Orchestrator            │
│  All gates passed        │
│  State → completed       │──→ .teamwork/state/<id>.yaml (final)
│  Final metrics logged    │──→ .teamwork/metrics/
└─────────────────────────┘
```

## Related Documentation

- [Agent Lifecycle](agent-lifecycle.md) — How agents are created, modified, and retired
- [Handoff Protocol](handoff-protocol.md) — How work flows between agents
- [Conventions](conventions.md) — Coding and process standards
- [Secrets Policy](secrets-policy.md) — How secrets and credentials are handled
