---
name: milestone-workflow
description: "End-to-end workflow for executing a planned milestone — from branch creation through merged, released code. Use when a milestone with issues exists in GitHub and the team is ready to implement it."
---

# Milestone Execution Workflow

## Overview

End-to-end workflow for implementing all issues in a GitHub milestone as a single cohesive unit
of work. Creates one feature branch and one PR per milestone, works through all issues using
agents and fleet parallelism, iterates through Copilot review and CI checks until clean, then
merges, releases, and closes the milestone before moving to the next one.

Use this workflow when milestones with issues are defined in GitHub and the team is ready to
begin implementation. This is the primary workflow for executing planned development work.

## Trigger

A human decides to begin work on one or more GitHub milestones. The milestones should already
have issues assigned with clear acceptance criteria. Milestones are executed in dependency order.

## Steps

| # | Role | Action | Inputs | Outputs | Success Criteria |
|---|------|--------|--------|---------|------------------|
| 0 | **Orchestrator** | Initialize workflow: create state file, identify target milestone, verify issues exist, determine dependency order | Milestone list, dependency map | `.teamwork/state/<id>.yaml`, execution plan, metrics log entry | State file created with status `active`; milestones ordered; all issues have acceptance criteria |
| 1 | **Coder** | Create feature branch for the milestone (`feat/<milestone-slug>`) | Milestone name, main branch | Feature branch created from latest main | Branch created; naming follows conventions |
| 2 | **Coder** | Open a draft PR linking all milestone issues with GitHub issue-closing keywords | Feature branch, milestone issues | Draft PR with issue-closing references in body | PR created; all issues linked with "Closes #N" or "Fixes #N" |
| 3 | **Orchestrator** | Dispatch issues to agents for parallel implementation | PR, milestone issues, dependency graph | Agent assignments | Independent issues dispatched in parallel; dependent issues queued |
| 4 | **Coder / Fleet** | Implement each issue using incremental agent turns: send focused first step, read result, send follow-up. Agents commit after each unit of work. | Issue acceptance criteria, conventions | Commits on feature branch | Each issue's acceptance criteria met; tests written; progress visible via git log |
| 5 | **Tester** | Run full test suite, verify coverage thresholds | Feature branch with all changes | Test results, coverage report | All tests pass; coverage ≥ 75% backend/frontend |
| 6 | **Lint Agent** | Run linters, fix any style violations | Feature branch | Clean lint output | No lint errors in backend or frontend |
| 7 | **Coder** | Request Copilot review on the PR | PR ready for review | Copilot review comments | Review requested successfully |
| 8 | **Coder** | Address all Copilot review recommendations | Copilot review comments | Commits addressing each recommendation | Every recommendation addressed or justified |
| 9 | **Coder** | Mark PR "Ready for Review" and trigger CI checks | PR with all changes | CI pipeline running | PR marked ready; checks triggered |
| 10 | **Coder** | Fix any CI check failures (lint, test, build, coverage) | CI failure logs | Commits fixing failures | All checks green |
| 11 | **Orchestrator** | Evaluate loop condition: are Copilot reviews clean AND all checks green? | Latest review, CI status | Decision: loop back to step 7 or proceed | If issues remain → loop to step 7. If clean → proceed |
| 12 | **Human** | Review the PR; approve or request changes | Clean PR, passing checks, Copilot approval | Merge approval | Human approves the PR |
| 13 | **Coder** | Merge PR to main | Approved PR | Merged commit on main | PR merged; main branch updated |
| 14 | **Coder** | Create a new release from the merge | Merged main, version strategy | GitHub Release with tag and notes | Release created with changelog |
| 15 | **Orchestrator** | Close the completed milestone | Merged PR, release | Milestone closed | All milestone issues closed; milestone marked complete |
| 16 | **Orchestrator** | Complete workflow: validate all gates passed, update state file to `completed` | All step outputs, quality gate results | State file with status `completed`, final metrics | All completion criteria verified; state file finalized |
| 17 | **Orchestrator** | Move to next milestone; repeat from step 0 | Next milestone in order | New iteration begins | Workflow continues until all milestones complete |

## Quality Gate Loop (Steps 7–11)

This is the critical quality loop that repeats until the PR is clean:

