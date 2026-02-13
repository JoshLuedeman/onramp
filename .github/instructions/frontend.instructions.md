---
applyTo: "frontend/**"
---

# Frontend Instructions (React + Fluent UI v9)

## Framework Rules

- Use React 19 with functional components and hooks only. Never use class components.
- Use Fluent UI React v9 (`@fluentui/react-components`). Never import from `@fluentui/react` (v8).
- Use React Router v7 (`react-router-dom`). Define routes in `App.tsx`.
- Use TypeScript strict mode. Never use `any` — use `unknown` with type guards for catch blocks.

## Styling

- Use `makeStyles` from `@griffel/react` for all component styles.
- Use `tokens` from `@fluentui/react-components` for colors, spacing, font sizes. Never use raw CSS values.
- Never use CSS modules, inline styles, or `styled-components`.

## Component Patterns

- All page components must be lazy-loaded with `React.lazy()` and wrapped in `<Suspense>`.
- All API calls go through `src/services/api.ts`. Never call `fetch()` directly in components.
- Use relative URLs for API calls (e.g., `/api/questionnaire/next`). Never hardcode `localhost`.
- Use ES module imports only. Never use `require()`.
- State management: React hooks (`useState`, `useEffect`, `useCallback`). No external state library.

## Icons

- Import from `@fluentui/react-icons`.
- Verify the icon name exists before using — not all v8 icon names exist in the current package.

## File Naming

- Components: `PascalCase.tsx` (e.g., `QuestionCard.tsx`)
- Hooks: `camelCase.ts` (e.g., `useAuth.ts`)
- Services/utils: `camelCase.ts` (e.g., `api.ts`, `exportUtils.ts`)
- Tests: colocated as `ComponentName.test.tsx`

## Testing (MANDATORY)

- Framework: Vitest + @testing-library/react + @testing-library/user-event
- Config: `frontend/vitest.config.ts` — jsdom environment, v8 coverage
- Setup: `src/test/setup.ts` — imports `@testing-library/jest-dom/vitest`, polyfills `ResizeObserver`
- Coverage thresholds: statements 75%, branches 70%, functions 60%, lines 75%
- Every new component MUST have a colocated `.test.tsx` file
- Wrap all Fluent UI components in `<FluentProvider theme={teamsLightTheme}>` in tests
- Use `<MemoryRouter>` for components that use React Router
- Run: `npm run test` (watch) or `npm run test:coverage` (with coverage)

### Testing Gotchas

- `document.createElement` mocks break jsdom rendering. Mock `URL.createObjectURL` AFTER `render()`.
- Fluent UI Checkbox does not reliably toggle via `userEvent.click` in jsdom.
- Type-only files (`src/types/**`, `src/auth/msalConfig.ts`) are excluded from coverage.

## Existing API Service Methods (`src/services/api.ts`)

```typescript
api.questionnaire.getCategories()
api.questionnaire.getQuestions()
api.questionnaire.getNextQuestion(answers)
api.questionnaire.resolveUnsure(questionId, answers)
api.questionnaire.getProgress(answers)
api.architecture.getArchetypes()
api.architecture.generate(answers, options)
api.architecture.refine(architecture, instructions)
api.architecture.estimateCosts(architecture)
```

Add new methods here for any new backend endpoints. Do not call `fetch()` directly.
