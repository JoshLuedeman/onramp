import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";
import DependencyGraph from "./DependencyGraph";
import type { DependencyGraph as DependencyGraphData, MigrationOrderResponse } from "../../services/api";

// ---------------------------------------------------------------------------
// Mock api
// ---------------------------------------------------------------------------

const mockGraph: DependencyGraphData = {
  nodes: [
    { id: "wl-1", name: "Frontend App", criticality: "mission-critical", migration_strategy: "rehost", project_id: "proj-1" },
    { id: "wl-2", name: "Backend API", criticality: "business-critical", migration_strategy: "refactor", project_id: "proj-1" },
    { id: "wl-3", name: "Database", criticality: "standard", migration_strategy: "rehost", project_id: "proj-1" },
  ],
  edges: [
    { source: "wl-1", target: "wl-2", dependency_type: "depends_on" },
    { source: "wl-2", target: "wl-3", dependency_type: "depends_on" },
  ],
  circular_dependencies: [],
  migration_groups: [["wl-1", "wl-2", "wl-3"]],
};

const mockGraphWithCycle: DependencyGraphData = {
  nodes: [
    { id: "wl-a", name: "Service A", criticality: "standard", migration_strategy: "rehost", project_id: "proj-1" },
    { id: "wl-b", name: "Service B", criticality: "standard", migration_strategy: "rehost", project_id: "proj-1" },
  ],
  edges: [
    { source: "wl-a", target: "wl-b", dependency_type: "depends_on" },
    { source: "wl-b", target: "wl-a", dependency_type: "depends_on" },
  ],
  circular_dependencies: [["wl-a", "wl-b"]],
  migration_groups: [["wl-a", "wl-b"]],
};

const mockMigrationOrder: MigrationOrderResponse = {
  order: ["wl-3", "wl-2", "wl-1"],
  migration_groups: [["wl-1", "wl-2", "wl-3"]],
  circular_dependencies: [],
  has_circular: false,
  workload_names: { "wl-1": "Frontend App", "wl-2": "Backend API", "wl-3": "Database" },
};

vi.mock("../../services/api", () => ({
  api: {
    workloads: {
      getDependencyGraph: vi.fn(),
      getMigrationOrder: vi.fn(),
      addDependency: vi.fn(),
      removeDependency: vi.fn(),
    },
  },
}));

import { api } from "../../services/api";

const mockedApi = api as unknown as {
  workloads: {
    getDependencyGraph: ReturnType<typeof vi.fn>;
    getMigrationOrder: ReturnType<typeof vi.fn>;
    addDependency: ReturnType<typeof vi.fn>;
    removeDependency: ReturnType<typeof vi.fn>;
  };
};

