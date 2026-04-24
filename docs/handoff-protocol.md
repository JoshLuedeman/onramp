# Handoff Protocol

How work flows between agents in the OnRamp Teamwork system.

## Overview

The handoff protocol defines how agents pass work to each other in a structured, validated way. Every workflow is a sequence of steps, each assigned to a role. When one agent completes its step, it produces a **handoff artifact** — a structured deliverable that the next agent needs to begin its work. The **Orchestrator** validates each handoff before dispatching the next role.

## The Orchestrator Pattern

### How It Works

The Orchestrator is the central coordinator. It does not implement, design, review, or test — it manages the workflow state machine:

```
Human Goal
    ↓
Orchestrator (initialize workflow, create state file)
    ↓
Step 1: Dispatch Role A → validate handoff artifact
    ↓
Step 2: Dispatch Role B → validate handoff artifact
    ↓
Step N: Dispatch final role → validate completion
    ↓
Orchestrator (mark workflow completed, log metrics)
```

### Orchestrator Responsibilities

1. **Initialize** — Create a state file in `.teamwork/state/` when a workflow begins.
2. **Dispatch** — Send the appropriate agent to work on the current step, providing all context from previous handoffs.
3. **Validate** — Confirm the handoff artifact exists, is well-formed, and meets the quality bar before advancing.
4. **Enforce gates** — If a quality gate fails, keep the workflow at the current step and re-dispatch with feedback.
5. **Track** — Update the state file after every transition. Log metrics for every action.
6. **Escalate** — Set the workflow to `blocked` and notify the human when intervention is required.

### What the Orchestrator Never Does

- Write application code
- Make design or architecture decisions
- Review code for correctness
- Write or run tests
- Modify documentation content (only orchestration files)

## Handoff Format and Requirements

### Handoff Artifacts

Each workflow step produces a specific artifact that the next step consumes. Artifacts are stored in `.teamwork/handoffs/<workflow-id>/` and follow the formats defined in project protocols.

### Common Artifact Types

| From → To | Artifact | Format |
|-----------|----------|--------|
| Human → Planner | Feature request or bug report | GitHub issue with goal, context, constraints |
| Planner → Architect | Task issues with acceptance criteria | GitHub issues with labels, dependency links |
| Architect → Coder | Design decisions, feasibility assessment | Comments on task issues, ADR file (if needed) |
| Coder → Tester | Pull request with code and tests | GitHub PR linked to task issues, CI passing |
| Tester → Security Auditor | Validated PR with coverage report | PR comment with coverage summary |
| Security Auditor → Reviewer | Security assessment | PR comment with findings table or "no findings" |
| Reviewer → Human | Review decision | GitHub PR review (approved or changes requested) |
| Human → Documenter | Merged code | Merged commit on target branch |
| Documenter → Orchestrator | Updated documentation | Changelog entry, corrected docs |

### Requirements for Every Handoff

1. **The artifact must exist.** The Orchestrator checks that the expected deliverable was actually produced (e.g., a PR was opened, a comment was posted, an issue was created).
2. **The artifact must be well-formed.** It follows the expected format — issues have acceptance criteria, PRs link to issues, comments include required sections.
3. **The artifact must meet the quality bar.** The deliverable satisfies the success criteria defined in the workflow step (e.g., "all tests pass," "no high/critical security findings").
4. **Context must be complete.** The receiving agent should be able to begin work without asking follow-up questions about prior steps.

## Quality Gates

Quality gates are checkpoints between workflow steps that prevent low-quality work from advancing.

### Configured Gates

The project's quality gates are defined in `.teamwork/config.yaml`:

```yaml
quality_gates:
    handoff_complete: true   # Handoff artifact must exist and be valid
    tests_pass: true         # Test suite must pass before advancing
    lint_pass: true          # Linting must pass before advancing
```

### Gate Behavior

| Scenario | Orchestrator Action |
|----------|-------------------|
| Gate passes | Advance to the next step and dispatch the next role |
| Gate fails | Keep workflow at current step, re-dispatch the responsible role with feedback on what failed |
| Gate fails after retry | Escalate to the human with details on what failed and what was tried |
| Blocker raised | Set workflow status to `blocked`, escalate immediately |

### Per-Workflow Gate Overrides

Some workflows skip certain roles or gates. These are configured in `.teamwork/config.yaml`:

```yaml
workflows:
    skip_steps:
        documentation:
            - security-auditor    # Docs-only changes skip security audit
        spike:
            - tester              # Research spikes skip formal testing
            - security-auditor    # Research spikes skip security audit
```

## Error Recovery and Retry Patterns

### Iteration Loops

When a quality gate fails, the workflow does not advance — it loops back to the responsible role:

```
Coder → Tester → [defects found] → Coder → Tester → [pass] → Security Auditor
Coder → Reviewer → [changes requested] → Coder → Reviewer → [approved] → Human
```

Specific loop patterns:

