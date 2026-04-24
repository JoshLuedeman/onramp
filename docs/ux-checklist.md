# UX Quality Checklist

Reference checklist for evaluating frontend components and pages in OnRamp. Used by the UX Agent during code reviews and by developers during implementation.

**Standard:** WCAG 2.1 AA · Fluent UI React v9 · Nielsen's 10 Usability Heuristics

---

## 1. Fluent UI v9 Token Usage

- [ ] All colors use `tokens.color*` — no hex codes, `rgb()`, or named colors
- [ ] All spacing uses `tokens.spacing*` — no raw pixel values for margins/padding
- [ ] All font sizes use `tokens.fontSizeBase*` — no raw `px` or `rem` values
- [ ] All font weights use `tokens.fontWeight*` — no numeric font weights
- [ ] All border radii use `tokens.borderRadius*` — no raw values
- [ ] All shadows use `tokens.shadow*` — no raw `box-shadow` values
- [ ] All line heights use `tokens.lineHeight*` — no raw values
- [ ] Styles defined with `makeStyles` from `@griffel/react` — no inline styles, CSS modules, or styled-components
- [ ] No imports from `@fluentui/react` (v8) — only `@fluentui/react-components` (v9)
- [ ] Icons imported from `@fluentui/react-icons` with verified icon names

## 2. Accessibility (WCAG 2.1 AA)

### 2.1 Perceivable
- [ ] All images have meaningful `alt` text (or `alt=""` for decorative images) — [1.1.1 Non-text Content]
- [ ] Color is not the only means of conveying information — [1.4.1 Use of Color]
- [ ] Text has minimum 4.5:1 contrast ratio (3:1 for large text) — [1.4.3 Contrast]
- [ ] Content is readable and functional at 200% zoom — [1.4.4 Resize Text]
- [ ] No information conveyed only through visual formatting — [1.3.1 Info and Relationships]
- [ ] Content follows a logical reading order in DOM — [1.3.2 Meaningful Sequence]

### 2.2 Operable
- [ ] All interactive elements are reachable via Tab key — [2.1.1 Keyboard]
- [ ] No keyboard traps (except intentional modal focus traps with Escape exit) — [2.1.2 No Keyboard Trap]
- [ ] Visible focus indicators on all interactive elements — [2.4.7 Focus Visible]
- [ ] Focus order matches visual/logical order — [2.4.3 Focus Order]
- [ ] Skip navigation link available for repeated content — [2.4.1 Bypass Blocks]
- [ ] Page titles are descriptive — [2.4.2 Page Titled]
- [ ] Link purpose is clear from text (no "click here") — [2.4.4 Link Purpose]

### 2.3 Understandable
- [ ] Form fields have visible labels (not placeholder-only) — [3.3.2 Labels or Instructions]
- [ ] Error messages identify the field and describe the error — [3.3.1 Error Identification]
- [ ] Error suggestions provide correction guidance — [3.3.3 Error Suggestion]
- [ ] Navigation is consistent across pages — [3.2.3 Consistent Navigation]
- [ ] Components behave consistently throughout the app — [3.2.4 Consistent Identification]

### 2.4 Robust
- [ ] Valid HTML — no duplicate IDs, proper nesting — [4.1.1 Parsing]
- [ ] Custom components have appropriate ARIA roles — [4.1.2 Name, Role, Value]
- [ ] Dynamic content updates use `aria-live` regions — [4.1.3 Status Messages]
- [ ] Form controls have programmatically associated labels — [4.1.2]

## 3. Responsive Design

- [ ] Layout adapts gracefully to viewport widths: 320px (mobile), 768px (tablet), 1024px+ (desktop)
- [ ] Touch targets are minimum 44×44px on mobile viewports
- [ ] No horizontal scrolling at any supported viewport width
- [ ] Text remains readable without horizontal scrolling at 320px width
- [ ] FluentProvider theme is used — supports light/dark mode switching
- [ ] Images and media scale proportionally
- [ ] Navigation collapses appropriately on smaller viewports

## 4. User Flow & Interaction Design

### 4.1 Loading States
- [ ] API calls show loading indicator (skeleton, spinner, or progress bar)
- [ ] Loading state appears within 100ms of action (no perceived delay)
- [ ] Long operations (>2s) show progress indication, not just a spinner
- [ ] Loading state is visually distinct — user knows the app is working

