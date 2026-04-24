---
name: feature-workflow
description: "End-to-end workflow for delivering a new feature from goal to merged, documented code. Use when the team receives a feature request or high-level goal."
---

# Feature Development Workflow

## Overview

End-to-end workflow for delivering a new feature from a human-provided goal to merged,
documented code. Use this workflow when the team receives a feature request, product
requirement, or high-level goal that requires new functionality. This is the most common
workflow and serves as the backbone of the development process.

## Trigger

A human creates a feature request or defines a goal (issue, description, or conversation).
The request should include enough context for the Planner to begin decomposition — at minimum
a clear goal statement and any known constraints or requirements.

## Steps

| # | Role | Action | Inputs | Outputs | Success Criteria |
|---|------|--------|--------|---------|------------------|
| 0 | **Orchestrator** | Initialize workflow: create state file, validate inputs | Trigger event, goal description | `.teamwork/state/<id>.yaml`, metrics log entry | State file created with status `active` |
| 1 | **Human** | Creates feature request with goal, context, and constraints | Product need or idea | Feature request with goal statement and constraints | Goal is clearly stated; enough context for planning |
| 2 | **Planner** | Decomposes goal into tasks with acceptance criteria, dependencies, and complexity estimates | Feature request | Task issues, dependency graph, milestone grouping | Every task has acceptance criteria; dependencies form a valid DAG |
| 3 | **Architect** | Reviews tasks for feasibility, makes design decisions, creates ADR if needed | Task list, dependency graph | Feasibility assessment, design decisions, ADR (if needed) | All tasks validated as feasible; decisions documented |
| 4 | **Coder** | Implements each task in dependency order, writes tests, opens PR | Validated tasks, design decisions, conventions | PR(s) with code, tests, linked issues, CI passing (if CI exists) | Code satisfies acceptance criteria; tests pass if test infrastructure exists; manual verification documented if not |
| 5 | **Tester** | Reviews coverage, writes edge-case tests, validates against acceptance criteria | PR, acceptance criteria | Additional tests, coverage report, defect reports | Acceptance criteria verified; edge cases covered; if no test suite, manual verification steps documented |
| 5a | **UX Agent** | Reviews frontend changes for accessibility, design system compliance, and usability (skip if PR has no frontend changes) | PR diff touching `frontend/src/`, UX checklist (`docs/ux-checklist.md`) | UX review with accessibility findings, design system violations, interaction state gaps | No blocking UX findings (WCAG A/AA violations); design system compliance verified |
| 6 | **Security Auditor** | Scans PR for vulnerabilities, secrets, unsafe dependencies | PR diff, dependency manifest | Security findings (severity, location, remediation) | No high/critical findings unresolved |
| 7 | **Reviewer** | Reviews for correctness, quality, standards, test sufficiency | PR, acceptance criteria, security findings, UX findings | Review decision, review comments | PR approved or actionable change requests given |
| 8 | **Human** | Approves and merges the PR | Approved PR, review summary | Merged code on target branch | Code merged; CI passes on target branch |
| 9 | **Documenter** | Updates README, API docs, architecture docs, changelog | Merged PR, task descriptions, ADRs | Updated docs, changelog entry | All docs reflect the new feature |
| 10 | **Orchestrator** | Complete workflow: validate all gates passed, update state | All step outputs, quality gate results | State file with status `completed`, final metrics | All completion criteria verified |

## Handoff Contracts

Each step must produce specific artifacts before the next step can begin.

The orchestrator validates each handoff artifact before dispatching the next role. Handoffs are stored in `.teamwork/handoffs/<workflow-id>/` following the format in `.teamwork/docs/protocols.md`.

**Human → Planner**
- Feature request with goal statement, context, and constraints (issue or structured description)

**Planner → Architect**
- Task issues with acceptance criteria and labels
- Dependency graph with links between issues

**Architect → Coder**
- Feasibility assessment per task (comments on task issues)
- Design decisions and conventions to follow
- ADR file in `.teamwork/docs/decisions/` (if the feature introduces new patterns)

**Coder → Tester**
- Open PR with implementation and initial tests (or manual verification notes if no test infrastructure exists)
- PR linked to task issues; CI passing (if CI exists)

**Tester → UX Agent** (if PR touches `frontend/src/`)
- PR branch with complete test suite committed
- Coverage summary posted as PR comment

**UX Agent → Security Auditor**
- UX review posted as PR comment with accessibility findings, design system violations, and interaction state gaps
- "No findings" confirmation if clean
- Step skipped entirely if PR has no frontend changes

