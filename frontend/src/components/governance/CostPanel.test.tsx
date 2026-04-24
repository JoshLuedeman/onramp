import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";

// ── Mocks ───────────────────────────────────────────────────────────────────

vi.mock("../../services/api", () => ({
  api: {
    governance: {
      cost: {
        getSummary: vi.fn(),
        getBudget: vi.fn(),
      },
    },
  },
}));

import CostPanel from "./CostPanel";
import { api } from "../../services/api";

const mockedApi = api as unknown as {
  governance: {
    cost: {
      getSummary: ReturnType<typeof vi.fn>;
      getBudget: ReturnType<typeof vi.fn>;
    };
  };
};

// ── Test data ───────────────────────────────────────────────────────────────

const sampleCostSummary = {
  total_monthly_cost: 4250.0,
  currency: "USD",
  top_services: [
    { service: "Virtual Machines", cost: 1800.0 },
    { service: "SQL Database", cost: 950.0 },
    { service: "Storage", cost: 320.0 },
  ],
  trend: "increasing",
  change_percentage: 12.5,
  last_updated: "2025-07-27T10:00:00Z",
};

const sampleBudget = {
  budget_amount: 5000.0,
  current_spend: 4250.0,
  utilization_percentage: 85.0,
  forecast_end_of_month: 5100.0,
  currency: "USD",
  alerts: [
    { threshold: 80, triggered: true, message: "Budget 80% utilized" },
    { threshold: 100, triggered: false, message: "Budget exceeded" },
  ],
};

// ── Helper ──────────────────────────────────────────────────────────────────

function renderCostPanel(projectId = "default") {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>
        <CostPanel projectId={projectId} />
      </MemoryRouter>
    </FluentProvider>,
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("CostPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading spinner initially", () => {
    mockedApi.governance.cost.getSummary.mockReturnValue(new Promise(() => {}));
    mockedApi.governance.cost.getBudget.mockReturnValue(new Promise(() => {}));
    renderCostPanel();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("shows cost summary after data loads", async () => {
    mockedApi.governance.cost.getSummary.mockResolvedValue(sampleCostSummary);
    mockedApi.governance.cost.getBudget.mockResolvedValue(sampleBudget);
    renderCostPanel();
    await waitFor(() => {
      expect(screen.getByText(/4,250/)).toBeInTheDocument();
    });
  });

  it("displays top services breakdown", async () => {
    mockedApi.governance.cost.getSummary.mockResolvedValue(sampleCostSummary);
    mockedApi.governance.cost.getBudget.mockResolvedValue(sampleBudget);
    renderCostPanel();
    await waitFor(() => {
      expect(screen.getByText("Virtual Machines")).toBeInTheDocument();
    });
    expect(screen.getByText("SQL Database")).toBeInTheDocument();
    expect(screen.getByText("Storage")).toBeInTheDocument();
  });

  it("shows budget utilization percentage", async () => {
    mockedApi.governance.cost.getSummary.mockResolvedValue(sampleCostSummary);
    mockedApi.governance.cost.getBudget.mockResolvedValue(sampleBudget);
    renderCostPanel();
    await waitFor(() => {
      expect(screen.getByText(/85%/)).toBeInTheDocument();
    });
  });

  it("shows budget amount", async () => {
    mockedApi.governance.cost.getSummary.mockResolvedValue(sampleCostSummary);
    mockedApi.governance.cost.getBudget.mockResolvedValue(sampleBudget);
    renderCostPanel();
    await waitFor(() => {
      expect(screen.getByText(/5,000/)).toBeInTheDocument();
    });
  });

  it("handles API error state for cost summary", async () => {
    mockedApi.governance.cost.getSummary.mockRejectedValue(
      new Error("Network error"),
    );
    mockedApi.governance.cost.getBudget.mockResolvedValue(sampleBudget);
    renderCostPanel();
    await waitFor(() => {
      expect(screen.getByText(/failed|error/i)).toBeInTheDocument();
    });
  });

  it("handles API error state for budget", async () => {
    mockedApi.governance.cost.getSummary.mockResolvedValue(sampleCostSummary);
    mockedApi.governance.cost.getBudget.mockRejectedValue(
      new Error("Network error"),
    );
    renderCostPanel();
    await waitFor(() => {
      expect(screen.getByText(/failed|error/i)).toBeInTheDocument();
    });
  });

  it("calls getSummary with correct project ID", async () => {
    mockedApi.governance.cost.getSummary.mockResolvedValue(sampleCostSummary);
    mockedApi.governance.cost.getBudget.mockResolvedValue(sampleBudget);
    renderCostPanel("proj-456");
    await waitFor(() => {
      expect(mockedApi.governance.cost.getSummary).toHaveBeenCalledWith(
        "proj-456",
      );
    });
  });

  it("calls getBudget with correct project ID", async () => {
    mockedApi.governance.cost.getSummary.mockResolvedValue(sampleCostSummary);
    mockedApi.governance.cost.getBudget.mockResolvedValue(sampleBudget);
    renderCostPanel("proj-456");
    await waitFor(() => {
      expect(mockedApi.governance.cost.getBudget).toHaveBeenCalledWith(
        "proj-456",
      );
    });
  });

  it("shows cost trend indicator", async () => {
    mockedApi.governance.cost.getSummary.mockResolvedValue(sampleCostSummary);
    mockedApi.governance.cost.getBudget.mockResolvedValue(sampleBudget);
    renderCostPanel();
    await waitFor(() => {
      expect(screen.getByText(/12\.5%/)).toBeInTheDocument();
    });
  });
});
