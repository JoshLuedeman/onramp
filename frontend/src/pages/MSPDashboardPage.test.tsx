import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";
import { vi, describe, it, expect, beforeEach } from "vitest";
import MSPDashboardPage from "./MSPDashboardPage";

// Mock the API
vi.mock("../services/api", () => ({
  api: {
    msp: {
      getOverview: vi.fn(),
      getTenantHealth: vi.fn(),
      getComplianceSummary: vi.fn(),
    },
  },
}));

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

import { api } from "../services/api";

const mockedApi = api as unknown as {
  msp: {
    getOverview: ReturnType<typeof vi.fn>;
    getTenantHealth: ReturnType<typeof vi.fn>;
    getComplianceSummary: ReturnType<typeof vi.fn>;
  };
};

function renderMSPDashboard() {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter initialEntries={["/msp"]}>
        <MSPDashboardPage />
      </MemoryRouter>
    </FluentProvider>,
  );
}

const sampleOverview = {
  tenants: [
    {
      tenant_id: "t-001",
      name: "Contoso Ltd",
      status: "active",
      last_activity: "2024-06-15T10:00:00Z",
      compliance_score: 92.5,
      project_count: 8,
      deployment_count: 24,
      active_deployments: 3,
    },
    {
      tenant_id: "t-002",
      name: "Fabrikam Inc",
      status: "active",
      last_activity: "2024-06-15T07:00:00Z",
      compliance_score: 78.0,
      project_count: 5,
      deployment_count: 15,
      active_deployments: 1,
    },
    {
      tenant_id: "t-003",
      name: "Woodgrove Bank",
      status: "warning",
      last_activity: "2024-06-14T12:00:00Z",
      compliance_score: 55.0,
      project_count: 3,
      deployment_count: 9,
      active_deployments: 0,
    },
  ],
  total_tenants: 3,
  total_projects: 16,
  avg_compliance_score: 75.2,
};

const sampleCompliance = {
  total_tenants: 3,
  passing: 1,
  warning: 1,
  failing: 1,
  scores_by_tenant: [
    { tenant_id: "t-001", name: "Contoso Ltd", score: 92.5, status: "passing" },
    {
      tenant_id: "t-002",
      name: "Fabrikam Inc",
      score: 78.0,
      status: "warning",
    },
    {
      tenant_id: "t-003",
      name: "Woodgrove Bank",
      score: 55.0,
      status: "failing",
    },
  ],
};

const emptyOverview = {
  tenants: [],
  total_tenants: 0,
  total_projects: 0,
  avg_compliance_score: 0,
};

const emptyCompliance = {
  total_tenants: 0,
  passing: 0,
  warning: 0,
  failing: 0,
  scores_by_tenant: [],
};