```
┌─────────────────────────────────────────────────┐
│                                                 │
│  Step 7: Request Copilot Review                 │
│      ↓                                          │
│  Step 8: Address Copilot Recommendations        │
│      ↓                                          │
│  Step 9: Mark Ready for Review + Run Checks     │
│      ↓                                          │
│  Step 10: Fix CI Failures                       │
│      ↓                                          │
│  Step 11: All clean? ──No──→ Loop to Step 7     │
│      │                                          │
│     Yes                                         │
│      ↓                                          │
│  Step 12: Human Review                          │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Exit condition:** Copilot review has no new recommendations AND all CI checks are green.

## Handoff Contracts

Each step must produce specific artifacts before the next step can begin.

The orchestrator validates each handoff artifact before dispatching the next role. Handoffs are stored in `.teamwork/handoffs/<workflow-id>/` following the format in `.teamwork/docs/protocols.md`.

**Orchestrator → Coder (Step 1)**
- Milestone name and slug for branch naming
- List of all issues with acceptance criteria
- Dependency order for issues

**Coder → Orchestrator (Step 4 complete)**
- All issues implemented with commits referencing issue numbers
- Tests written for all new/modified code

**Orchestrator → Human (Step 12)**
- PR link with:
  - All checks passing
  - Copilot review clean (no outstanding recommendations)
  - Summary of changes and issues addressed

**Human → Coder (Step 13)**
- Merge approval (verbal or GitHub approval)

**Coder → Orchestrator (Step 14)**
- Release URL and tag
- Changelog entries

## Completion Criteria

A milestone is complete when:

- All issues in the milestone are implemented and their acceptance criteria are met
- All tests pass with coverage at or above thresholds (75% backend, 75% frontend)
- All linters pass with no errors
- Copilot review has no unaddressed recommendations
- All CI checks are green
- PR is merged to main
- A GitHub Release is created with version tag and release notes
- The milestone is closed on GitHub
- All linked issues are closed

The full workflow is complete when all milestones have been executed in order.

## Notes

- **One PR per milestone:** All issues in a milestone are implemented on a single feature
  branch in a single PR. This eliminates rebase conflicts and allows maximum parallelism
  within the milestone.
- **Fleet parallelism:** Independent issues (no dependency relationship) should be dispatched
  to agent fleet for parallel implementation. The orchestrator uses the dependency graph to
  determine which issues can run concurrently.
- **Milestone ordering:** Milestones are executed in dependency order. A milestone cannot begin
  until all milestones it depends on are complete and merged to main.
- **Branch naming:** Use `feat/<milestone-slug>` (e.g., `feat/security-stability`,
  `feat/test-coverage`). If the milestone is a fix-focused milestone, use `fix/<milestone-slug>`.
- **Issue linking:** The PR body should reference all milestone issues using "Closes #N" or
  "Fixes #N" keywords so that issues auto-close when the PR merges. Use "Closes" for
  feature issues and "Fixes" for bug issues. Only use "Addresses #N" for issues that are
  partially addressed and will need follow-up work in a later milestone.
- **Human checkpoints:** The human reviews at step 12 only. All other quality gates (Copilot
  review, CI checks) are automated. The human should not need to intervene unless something
  unexpected arises.
- **Release versioning:** Follow semantic versioning. Each milestone merge produces a release.
  Use the milestone's scope to determine version bump: security fixes = patch, new features
  = minor, breaking changes = major.
- **Rollback:** If a merged milestone causes issues on main, invoke the rollback-workflow skill
  to revert the merge before proceeding with the next milestone.
- **Incremental agent turns:** When dispatching agents in step 4, prefer multi-turn conversations
  over monolithic single-turn dispatches. Send a focused first step, read the result with
  `read_agent`, then send follow-ups with `write_agent`. This provides checkpoint-level
  visibility and the ability to course-correct. See `AGENTS.md` §Sub-Agent Delegation Pattern.

## Error Handling

### Common Failures

| Step | Failure | Recovery Action |
|------|---------|-----------------|
| 0 (Orchestrator) | Milestone has issues without acceptance criteria | Pause workflow. Return issues to the Planner for criteria before proceeding with implementation |
| 4 (Coder/Fleet) | Agent fails mid-implementation of an issue | Retry the agent on the same issue. If it fails again, break the issue into smaller sub-tasks and dispatch individually |
| 4 (Coder/Fleet) | Merge conflicts between parallel agents | Resolve conflicts on the feature branch. Prefer rebasing individual agent work. If conflicts are severe, serialize the conflicting issues instead of parallelizing |
| 5 (Tester) | Coverage falls below 75% threshold | Return to Coder (step 4) to add missing tests. Identify which issues lack coverage and dispatch targeted test-writing |
| 6 (Lint) | Lint errors across many files | Dispatch Lint Agent to fix all violations. If lint errors reveal deeper code quality issues, file follow-up issues rather than expanding scope |
| 7–11 (Quality Loop) | Loop iterates more than 3 times without converging | Escalate to human. Likely indicates a fundamental issue with the implementation approach. Consider reverting to step 4 with revised guidance |
| 10 (Coder) | CI failures that are flaky or infrastructure-related | Retry CI. If a specific test is flaky, document it and file a separate issue. Do not block the milestone on pre-existing flakiness |
| 13 (Coder) | Merge to main fails (branch protection, conflicts) | Rebase the feature branch onto latest main and resolve conflicts. Re-run CI after rebase |

### Escalation Criteria

- Quality gate loop exceeds 3 iterations — escalate to human for direction
- More than 30% of milestone issues fail during implementation — re-evaluate milestone scope with Planner
- Milestone is blocked by an incomplete dependency milestone — cannot proceed; set to `blocked`
- Human review (step 12) results in major rework — loop back to step 4 with revised scope

### Rollback Procedures

- Before merge: abandon the feature branch entirely and restart the milestone
- After merge: invoke **rollback-workflow** to revert the milestone PR, then restart
- After release: if the release causes issues, create a patch release reverting the problematic changes