**Tester → Security Auditor** (if PR has no frontend changes)
- PR branch with complete test suite committed
- Coverage summary posted as PR comment

**Security Auditor → Reviewer**
- Security findings table as PR comment (severity, location, remediation)
- "No findings" confirmation if clean

**Reviewer → Human**
- GitHub PR review: approved or changes requested with file/line-specific comments

**Human → Documenter**
- Merged commit on target branch

## Completion Criteria

- All tasks from the plan are implemented, tested (or manually verified if no test suite exists), reviewed, and merged.
- No unresolved security findings at high or critical severity.
- Documentation is updated to reflect the new feature.
- Changelog entry exists for the feature.

## Notes

- **Iteration loops**: If the Reviewer requests changes, control returns to the Coder
  (step 4). If the Tester finds defects, the Coder fixes them before the UX Agent and
  Security Auditor review. If the UX Agent finds blocking issues, the Coder fixes them
  before the Security Auditor reviews. These loops repeat until all quality gates pass.
- **Parallel work**: Independent tasks (no dependency relationship) can be implemented in
  parallel by the Coder, each as a separate PR. The Planner's dependency graph determines
  which tasks can run concurrently.
- **ADR threshold**: The Architect should create an ADR when the feature introduces a new
  technology, pattern, or trade-off that future contributors need to understand. Small
  features following existing patterns do not need an ADR.
- **Scope creep**: If the Architect or Coder discovers the feature is larger than expected,
  surface this to the Planner to re-scope before continuing. Do not silently expand the
  implementation beyond the original task boundaries.
- **Multi-PR features**: Large features produce multiple PRs. Each PR goes through steps
  4–8 independently. The Documenter (step 9) can run once after all PRs merge, or
  incrementally as each PR lands.
- **Optional roles**: If a Triager is active, it may pre-process the feature request before
  the Planner picks it up. If DevOps is active, they coordinate deployment after merge.
- **Blocked tasks**: If the Architect flags a task as infeasible, the Planner must revise
  the plan before the Coder begins. Never skip the Architect's review to save time.
- **Orchestrator coordination:** The orchestrator manages workflow state throughout. If any
  quality gate fails, the orchestrator keeps the workflow at the current step and notifies
  the responsible role. If a blocker is raised, the orchestrator sets the workflow to
  `blocked` and escalates to the human.
- **Projects without a test suite:** If the project has no test infrastructure, steps 4 and 5
  adapt as follows: the Coder documents manual verification steps and their results in the
  handoff artifact; the Tester performs structured manual testing using the acceptance criteria
  as a checklist and documents each step and outcome. This is not a permanent exemption —
  the Planner or Architect should track adding test infrastructure as a follow-up task.

## Error Handling

### Common Failures

| Step | Failure | Recovery Action |
|------|---------|-----------------|
| 2 (Planner) | Goal is too vague to decompose into tasks | Return to Human (step 1) requesting clearer acceptance criteria, constraints, and scope boundaries |
| 3 (Architect) | Task is infeasible with current architecture | Architect flags the issue. Planner must revise the plan before Coder begins. May spawn a spike-workflow to investigate alternatives |
| 4 (Coder) | Implementation reveals scope is much larger than estimated | Stop and surface to Planner for re-scoping. Do not silently expand — file new issues for discovered work |
| 4 (Coder) | CI failures unrelated to the feature (flaky tests, infra issues) | Retry CI. If persistent, isolate the flaky test and file a separate bug. Do not block the feature on pre-existing CI issues |
| 5 (Tester) | Acceptance criteria are ambiguous or untestable | Return to Planner to clarify criteria. Tester should not invent acceptance criteria — they come from the plan |
| 6 (Security) | Critical vulnerability found in the implementation | Return to Coder (step 4) with specific remediation guidance. Block merge until resolved |
| 7 (Reviewer) | PR is too large to review effectively | Return to Planner to split into smaller PRs. Each sub-PR goes through steps 4–8 independently |
| 8 (Human) | Human rejects the PR for business reasons | Escalate to Planner — the feature may need re-scoping or deprioritization |

### Escalation Criteria

- Feature requires an architectural change not covered by existing ADRs — trigger a spike-workflow
- Three or more review-fix cycles without convergence — escalate to human for direction
- Blocked by an external dependency (API, service, team) — set workflow to `blocked` and notify human
- Scope creep detected (implementation growing beyond original tasks) — pause and re-plan

### Rollback Procedures

- Unmerged work: abandon the feature branch and restart from the revised plan
- Merged but broken: invoke **rollback-workflow** to revert, then restart from step 4
- Multi-PR features: revert only the problematic PR; other merged PRs remain if independent
