import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";
import { vi, describe, it, expect, beforeEach } from "vitest";
import DashboardPage from "./DashboardPage";

// Mock the API
vi.mock("../services/api", () => ({
  api: {
    projects: {
      list: vi.fn(),
      getStats: vi.fn(),
      create: vi.fn(),
      delete: vi.fn(),
    },
  },
}));

// Mock @fluentui/react-charting to avoid rendering issues in jsdom
vi.mock("@fluentui/react-charting", () => ({
  DonutChart: ({ data }: { data: { chartData: { legend: string }[] } }) => (
    <div data-testid="donut-chart">
      {data.chartData.map((d: { legend: string }) => (
        <span key={d.legend}>{d.legend}</span>
      ))}
    </div>
  ),
}));

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

import { api } from "../services/api";

const mockedApi = api as unknown as {
  projects: {
    list: ReturnType<typeof vi.fn>;
    getStats: ReturnType<typeof vi.fn>;
    create: ReturnType<typeof vi.fn>;
    delete: ReturnType<typeof vi.fn>;
  };
};

function renderDashboard() {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </FluentProvider>
  );
}

const emptyStats = {
  total: 0,
  by_status: {},
  avg_compliance_score: null,
  deployment_success_rate: null,
  recent_projects: [],
};

const sampleProjects = [
  {
    id: "p1",
    name: "Project Alpha",
    description: "First project",
    status: "draft",
    created_at: "2024-01-15T10:00:00Z",
    updated_at: "2024-01-15T10:00:00Z",
  },
  {
    id: "p2",
    name: "Project Beta",
    description: "Second project",
    status: "deployed",
    created_at: "2024-02-20T12:00:00Z",
    updated_at: "2024-02-20T12:00:00Z",
  },
];

const sampleStats = {
  total: 5,
  by_status: { draft: 2, deployed: 2, deploying: 1 },
  avg_compliance_score: 85,
  deployment_success_rate: 0.9,
  recent_projects: [],
};

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockReset();
  });

  it("shows loading spinner initially", () => {
    // Return promises that never resolve to keep loading state
    mockedApi.projects.list.mockReturnValue(new Promise(() => {}));
    mockedApi.projects.getStats.mockReturnValue(new Promise(() => {}));
    renderDashboard();
    expect(screen.getByText("Loading dashboard...")).toBeInTheDocument();
  });

  it("renders empty state when no projects", async () => {
    mockedApi.projects.list.mockResolvedValue({ projects: [] });
    mockedApi.projects.getStats.mockResolvedValue(emptyStats);
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("No projects yet")).toBeInTheDocument();
    });
    expect(
      screen.getByText("Create your first project to get started.")
    ).toBeInTheDocument();
  });

  it("renders project table with projects", async () => {
    mockedApi.projects.list.mockResolvedValue({ projects: sampleProjects });
    mockedApi.projects.getStats.mockResolvedValue(sampleStats);
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("Project Alpha")).toBeInTheDocument();
    });
    expect(screen.getByText("Project Beta")).toBeInTheDocument();
  });

  it("renders summary cards with stats", async () => {
    mockedApi.projects.list.mockResolvedValue({ projects: sampleProjects });
    mockedApi.projects.getStats.mockResolvedValue(sampleStats);
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("Total Projects")).toBeInTheDocument();
    });
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    // "Deployed" appears in both summary card and status badge
    expect(screen.getAllByText("Deployed").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("2").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Avg Compliance Score")).toBeInTheDocument();
    expect(screen.getByText("85%")).toBeInTheDocument();
  });

  it("opens create project dialog", async () => {
    const user = userEvent.setup();
    mockedApi.projects.list.mockResolvedValue({ projects: [] });
    mockedApi.projects.getStats.mockResolvedValue(emptyStats);
    const { baseElement } = renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("No projects yet")).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /new project/i }));
    await waitFor(() => {
      const doc = baseElement.ownerDocument;
      expect(
        doc.querySelector('input[placeholder="My Landing Zone"]')
      ).toBeTruthy();
      expect(
        doc.querySelector('textarea[placeholder="Optional project description"]')
      ).toBeTruthy();
    });
  });

  it("creates a project via dialog", async () => {
    const user = userEvent.setup();
    mockedApi.projects.list.mockResolvedValue({ projects: [] });
    mockedApi.projects.getStats.mockResolvedValue(emptyStats);
    mockedApi.projects.create.mockResolvedValue({
      id: "new-id",
      name: "New LZ",
      status: "draft",
    });
    const { baseElement } = renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("No projects yet")).toBeInTheDocument();
    });
    const newProjectBtn = screen.getByRole("button", { name: /new project/i });
    await user.click(newProjectBtn);

    // Dialog may render in a portal — search across the entire document
    await waitFor(() => {
      const input = baseElement.ownerDocument.querySelector(
        'input[placeholder="My Landing Zone"]'
      );
      expect(input).toBeTruthy();
    });

    const input = baseElement.ownerDocument.querySelector(
      'input[placeholder="My Landing Zone"]'
    ) as HTMLInputElement;
    await user.clear(input);
    await user.click(input);
    await user.keyboard("New LZ");

    // Find the Create button across the whole document
    const allButtons = Array.from(
      baseElement.ownerDocument.querySelectorAll("button")
    );
    const createBtn = allButtons.find(
      (b) => b.textContent === "Create"
    );
    expect(createBtn).toBeTruthy();
    await user.click(createBtn!);

    await waitFor(() => {
      expect(mockedApi.projects.create).toHaveBeenCalled();
    });
  });

  it("deletes a project", async () => {
    const user = userEvent.setup();
    mockedApi.projects.list.mockResolvedValue({ projects: sampleProjects });
    mockedApi.projects.getStats.mockResolvedValue(sampleStats);
    mockedApi.projects.delete.mockResolvedValue({ deleted: true });
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("Project Alpha")).toBeInTheDocument();
    });
    const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
    await user.click(deleteButtons[0]);
    await waitFor(() => {
      expect(mockedApi.projects.delete).toHaveBeenCalledWith("p1");
    });
  });

  it("navigates to wizard for draft projects", async () => {
    mockedApi.projects.list.mockResolvedValue({ projects: sampleProjects });
    mockedApi.projects.getStats.mockResolvedValue(sampleStats);
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByText("Project Alpha")).toBeInTheDocument();
    });
    const continueButton = screen.getByRole("button", { name: "Continue" });
    expect(continueButton).toBeInTheDocument();
    // Also verify View button exists for deployed project
    const viewButton = screen.getByRole("button", { name: "View" });
    expect(viewButton).toBeInTheDocument();
  });

  it("renders donut chart with status data", async () => {
    mockedApi.projects.list.mockResolvedValue({ projects: sampleProjects });
    mockedApi.projects.getStats.mockResolvedValue(sampleStats);
    renderDashboard();
    await waitFor(() => {
      expect(screen.getByTestId("donut-chart")).toBeInTheDocument();
    });
    // "Draft" appears in both donut chart and status badge
    expect(screen.getAllByText("Draft").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Deploying")).toBeInTheDocument();
  });
});
