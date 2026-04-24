# Agent Lifecycle

How agents are created, modified, and retired in the OnRamp Teamwork system.

## Overview

OnRamp uses a multi-agent system where specialized AI agents collaborate through structured workflows. Each agent is defined by a Markdown file in `.github/agents/` and is orchestrated by the Orchestrator agent, which dispatches roles, validates handoffs, and tracks workflow state.

## Agent Creation

### File Structure

Each agent is defined in a single `.agent.md` file under `.github/agents/`. The file uses YAML frontmatter for metadata followed by Markdown content defining the agent's behavior.

```
.github/agents/<name>.agent.md
```

### Frontmatter Schema

Every agent file begins with YAML frontmatter:

```yaml
---
name: <agent-name>          # Lowercase, kebab-case identifier
description: <one-liner>    # When to use this agent (displayed in tool pickers)
tools: ["read", "search"]   # Tool access: read, search, edit, execute
---
```

### Required Sections

Agent files follow a consistent structure with these sections:

| Section | Purpose |
|---------|---------|
| **Identity** | One-sentence summary of who the agent is and what it does |
| **Project Knowledge** | Project-specific context (tech stack, paths, commands) |
| **Model Requirements** | Model tier (Premium, Standard, Fast) and justification |
| **MCP Tools** | Which MCP servers and tools the agent uses |
| **Responsibilities** | Enumerated list of what the agent is expected to do |
| **Inputs** | What the agent receives to begin its work |
| **Outputs** | What the agent produces as deliverables |
| **Boundaries** | Always/Ask first/Never rules governing behavior |
| **Quality Bar** | Criteria for "good enough" output |
| **Escalation** | When to stop and ask the human for help |

### Creation Process

1. **Identify the gap.** Determine what role is missing or underserved. Check the [Role Selector](role-selector.md) to ensure no existing agent covers this responsibility.
2. **Draft the agent file.** Create `.github/agents/<name>.agent.md` following the structure above. Start with Identity, Responsibilities, and Boundaries — these define the agent's scope.
3. **Register in config.** Add the agent name to `.teamwork/config.yaml` under `roles.core` or `roles.optional`.
4. **Assign MCP tools.** In `.teamwork/config.yaml` under `mcp_servers`, add the agent name to the `roles` array of each MCP server it needs access to.
5. **Update documentation.** Add the agent to the [Role Selector](role-selector.md) decision tree so the Orchestrator and humans know when to invoke it.
6. **Test the agent.** Invoke the agent on a real or representative task and verify it stays within its boundaries, produces the expected outputs, and escalates appropriately.

## Agent Roles and Responsibilities

### Core Agents

These agents are registered in `roles.core` in `.teamwork/config.yaml` and participate in standard workflows.

| Agent | Description |
|-------|-------------|
| **Orchestrator** | Coordinates workflow state machines — dispatches roles, validates handoffs, enforces quality gates, tracks progress. Never implements or reviews code. |
| **Planner** | Translates high-level goals into structured, actionable tasks with acceptance criteria and dependencies. |
| **Architect** | Makes design decisions, evaluates tradeoffs, documents architecture through ADRs. Validates feasibility before implementation begins. |
| **Coder** | Implements tasks by writing code and tests. Opens PRs linked to task issues. Follows conventions and keeps changes minimal. |
| **Tester** | Writes and runs tests with an adversarial mindset — edge cases, error paths, boundary conditions. Validates acceptance criteria. |
| **Reviewer** | Reviews PRs for correctness, quality, and standards compliance. Approves or requests changes with specific, actionable feedback. |
| **Security Auditor** | Identifies vulnerabilities, unsafe patterns, and security risks in code and configuration. Scans for secrets and unsafe dependencies. |
| **Documenter** | Writes and maintains documentation — READMEs, API docs, changelogs, architecture docs. Updates docs after features merge. |

### Optional and Specialized Agents

These agents are invoked when their specific expertise is needed.

