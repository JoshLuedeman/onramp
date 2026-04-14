import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import Layout from "./Layout";

// Mock useAuth used by AuthButton
vi.mock("../../auth", () => ({
  useAuth: () => ({
    isAuthenticated: false,
    user: null,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

const mockProjectsList = vi.fn();

vi.mock("../../services/api", () => ({
  api: {
    projects: {
      list: (...args: unknown[]) => mockProjectsList(...args),
    },
  },
}));

function renderLayout(children = <div>Test Content</div>, initialRoute = "/") {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter initialEntries={[initialRoute]}>
        <Layout>{children}</Layout>
      </MemoryRouter>
    </FluentProvider>
  );
}

describe("Layout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockProjectsList.mockResolvedValue({ projects: [] });
  });

  it("renders OnRamp title", () => {
    renderLayout();
    expect(screen.getByText("OnRamp", { exact: false })).toBeInTheDocument();
  });

  it("renders navigation tabs", () => {
    renderLayout();
    expect(screen.getByRole("tab", { name: /Home/ })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Wizard/ })).toBeInTheDocument();
  });

  it("renders children content", () => {
    renderLayout(<div>My Content</div>);
    expect(screen.getByText("My Content")).toBeInTheDocument();
  });

  it("has architecture tab", () => {
    renderLayout();
    expect(screen.getByRole("tab", { name: /Architecture/ })).toBeInTheDocument();
  });

  it("shows project switcher when projects exist", async () => {
    mockProjectsList.mockResolvedValue({
      projects: [
        { id: "p1", name: "Project Alpha", status: "draft", description: null, created_at: "2024-01-01", updated_at: "2024-01-01" },
      ],
    });
    renderLayout();
    await waitFor(() => {
      expect(screen.getByLabelText("Switch project")).toBeInTheDocument();
    });
  });

  it("hides project switcher when no projects", async () => {
    mockProjectsList.mockResolvedValue({ projects: [] });
    renderLayout();
    // Wait for the effect to settle
    await waitFor(() => {
      expect(mockProjectsList).toHaveBeenCalled();
    });
    expect(screen.queryByLabelText("Switch project")).not.toBeInTheDocument();
  });
});