### 4.2 Error States
- [ ] Errors display user-friendly messages (no raw error codes or stack traces)
- [ ] Error messages suggest a recovery action ("Try again", "Go back", "Contact support")
- [ ] Network errors are distinguished from validation errors
- [ ] Error boundaries catch rendering crashes with a graceful fallback UI
- [ ] Failed API calls don't leave the UI in a broken state

### 4.3 Empty States
- [ ] Empty lists/tables show helpful messages, not blank space
- [ ] Empty states suggest next action ("Create your first project", "Start the questionnaire")
- [ ] Empty states are visually designed, not just text

### 4.4 Success States
- [ ] Successful actions provide confirmation feedback (toast, banner, or page transition)
- [ ] Destructive actions require confirmation before executing
- [ ] Form submissions clear or redirect appropriately after success

### 4.5 Wizard Flow (OnRamp-specific)
- [ ] Progress indicator shows current step and total steps
- [ ] Back button preserves previously entered answers
- [ ] "Unsure" option is available and clearly marked on choice questions
- [ ] Recommended options are visually highlighted
- [ ] Navigation between steps is smooth with no jarring layout shifts

## 5. Design System Enforcement

- [ ] No inline `style={}` props on any element
- [ ] No `className` with CSS module imports
- [ ] No `styled-components` or `emotion` usage
- [ ] Component spacing uses Fluent UI layout components (`Stack` → `flex` with tokens) or `makeStyles`
- [ ] Typography uses Fluent UI `Text`, `Title`, `Subtitle`, `Caption` components or token-based `makeStyles`
- [ ] Button variants match Fluent UI patterns: `appearance="primary"` for main action, `appearance="subtle"` for secondary
- [ ] Dialog/modal uses Fluent UI `Dialog` component — no custom modal implementations
- [ ] Form inputs use Fluent UI `Input`, `Textarea`, `Select`, `Checkbox`, `RadioGroup` — no native HTML form elements

## 6. Performance (Core Web Vitals)

- [ ] Page components are lazy-loaded with `React.lazy()` and `<Suspense>`
- [ ] Large lists use virtualization (if >50 items)
- [ ] Images are optimized and lazy-loaded where below the fold
- [ ] No unnecessary re-renders — `useCallback`/`useMemo` for expensive computations or stable references
- [ ] No layout shifts during loading — skeleton loaders match content dimensions (CLS)
- [ ] Interactive elements respond within 100ms of user input (FID/INP)
- [ ] Above-the-fold content renders within 2.5s (LCP)
- [ ] Bundle size impact considered — no large libraries imported for single-use

## 7. Usability Heuristics (Nielsen's 10)

- [ ] **Visibility of system status** — Users always know what's happening (loading, saving, error, success)
- [ ] **Match between system and real world** — Uses Azure/cloud terminology the target audience understands
- [ ] **User control and freedom** — Undo/back actions available; no destructive actions without confirmation
- [ ] **Consistency and standards** — Same action looks and behaves the same across all pages
- [ ] **Error prevention** — Input validation before submission; dangerous actions require confirmation
- [ ] **Recognition rather than recall** — Options visible in dropdowns/lists; no requirement to remember values
- [ ] **Flexibility and efficiency** — Keyboard shortcuts for power users; efficient flows for repeated tasks
- [ ] **Aesthetic and minimalist design** — No unnecessary information competing for attention
- [ ] **Help users recognize, diagnose, and recover from errors** — Plain-language error messages with next steps
- [ ] **Help and documentation** — Tooltips on complex fields; wizard guidance text; contextual help links

---

## How to Use This Checklist

**During code review (UX Agent):**
1. Review the PR diff against all applicable sections
2. Reference specific checklist items in review comments (e.g., "Fails §2.2 — missing keyboard Tab support")
3. Mark findings as Blocking (accessibility violations), High, Medium, or Low severity

**During development (Coder):**
1. Check applicable sections before opening a PR
2. Self-audit interactive components against §2 (Accessibility) and §4 (Interaction States)
3. Run keyboard-only navigation test on new components

**During audit (UX Agent initial audit):**
1. Evaluate every component and page against the full checklist
2. Create remediation issues grouped by severity
3. Prioritize: Accessibility (§2) > Interaction States (§4) > Design System (§5) > Performance (§6) > Responsive (§3) > Heuristics (§7)