| Agent | Description |
|-------|-------------|
| **Triager** | Categorizes incoming issues, assigns priority and labels, identifies duplicates, routes work to appropriate workflows. |
| **DevOps** | Manages CI/CD pipelines, deployment configurations, infrastructure-as-code, and build systems. |
| **API Agent** | Designs and builds API endpoints, maintains API contracts and OpenAPI specs, ensures RESTful consistency. |
| **DBA Agent** | Database schema design, migration scripts, query optimization, and data integrity enforcement. |
| **Dependency Manager** | Monitors, evaluates, and updates project dependencies for security, compatibility, and health. |
| **Lint Agent** | Dedicated code style and formatting enforcer — fixes linting errors and enforces naming conventions without changing logic. |
| **Product Owner** | Defines product priorities, validates feature alignment with business goals, maintains the product backlog. |
| **QA Lead** | Defines test strategy, coordinates quality assurance across roles, validates release readiness. |
| **Refactorer** | Improves code quality without changing behavior — resolves tech debt, code smells, duplication, and excessive complexity. |
| **UX Agent** | Reviews frontend code for design quality, accessibility, and user experience. Invoked when PRs touch `frontend/src/`. |

## Agent Modification and Versioning

### When to Modify an Agent

- The agent's responsibilities have expanded or narrowed based on project needs.
- New MCP tools are available that the agent should use.
- The agent's model tier needs adjustment (e.g., a previously Fast agent needs Premium reasoning).
- Boundary rules need tightening after an incident (e.g., an agent overstepped its scope).
- Project Knowledge needs updating (new paths, new commands, new conventions).

### Modification Process

1. **Edit the agent file directly.** Agent definitions are plain Markdown — modify the relevant section in `.github/agents/<name>.agent.md`.
2. **Update config if needed.** If tool access or MCP server assignments changed, update `.teamwork/config.yaml`.
3. **Commit with a descriptive message.** Use Conventional Commits: `docs(agents): update coder boundaries for new test requirements`.
4. **Test the change.** Run the agent on a task that exercises the modified behavior. Verify it respects new boundaries and produces correct outputs.

### Versioning

Agent files are versioned through Git alongside the rest of the codebase. The `.teamwork/framework-manifest.json` file tracks SHA-256 hashes of all framework files, including agent definitions, enabling detection of local modifications vs. framework defaults.

- **Framework updates** may introduce changes to agent definitions. Compare hashes in `framework-manifest.json` against local files to detect drift.
- **Local customizations** (project-specific Knowledge, Responsibilities, or Boundaries) should be committed and documented so they survive framework updates.

## Agent Deprecation and Removal

### When to Deprecate

- The agent's responsibilities are fully covered by another agent.
- The agent was experimental and the experiment concluded.
- A workflow change eliminates the need for the role.

### Deprecation Process

1. **Remove from workflows.** Ensure no active workflow references the agent in its steps. Check all SKILL.md files in `.github/skills/`.
2. **Remove from config.** Remove the agent name from `roles.core` or `roles.optional` in `.teamwork/config.yaml`. Remove it from `mcp_servers[*].roles` arrays.
3. **Update the Role Selector.** Remove the agent from the decision tree in `docs/role-selector.md`.
4. **Delete the agent file.** Remove `.github/agents/<name>.agent.md`.
5. **Commit with explanation.** Use: `chore(agents): remove <name> agent — responsibilities covered by <replacement>`.
6. **Verify workflows.** Run through at least one instance of each workflow that previously used the agent to confirm no step is broken.

## Testing Agent Changes

### Manual Testing

Invoke the agent on a representative task and verify:

- **Scope compliance:** The agent stays within its defined boundaries (Always/Ask first/Never rules).
- **Output quality:** Deliverables meet the Quality Bar criteria defined in the agent file.
- **Escalation behavior:** The agent asks for help in the documented Escalation scenarios instead of guessing.
- **Handoff compatibility:** The agent's outputs are accepted by downstream agents in the workflow.

### Checklist

Before merging agent changes:

- [ ] Agent file follows the required section structure
- [ ] YAML frontmatter includes `name`, `description`, and `tools`
- [ ] Agent is registered in `.teamwork/config.yaml` (if new)
- [ ] MCP server access is configured for the agent's needs
- [ ] Role Selector is updated (if new or removed)
- [ ] Agent has been invoked on at least one representative task
- [ ] Downstream workflow steps still accept the agent's output format

## Related Documentation

- [Role Selector](role-selector.md) — How to choose the right agent for a task
- [Workflow Selector](workflow-selector.md) — How to choose the right workflow
- [Handoff Protocol](handoff-protocol.md) — How work flows between agents
- [State Management](state-management.md) — How workflow state is tracked
- [Conventions](conventions.md) — Coding and process standards
