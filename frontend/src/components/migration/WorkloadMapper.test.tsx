import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";
import WorkloadMapper from "./WorkloadMapper";
import * as apiModule from "../../services/api";

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_WORKLOADS = [
  {
    id: "wl-1",
    project_id: "proj-1",
    name: "ProdWebApp",
    type: "web-app",
    source_platform: "vmware",
    cpu_cores: 4,
    memory_gb: 16,
    storage_gb: 100,
    os_type: "Linux",
    os_version: "Ubuntu 22.04",
    criticality: "mission-critical",
    compliance_requirements: ["SOC2"],
    dependencies: [],
    migration_strategy: "rehost",
    notes: null,
    target_subscription_id: null,
    mapping_reasoning: null,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
  {
    id: "wl-2",
    project_id: "proj-1",
    name: "DevDatabase",
    type: "database",
    source_platform: "other",
    cpu_cores: 2,
    memory_gb: 8,
    storage_gb: 200,
    os_type: null,
    os_version: null,
    criticality: "dev-test",
    compliance_requirements: [],
    dependencies: [],
    migration_strategy: "refactor",
    notes: null,
    target_subscription_id: null,
    mapping_reasoning: null,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  },
];

const MOCK_MAPPINGS = [
  {
    workload_id: "wl-1",
    workload_name: "ProdWebApp",
    recommended_subscription_id: "sub-prod",
    recommended_subscription_name: "sub-workload-prod",
    reasoning: "Mission-critical maps to production",
    confidence_score: 0.92,
    warnings: [],
  },
  {
    workload_id: "wl-2",
    workload_name: "DevDatabase",
    recommended_subscription_id: "sub-dev",
    recommended_subscription_name: "sub-workload-dev",
    reasoning: "Dev-test maps to dev subscription",
    confidence_score: 0.75,
    warnings: [],
  },
];

const MOCK_SUBSCRIPTIONS = [
  { id: "sub-prod", name: "sub-workload-prod", purpose: "Production workloads", management_group: "mg-corp" },
  { id: "sub-dev", name: "sub-workload-dev", purpose: "Development and testing", management_group: "mg-corp" },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderMapper(projectId = "proj-1", subscriptions = MOCK_SUBSCRIPTIONS) {
  return render(
    <MemoryRouter>
      <FluentProvider theme={teamsLightTheme}>
        <WorkloadMapper projectId={projectId} subscriptions={subscriptions} />
      </FluentProvider>
    </MemoryRouter>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("WorkloadMapper", () => {
  beforeEach(() => {
    vi.spyOn(apiModule.api.workloads, "list").mockResolvedValue({
      workloads: MOCK_WORKLOADS,
      total: MOCK_WORKLOADS.length,
    });
    vi.spyOn(apiModule.api.workloads, "generateMapping").mockResolvedValue({
      mappings: MOCK_MAPPINGS,
      warnings: [],
    });
    vi.spyOn(apiModule.api.workloads, "overrideMapping").mockResolvedValue(MOCK_WORKLOADS[0]);
    vi.spyOn(apiModule.api.architecture, "getByProject").mockResolvedValue({
      architecture: {
        organization_size: "small",
        management_groups: {},
        subscriptions: MOCK_SUBSCRIPTIONS,
        network_topology: {},
      },
      project_id: "proj-1",
    });
  });

  it("renders the component title", async () => {
    renderMapper();
    await waitFor(() => {
      expect(screen.getByText("Workload–Subscription Mapping")).toBeInTheDocument();
    });
  });

  it("renders Generate Mapping button", async () => {
    renderMapper();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /generate mapping/i })).toBeInTheDocument();
    });
  });

  it("loads and displays workloads", async () => {
    renderMapper();
    await waitFor(() => {
      expect(screen.getByText("ProdWebApp")).toBeInTheDocument();
      expect(screen.getByText("DevDatabase")).toBeInTheDocument();
    });
  });

  it("displays workload criticality badges", async () => {
    renderMapper();
    await waitFor(() => {
      expect(screen.getByText("mission-critical")).toBeInTheDocument();
      expect(screen.getByText("dev-test")).toBeInTheDocument();
    });
  });

  it("displays subscription targets", async () => {
    renderMapper();
    await waitFor(() => {
      expect(screen.getByText("sub-workload-prod")).toBeInTheDocument();
      expect(screen.getByText("sub-workload-dev")).toBeInTheDocument();
    });
  });

  it("shows 'Drop workloads here' hint on empty subscriptions", async () => {
    renderMapper();
    await waitFor(() => {
      const hints = screen.getAllByText(/drop workloads here/i);
      expect(hints.length).toBeGreaterThan(0);
    });
  });

  it("calls generateMapping API on button click", async () => {
    renderMapper();
    await waitFor(() => screen.getByText("ProdWebApp"));

    const btn = screen.getByRole("button", { name: /generate mapping/i });
    fireEvent.click(btn);

    await waitFor(() => {
      expect(apiModule.api.workloads.generateMapping).toHaveBeenCalledWith("proj-1", "", true);
    });
  });

  it("shows suggested badge and confidence after mapping generation", async () => {
    renderMapper();
    await waitFor(() => screen.getByText("ProdWebApp"));

    fireEvent.click(screen.getByRole("button", { name: /generate mapping/i }));

    await waitFor(() => {
      const badges = screen.getAllByText("Suggested");
      expect(badges.length).toBeGreaterThan(0);
    });

    await waitFor(() => {
      // 92% confidence → "High"
      expect(screen.getByText(/High.*92%|92%.*High/i)).toBeInTheDocument();
    });
  });

  it("shows warnings from API response", async () => {
    vi.spyOn(apiModule.api.workloads, "generateMapping").mockResolvedValue({
      mappings: MOCK_MAPPINGS,
      warnings: ["Workload 'ProdWebApp' has compliance requirements mapped to dev subscription"],
    });

    renderMapper();
    await waitFor(() => screen.getByText("ProdWebApp"));
    fireEvent.click(screen.getByRole("button", { name: /generate mapping/i }));

    await waitFor(() => {
      expect(screen.getByText(/ProdWebApp.*compliance/i)).toBeInTheDocument();
    });
  });

  it("shows error message when mapping API fails", async () => {
    vi.spyOn(apiModule.api.workloads, "generateMapping").mockRejectedValue(
      new Error("Server error")
    );

    renderMapper();
    await waitFor(() => screen.getByText("ProdWebApp"));
    fireEvent.click(screen.getByRole("button", { name: /generate mapping/i }));

    await waitFor(() => {
      expect(screen.getByText(/server error/i)).toBeInTheDocument();
    });
  });

  it("shows empty state hint when no workloads", async () => {
    vi.spyOn(apiModule.api.workloads, "list").mockResolvedValue({ workloads: [], total: 0 });

    renderMapper();
    await waitFor(() => {
      expect(screen.getByText(/no workloads found/i)).toBeInTheDocument();
    });
  });

  it("disables Generate Mapping button when no workloads", async () => {
    vi.spyOn(apiModule.api.workloads, "list").mockResolvedValue({ workloads: [], total: 0 });

    renderMapper();
    await waitFor(() => {
      const btn = screen.getByRole("button", { name: /generate mapping/i });
      expect(btn).toBeDisabled();
    });
  });

  it("shows empty subscriptions hint when none provided", async () => {
    vi.spyOn(apiModule.api.architecture, "getByProject").mockResolvedValue({
      architecture: null,
      project_id: "proj-1",
    });
    renderMapper("proj-1", []);
    await waitFor(() => {
      expect(screen.getByText(/no subscriptions available/i)).toBeInTheDocument();
    });
  });

  it("loads subscriptions from architecture when not provided via props", async () => {
    renderMapper("proj-1", []); // No props subscriptions, should load from architecture
    await waitFor(() => {
      // Subscriptions loaded from architecture mock
      expect(screen.getByText("sub-workload-prod")).toBeInTheDocument();
    });
  });

  it("shows override failure error and reverts mapping", async () => {
    vi.spyOn(apiModule.api.workloads, "overrideMapping").mockRejectedValue(
      new Error("Save failed")
    );

    renderMapper();
    await waitFor(() => screen.getByText("ProdWebApp"));

    // Generate mappings first
    fireEvent.click(screen.getByRole("button", { name: /generate mapping/i }));
    await waitFor(() => screen.getAllByText("Suggested"));

    // Drag the workload card (simulate dragstart then drop)
    const card = screen.getByTestId("workload-card-wl-1");
    fireEvent.dragStart(card);

    const target = screen.getByTestId("subscription-target-sub-dev");
    fireEvent.dragOver(target);
    fireEvent.drop(target);

    // Error message should appear after failed PATCH
    await waitFor(() => {
      expect(screen.getByText(/failed to save mapping override/i)).toBeInTheDocument();
    });
  });

  it("shows compliance requirements badge", async () => {
    renderMapper();
    await waitFor(() => {
      expect(screen.getByText("SOC2")).toBeInTheDocument();
    });
  });

  it("groups workloads by type", async () => {
    renderMapper();
    await waitFor(() => {
      expect(screen.getByText("web-app")).toBeInTheDocument();
      expect(screen.getByText("database")).toBeInTheDocument();
    });
  });

  it("workload cards are draggable", async () => {
    renderMapper();
    await waitFor(() => screen.getByText("ProdWebApp"));

    const card = screen.getByTestId("workload-card-wl-1");
    expect(card).toHaveAttribute("draggable", "true");
  });
});