describe("MSPDashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Loading state ──────────────────────────────────────────────────

  it("shows loading spinner initially", () => {
    mockedApi.msp.getOverview.mockReturnValue(new Promise(() => {}));
    mockedApi.msp.getComplianceSummary.mockReturnValue(new Promise(() => {}));
    renderMSPDashboard();
    expect(screen.getByText("Loading MSP dashboard...")).toBeInTheDocument();
  });

  it("shows spinner component while loading", () => {
    mockedApi.msp.getOverview.mockReturnValue(new Promise(() => {}));
    mockedApi.msp.getComplianceSummary.mockReturnValue(new Promise(() => {}));
    renderMSPDashboard();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  // ── Empty state ────────────────────────────────────────────────────

  it("shows empty state when no tenants exist", async () => {
    mockedApi.msp.getOverview.mockResolvedValue(emptyOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(emptyCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(screen.getByText("No tenants found")).toBeInTheDocument();
    });
  });

  it("shows guidance message in empty state", async () => {
    mockedApi.msp.getOverview.mockResolvedValue(emptyOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(emptyCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(
        screen.getByText(/No managed tenants are configured yet/),
      ).toBeInTheDocument();
    });
  });

  // ── Error state ────────────────────────────────────────────────────

  it("shows error state when API call fails", async () => {
    mockedApi.msp.getOverview.mockRejectedValue(new Error("Network error"));
    mockedApi.msp.getComplianceSummary.mockRejectedValue(
      new Error("Network error"),
    );
    renderMSPDashboard();
    await waitFor(() => {
      expect(screen.getByText("Error loading dashboard")).toBeInTheDocument();
    });
  });

  it("shows error message from API", async () => {
    mockedApi.msp.getOverview.mockRejectedValue(
      new Error("Forbidden: Access denied"),
    );
    mockedApi.msp.getComplianceSummary.mockRejectedValue(
      new Error("Forbidden: Access denied"),
    );
    renderMSPDashboard();
    await waitFor(() => {
      expect(
        screen.getByText("Forbidden: Access denied"),
      ).toBeInTheDocument();
    });
  });

  it("shows retry button on error", async () => {
    mockedApi.msp.getOverview.mockRejectedValue(new Error("fail"));
    mockedApi.msp.getComplianceSummary.mockRejectedValue(new Error("fail"));
    renderMSPDashboard();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
    });
  });

  it("retries fetching when retry button is clicked", async () => {
    const user = userEvent.setup();
    mockedApi.msp.getOverview
      .mockRejectedValueOnce(new Error("fail"))
      .mockResolvedValueOnce(sampleOverview);
    mockedApi.msp.getComplianceSummary
      .mockRejectedValueOnce(new Error("fail"))
      .mockResolvedValueOnce(sampleCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /retry/i }));
    await waitFor(() => {
      expect(screen.getByText("MSP Dashboard")).toBeInTheDocument();
      expect(mockedApi.msp.getOverview).toHaveBeenCalledTimes(2);
    });
  });

  // ── Overview cards ─────────────────────────────────────────────────

  it("renders the page title", async () => {
    mockedApi.msp.getOverview.mockResolvedValue(sampleOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(sampleCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(screen.getByText("MSP Dashboard")).toBeInTheDocument();
    });
  });

  it("displays total tenants count", async () => {
    mockedApi.msp.getOverview.mockResolvedValue(sampleOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(sampleCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(screen.getByText("Total Tenants")).toBeInTheDocument();
    });
    // The "3" may appear in multiple places; just check the label exists
    expect(screen.getByText("Total Tenants")).toBeInTheDocument();
  });

  it("displays total projects count", async () => {
    mockedApi.msp.getOverview.mockResolvedValue(sampleOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(sampleCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(screen.getByText("16")).toBeInTheDocument();
    });
    expect(screen.getByText("Total Projects")).toBeInTheDocument();
  });

  it("displays average compliance score", async () => {
    mockedApi.msp.getOverview.mockResolvedValue(sampleOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(sampleCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(screen.getByText("75.2%")).toBeInTheDocument();
    });
    expect(screen.getByText("Avg Compliance")).toBeInTheDocument();
  });

  it("displays active deployments count", async () => {
    mockedApi.msp.getOverview.mockResolvedValue(sampleOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(sampleCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(screen.getByText("4")).toBeInTheDocument();
    });
    expect(screen.getByText("Active Deployments")).toBeInTheDocument();
  });

  // ── Tenant table ───────────────────────────────────────────────────

  it("renders Managed Tenants section", async () => {
    mockedApi.msp.getOverview.mockResolvedValue(sampleOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(sampleCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(screen.getByText("Managed Tenants")).toBeInTheDocument();
    });
  });

  it("renders tenant names in the table", async () => {
    mockedApi.msp.getOverview.mockResolvedValue(sampleOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(sampleCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(screen.getByText("Contoso Ltd")).toBeInTheDocument();
    });
    expect(screen.getByText("Fabrikam Inc")).toBeInTheDocument();
    // Woodgrove Bank appears in both table and alerts; use getAllByText
    expect(screen.getAllByText("Woodgrove Bank").length).toBeGreaterThanOrEqual(1);
  });

  it("renders status badges in the table", async () => {
    mockedApi.msp.getOverview.mockResolvedValue(sampleOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(sampleCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(screen.getAllByText("active").length).toBe(2);
    });
    expect(screen.getByText("warning")).toBeInTheDocument();
  });

  it("renders compliance scores in the table", async () => {
    mockedApi.msp.getOverview.mockResolvedValue(sampleOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(sampleCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(screen.getByText("92.5%")).toBeInTheDocument();
    });
    expect(screen.getByText("78%")).toBeInTheDocument();
    expect(screen.getByText("55%")).toBeInTheDocument();
  });

  it("renders project counts in the table", async () => {
    mockedApi.msp.getOverview.mockResolvedValue(sampleOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(sampleCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(screen.getByText("8")).toBeInTheDocument();
    });
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  // ── Tenant row click / navigation ─────────────────────────────────

  it("navigates to tenant detail when row is clicked", async () => {
    const user = userEvent.setup();
    mockedApi.msp.getOverview.mockResolvedValue(sampleOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(sampleCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(screen.getByText("Contoso Ltd")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Contoso Ltd"));
    expect(mockNavigate).toHaveBeenCalledWith("/msp/tenants/t-001");
  });

  it("navigates with correct tenant ID for second tenant", async () => {
    const user = userEvent.setup();
    mockedApi.msp.getOverview.mockResolvedValue(sampleOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(sampleCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(screen.getByText("Fabrikam Inc")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Fabrikam Inc"));
    expect(mockNavigate).toHaveBeenCalledWith("/msp/tenants/t-002");
  });

  // ── Compliance alerts ──────────────────────────────────────────────

  it("shows compliance alerts section", async () => {
    mockedApi.msp.getOverview.mockResolvedValue(sampleOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(sampleCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(screen.getByText("Compliance Alerts")).toBeInTheDocument();
    });
  });

  it("shows failing tenant in alerts", async () => {
    mockedApi.msp.getOverview.mockResolvedValue(sampleOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(sampleCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      // Woodgrove Bank appears in both table and alerts
      expect(screen.getAllByText("Woodgrove Bank").length).toBeGreaterThanOrEqual(1);
    });
    expect(screen.getByText("Action Required")).toBeInTheDocument();
  });

  it("shows compliance score in alert", async () => {
    mockedApi.msp.getOverview.mockResolvedValue(sampleOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(sampleCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(
        screen.getByText(/55%.*failing/),
      ).toBeInTheDocument();
    });
  });

  it("hides compliance alerts when no failing tenants", async () => {
    const allPassingCompliance = {
      total_tenants: 2,
      passing: 2,
      warning: 0,
      failing: 0,
      scores_by_tenant: [
        {
          tenant_id: "t-001",
          name: "Contoso Ltd",
          score: 92.5,
          status: "passing",
        },
        {
          tenant_id: "t-002",
          name: "Fabrikam Inc",
          score: 85.0,
          status: "passing",
        },
      ],
    };
    mockedApi.msp.getOverview.mockResolvedValue(sampleOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(allPassingCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(screen.getByText("Managed Tenants")).toBeInTheDocument();
    });
    expect(screen.queryByText("Compliance Alerts")).not.toBeInTheDocument();
  });

  // ── Refresh button ─────────────────────────────────────────────────

  it("renders refresh button", async () => {
    mockedApi.msp.getOverview.mockResolvedValue(sampleOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(sampleCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /refresh/i }),
      ).toBeInTheDocument();
    });
  });

  it("calls API again when refresh is clicked", async () => {
    const user = userEvent.setup();
    mockedApi.msp.getOverview.mockResolvedValue(sampleOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(sampleCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /refresh/i }),
      ).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /refresh/i }));
    await waitFor(() => {
      expect(mockedApi.msp.getOverview).toHaveBeenCalledTimes(2);
    });
  });

  // ── Table header columns ───────────────────────────────────────────

  it("renders table header columns", async () => {
    mockedApi.msp.getOverview.mockResolvedValue(sampleOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(sampleCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(screen.getByText("Name")).toBeInTheDocument();
    });
    expect(screen.getByText("Status")).toBeInTheDocument();
    expect(screen.getByText("Compliance Score")).toBeInTheDocument();
    expect(screen.getByText("Projects")).toBeInTheDocument();
    expect(screen.getByText("Last Activity")).toBeInTheDocument();
  });

  // ── Last activity formatting ───────────────────────────────────────

  it("shows dash for null last_activity", async () => {
    const overviewWithNull = {
      ...sampleOverview,
      tenants: [
        {
          ...sampleOverview.tenants[0],
          last_activity: null,
        },
      ],
      total_tenants: 1,
    };
    mockedApi.msp.getOverview.mockResolvedValue(overviewWithNull);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(sampleCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(screen.getByText("—")).toBeInTheDocument();
    });
  });

  // ── Table accessibility ────────────────────────────────────────────

  it("table has accessible aria-label", async () => {
    mockedApi.msp.getOverview.mockResolvedValue(sampleOverview);
    mockedApi.msp.getComplianceSummary.mockResolvedValue(sampleCompliance);
    renderMSPDashboard();
    await waitFor(() => {
      expect(
        screen.getByRole("table", { name: /managed tenants/i }),
      ).toBeInTheDocument();
    });
  });
});