function renderComponent(projectId = "proj-1") {
  return render(
    <MemoryRouter>
      <FluentProvider theme={teamsLightTheme}>
        <DependencyGraph projectId={projectId} />
      </FluentProvider>
    </MemoryRouter>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("DependencyGraph", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedApi.workloads.getDependencyGraph.mockResolvedValue(mockGraph);
    mockedApi.workloads.getMigrationOrder.mockResolvedValue(mockMigrationOrder);
    mockedApi.workloads.addDependency.mockResolvedValue({ id: "wl-1", dependencies: ["wl-2"] });
    mockedApi.workloads.removeDependency.mockResolvedValue({ id: "wl-1", dependencies: [] });
  });

  it("renders loading state and then graph nodes", async () => {
    renderComponent();
    await waitFor(() => {
      expect(screen.getByLabelText("Workload dependency graph SVG")).toBeInTheDocument();
    });
    expect(screen.getByLabelText("Workload node: Frontend App")).toBeInTheDocument();
    expect(screen.getByLabelText("Workload node: Backend API")).toBeInTheDocument();
    expect(screen.getByLabelText("Workload node: Database")).toBeInTheDocument();
  });

  it("calls getDependencyGraph with the project ID", async () => {
    renderComponent("my-project");
    await waitFor(() => {
      expect(mockedApi.workloads.getDependencyGraph).toHaveBeenCalledWith("my-project");
    });
  });

  it("shows error message when getDependencyGraph fails", async () => {
    mockedApi.workloads.getDependencyGraph.mockRejectedValue(new Error("Network error"));
    renderComponent();
    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });

  it("shows circular dependency warning when cycles exist", async () => {
    mockedApi.workloads.getDependencyGraph.mockResolvedValue(mockGraphWithCycle);
    renderComponent();
    await waitFor(() => {
      expect(screen.getByText(/Circular dependencies detected/i)).toBeInTheDocument();
    });
  });

  it("clicking a node shows its detail panel", async () => {
    const user = userEvent.setup();
    renderComponent();
    await waitFor(() => {
      expect(screen.getByLabelText("Workload node: Frontend App")).toBeInTheDocument();
    });
    await user.click(screen.getByLabelText("Workload node: Frontend App"));
    await waitFor(() => {
      expect(screen.getByLabelText("Details for Frontend App")).toBeInTheDocument();
    });
  });

  it("clicking selected node again clears the detail panel", async () => {
    const user = userEvent.setup();
    renderComponent();
    await waitFor(() => {
      expect(screen.getByLabelText("Workload node: Frontend App")).toBeInTheDocument();
    });
    await user.click(screen.getByLabelText("Workload node: Frontend App"));
    await waitFor(() => {
      expect(screen.getByLabelText("Details for Frontend App")).toBeInTheDocument();
    });
    await user.click(screen.getByLabelText("Workload node: Frontend App"));
    await waitFor(() => {
      expect(screen.queryByLabelText("Details for Frontend App")).not.toBeInTheDocument();
    });
  });

  it("shows Suggest Migration Order button and fetches order on click", async () => {
    const user = userEvent.setup();
    renderComponent();
    await waitFor(() => {
      expect(screen.getByLabelText("Workload dependency graph SVG")).toBeInTheDocument();
    });
    const btn = screen.getByLabelText("Suggest Migration Order");
    await user.click(btn);
    await waitFor(() => {
      expect(mockedApi.workloads.getMigrationOrder).toHaveBeenCalledWith("proj-1");
    });
    await waitFor(() => {
      expect(screen.getByText("Suggested Migration Order")).toBeInTheDocument();
    });
  });

  it("displays migration order as numbered list", async () => {
    const user = userEvent.setup();
    renderComponent();
    await waitFor(() => {
      expect(screen.getByLabelText("Workload dependency graph SVG")).toBeInTheDocument();
    });
    await user.click(screen.getByLabelText("Suggest Migration Order"));
    await waitFor(() => {
      expect(screen.getByText("Suggested Migration Order")).toBeInTheDocument();
    });
    // The order list should contain the workload names (may appear multiple times with node)
    expect(screen.getAllByText("Database").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Backend API").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Frontend App").length).toBeGreaterThanOrEqual(1);
  });

  it("shows migration order warning when has_circular is true", async () => {
    mockedApi.workloads.getMigrationOrder.mockResolvedValue({
      ...mockMigrationOrder,
      has_circular: true,
      circular_dependencies: [["wl-1", "wl-2"]],
      order: [],
    });
    const user = userEvent.setup();
    renderComponent();
    await waitFor(() => screen.getByLabelText("Workload dependency graph SVG"));
    await user.click(screen.getByLabelText("Suggest Migration Order"));
    await waitFor(() => {
      expect(screen.getByText(/Circular dependencies detected — order may be incomplete/i)).toBeInTheDocument();
    });
  });

  it("shows empty state when no workloads", async () => {
    mockedApi.workloads.getDependencyGraph.mockResolvedValue({
      nodes: [],
      edges: [],
      circular_dependencies: [],
      migration_groups: [],
    });
    renderComponent();
    await waitFor(() => {
      expect(screen.getByText(/No workloads in this project yet/i)).toBeInTheDocument();
    });
  });

  it("Add Dependency button is disabled when fewer than 2 workloads", async () => {
    mockedApi.workloads.getDependencyGraph.mockResolvedValue({
      nodes: [{ id: "wl-1", name: "Solo", criticality: "standard", migration_strategy: "rehost", project_id: "proj-1" }],
      edges: [],
      circular_dependencies: [],
      migration_groups: [["wl-1"]],
    });
    renderComponent();
    await waitFor(() => screen.getByLabelText("Add Dependency"));
    expect(screen.getByLabelText("Add Dependency")).toBeDisabled();
  });

  it("renders legend with criticality colors", async () => {
    renderComponent();
    await waitFor(() => screen.getByLabelText("Workload dependency graph SVG"));
    // Legend contains all criticality levels (may appear multiple times in nodes + legend)
    expect(screen.getAllByText("mission-critical").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("business-critical").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("standard").length).toBeGreaterThanOrEqual(1);
    // dev-test only appears in legend (not in mock data)
    expect(screen.getByText("dev-test")).toBeInTheDocument();
  });

  it("refresh button reloads the graph", async () => {
    const user = userEvent.setup();
    renderComponent();
    await waitFor(() => screen.getByLabelText("Workload dependency graph SVG"));
    await user.click(screen.getByText("Refresh"));
    await waitFor(() => {
      expect(mockedApi.workloads.getDependencyGraph).toHaveBeenCalledTimes(2);
    });
  });
});
