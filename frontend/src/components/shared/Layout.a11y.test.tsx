/**
 * Layout WCAG 2.1 AA accessibility tests.
 *
 * Tests navigation semantics, accessible labels, main content landmark,
 * heading hierarchy, and tab-based navigation.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";
import Layout from "./Layout";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("../../services/api", () => ({
  api: {
    projects: {
      list: vi.fn().mockResolvedValue({ projects: [] }),
    },
  },
}));

vi.mock("../../auth", () => ({
  useAuth: () => ({
    isAuthenticated: false,
    user: null,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

vi.mock("../../hooks/useTutorial", () => ({
  useTutorial: () => ({
    isActive: false,
    currentStep: null,
    currentStepIndex: 0,
    totalSteps: 0,
    startTutorial: vi.fn(),
    nextStep: vi.fn(),
    prevStep: vi.fn(),
    skipTutorial: vi.fn(),
  }),
}));

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function renderLayout(children: React.ReactNode = <h1>Test Page</h1>) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter initialEntries={["/"]}>
        <Layout>{children}</Layout>
      </MemoryRouter>
    </FluentProvider>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("Layout Accessibility", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // 1 — Navigation tabs are rendered within a tablist role (Fluent TabList)
  it("renders navigation with tablist role", () => {
    renderLayout();
    const tablist = screen.getByRole("tablist");
    expect(tablist).toBeInTheDocument();
  });

  // 2 — Each navigation item has an accessible tab role
  it("navigation items have tab role with accessible names", () => {
    renderLayout();
    const tabs = screen.getAllByRole("tab");
    expect(tabs.length).toBeGreaterThanOrEqual(6);

    // Verify each nav item has an accessible name
    const expectedLabels = ["Home", "Wizard", "Architecture", "Compliance", "Bicep", "Deploy"];
    for (const label of expectedLabels) {
      expect(screen.getByRole("tab", { name: label })).toBeInTheDocument();
    }
  });

  // 3 — Main content area uses <main> element
  it("main content area uses semantic <main> element", () => {
    renderLayout(<h1>Dashboard</h1>);
    const mainEl = screen.getByRole("main");
    expect(mainEl).toBeInTheDocument();
  });

  // 4 — Children are rendered inside the main landmark
  it("children are rendered inside the main landmark", () => {
    renderLayout(<h1>Dashboard</h1>);
    const mainEl = screen.getByRole("main");
    expect(within(mainEl).getByText("Dashboard")).toBeInTheDocument();
  });

  // 5 — Heading hierarchy: h1 is present when children include one
  it("heading hierarchy: h1 is present inside main content", () => {
    renderLayout(<h1>Welcome to OnRamp</h1>);
    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading).toBeInTheDocument();
    expect(heading).toHaveTextContent("Welcome to OnRamp");
  });

  // 6 — Header uses <header> element
  it("renders a semantic <header> element", () => {
    renderLayout();
    const headerEl = document.querySelector("header");
    expect(headerEl).toBeInTheDocument();
  });

  // 7 — Tutorial button has accessible label
  it("tutorial button has accessible label", () => {
    renderLayout();
    expect(screen.getByLabelText("Start tutorial")).toBeInTheDocument();
  });

  // 8 — Project switcher dropdown has aria-label when rendered
  it("project switcher dropdown has aria-label when projects exist", async () => {
    const { api } = await import("../../services/api");
    (api.projects.list as ReturnType<typeof vi.fn>).mockResolvedValue({
      projects: [
        { id: "p1", name: "Project Alpha" },
        { id: "p2", name: "Project Beta" },
      ],
    });

    renderLayout();

    const dropdown = await screen.findByLabelText("Switch project");
    expect(dropdown).toBeInTheDocument();
  });

  // 9 — Selected tab has aria-selected="true"
  it("current route tab has aria-selected=true", () => {
    renderLayout();
    const homeTab = screen.getByRole("tab", { name: "Home" });
    expect(homeTab).toHaveAttribute("aria-selected", "true");
  });

  // 10 — Non-selected tabs have aria-selected="false"
  it("non-current route tabs have aria-selected=false", () => {
    renderLayout();
    const wizardTab = screen.getByRole("tab", { name: "Wizard" });
    expect(wizardTab).toHaveAttribute("aria-selected", "false");
  });
});
