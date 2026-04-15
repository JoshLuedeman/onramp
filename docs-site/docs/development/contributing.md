# Contributing

Thank you for your interest in contributing to OnRamp! This guide covers the conventions and processes for contributing code.

## Branch Naming

Use descriptive branch names with a type prefix:

```
feat/short-description     # New features
fix/short-description      # Bug fixes
docs/short-description     # Documentation changes
refactor/short-description # Code refactoring
test/short-description     # Test additions or changes
chore/short-description    # Maintenance tasks
```

**Examples:**

- `feat/compliance-scoring`
- `fix/questionnaire-validation`
- `docs/api-reference`

## Commit Format

OnRamp uses [Conventional Commits](https://www.conventionalcommits.org/). Every commit message must follow this format:

```
<type>: <description>
```

**Types:**

| Type       | Use For                                     |
| ---------- | ------------------------------------------- |
| `feat`     | New feature                                  |
| `fix`      | Bug fix                                      |
| `docs`     | Documentation changes                        |
| `refactor` | Code restructuring without behavior change   |
| `test`     | Adding or updating tests                     |
| `chore`    | Build, CI, or maintenance tasks              |

**Examples:**

```
feat: add compliance scoring endpoint
fix: handle empty questionnaire answers
docs: update API reference for deployment
test: add integration tests for bicep generation
chore: update vitepress dependency
```

## Pull Request Process

1. **Create a branch** from `main` using the naming convention above
2. **Make your changes** — keep them focused on a single task
3. **Write tests** for any new or changed behavior
4. **Run lint and tests** locally before pushing:
   ```bash
   # Backend
   cd backend && ruff check app/ && pytest tests/ -v --cov=app --cov-fail-under=75

   # Frontend
   cd frontend && npm run lint && npm run test:coverage && npm run build
   ```
5. **Open a PR** with:
   - A clear title matching the commit convention
   - A description summarizing what changed and why
   - A link to the related issue (e.g., `Closes #42`)
6. **All CI checks must pass** — lint, test, build, and coverage thresholds
7. **Wait for review** — at least one approval required before merging
8. **One task per PR** — don't combine multiple tasks into a single PR

## Code Style

### Backend (Python)

- **Linter:** [Ruff](https://docs.astral.sh/ruff/)
- **Type hints:** Required for all function signatures
- **Docstrings:** Required for public functions and classes
- **Framework:** FastAPI with Pydantic models for request/response

### Frontend (TypeScript)

- **Linter:** ESLint
- **Components:** Fluent UI v9
- **State management:** React hooks
- **Styling:** Fluent UI tokens and `makeStyles`

## Getting Help

- Check existing [issues](https://github.com/JoshLuedeman/onramp/issues) for context
- Read the [Architecture Guide](./architecture) for system design decisions
- Review the [API Reference](/api/) for endpoint contracts