- **Reviewer requests changes:** Control returns to the Coder (step 4 in most workflows). The Coder addresses feedback and re-submits for review.
- **Tester finds defects:** The Coder fixes them before the Security Auditor and Reviewer see the PR.
- **UX Agent finds blocking issues:** The Coder fixes them before the Security Auditor reviews.
- **Security Auditor finds high/critical vulnerabilities:** The Coder remediates before the Reviewer sees the PR.

### Retry Limits

If a step has been retried more than **twice** without success, the Orchestrator escalates to the human. This prevents infinite loops where an agent cannot resolve an issue on its own.

### Blocker Handling

When an agent encounters a situation it cannot resolve:

1. The agent raises a blocker with a description of what's wrong and what it tried.
2. The Orchestrator sets the workflow status to `blocked` in the state file.
3. The Orchestrator escalates to the human with full context.
4. The workflow remains blocked until the human intervenes.
5. After human intervention, the Orchestrator resumes from the blocked step.

### Escalation Triggers

Agents must escalate (not guess) when:

- The task description is ambiguous and "done" cannot be determined
- Acceptance criteria conflict with each other or with existing behavior
- A required secret or credential is needed but unavailable
- The scope is significantly larger than the complexity estimate suggests
- Two roles produce conflicting outputs

## Common Workflow Examples

### Feature Workflow

The most common workflow. Delivers a new feature from a human-provided goal to merged, documented code.

```
Human (goal) → Orchestrator (init)
  → Planner (decompose into tasks)
    → Architect (validate feasibility, design decisions)
      → Coder (implement, write tests, open PR)
        → Tester (validate, write edge-case tests)
          → UX Agent (review frontend changes, if applicable)
            → Security Auditor (scan for vulnerabilities)
              → Reviewer (code review)
                → Human (approve & merge)
                  → Documenter (update docs & changelog)
                    → Orchestrator (complete)
```

**Key characteristics:**
- Steps 4–8 repeat for each PR if the feature spans multiple tasks.
- Step 5a (UX Agent) is skipped for backend-only PRs.
- Independent tasks can be implemented in parallel, each as a separate PR.
- The Planner's dependency graph determines which tasks can run concurrently.

### Bugfix Workflow

Diagnoses and fixes a reported bug with a regression test to prevent recurrence.

```
Human/Triager (bug report) → Orchestrator (init)
  → Planner (confirm reproduction, create fix task)
    → Architect (scope the fix, check for systemic issues)
      → Coder (write failing test first, then fix)
        → Tester (validate fix, check for regressions)
          → Security Auditor (assess if bug was exploitable)
            → Reviewer (review fix for correctness and minimality)
              → Human (approve & merge)
                → Documenter (changelog, correct misleading docs)
                  → Orchestrator (complete)
```

**Key characteristics:**
- Reproduction is required before a fix task is created — no fixing unconfirmed bugs.
- The Coder writes a failing regression test first, then makes it pass with the fix.
- Minimal fixes only — adjacent problems discovered during investigation become separate issues.
- If the Security Auditor determines the bug is exploitable, immediate escalation to the human is required.

### Hotfix Workflow

Abbreviated workflow for critical production issues requiring immediate resolution.

```
Human (critical issue) → Orchestrator (init, expedited)
  → Architect (quick scope check)
    → Coder (fix + regression test)
      → Tester (validate)
        → Reviewer (expedited review)
          → Human (merge)
            → Orchestrator (complete)
```

**Key characteristics:**
- Architect provides a quick scope check rather than full design review.
- Security Auditor can review post-merge if urgency demands it.
- Abbreviated documentation — the PR description documents the abbreviation.

### Documentation Workflow

Creates or updates documentation independently of code changes.

```
Human (docs request) → Orchestrator (init)
  → Planner (scope documentation work)
    → Documenter (write/update docs)
      → Reviewer (review for accuracy and clarity)
        → Human (approve & merge)
          → Orchestrator (complete)
```

**Key characteristics:**
- Security Auditor is skipped (configured in `workflows.skip_steps`).
- Tester is typically not involved unless docs include code examples that should be verified.

## Sub-Agent Delegation

When agents use sub-agents (background tasks) for parallel work, additional coordination rules apply:

### Incremental Turns

Sub-agents should work in small, focused turns rather than monolithic runs:

1. **Small first turn** — Scoped task (analyze, plan, or implement one thing).
2. **Read and verify** — Review the result before sending the next step.
3. **Follow-up turns** — Build on verified work incrementally.

### Parallel Agent Safety

When multiple agents work on the same branch simultaneously:

- **Always use selective staging:** `git add <specific-files>` — never `git add .` or `git add -A`.
- **Sequential dispatch** is safest when changes overlap in the same files.
- **Separate branches** provide full isolation when required.

## Related Documentation

- [Agent Lifecycle](agent-lifecycle.md) — How agents are created, modified, and retired
- [State Management](state-management.md) — How workflow state is tracked
- [Role Selector](role-selector.md) — How to choose the right agent
- [Workflow Selector](workflow-selector.md) — How to choose the right workflow
- [Conventions](conventions.md) — Coding and process standards
