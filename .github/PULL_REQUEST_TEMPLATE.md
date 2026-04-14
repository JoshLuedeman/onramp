## Task Issue

Closes #<!-- issue number -->

## Description

<!-- What changes does this PR make and why? -->

## Checklist

- [ ] Linked to task issue
- [ ] Changes are minimal (only what the task requires)
- [ ] Tests added/updated
- [ ] Backend tests pass: `cd backend && pytest tests/ -v`
- [ ] Frontend tests pass: `cd frontend && npm run test`
- [ ] Backend lint passes: `cd backend && ruff check app/`
- [ ] Frontend lint passes: `cd frontend && npm run lint`
- [ ] Frontend builds: `cd frontend && npm run build`
- [ ] Coverage maintained above 75% (both frontend and backend)
- [ ] No `any` types in TypeScript
- [ ] No `print()` in Python code
- [ ] No secrets or credentials committed
- [ ] Pydantic schemas defined for new API endpoints
- [ ] New routes registered in `backend/app/main.py`
- [ ] Documentation updated (if applicable)
- [ ] Conventional Commit message format (`feat:`, `fix:`, `docs:`, etc.)

## Reviewer Notes

<!-- Anything reviewers should know or pay attention to -->

## Security Considerations

<!-- Any security implications? (new inputs, auth changes, dependency updates, Azure resource changes, etc.) -->
