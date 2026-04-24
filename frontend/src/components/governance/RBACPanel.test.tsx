import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";

// ── Mocks ───────────────────────────────────────────────────────────────────

vi.mock("../../services/api", () => ({
  api: {
    governance: {
      rbac: {
        getSummary: vi.fn(),
        getResults: vi.fn(),
        scan: vi.fn(),
      },
    },
  },
}));

import RBACPanel from "./RBACPanel";
import { api } from "../../services/api";

const mockedApi = api as unknown as {
  governance: {
    rbac: {
      getSummary: ReturnType<typeof vi.fn>;
      getResults: ReturnType<typeof vi.fn>;
      scan: ReturnType<typeof vi.fn>;
    };
  };
};

// ── Test data ───────────────────────────────────────────────────────────────

const sampleRBACSummary = {
  health_score: 78,
  total_assignments: 42,
  excessive_permissions: 5,
  orphaned_assignments: 3,
  status: "warning" as const,
  last_scan: "2025-07-27T10:00:00Z",
};

const sampleRBACResults = {
  findings: [
    {
      id: "rbac-1",
      severity: "high",
      type: "excessive_permission",
      principal: "user@example.com",
      role: "Owner",
      scope: "/subscriptions/sub-1",
      recommendation: "Reduce to Contributor role",
    },
    {
      id: "rbac-2",
      severity: "medium",
      type: "orphaned_assignment",
      principal: "deleted-user@example.com",
      role: "Reader",
      scope: "/subscriptions/sub-1/resourceGroups/rg-1",
      recommendation: "Remove orphaned assignment",
    },
    {
      id: "rbac-3",
      severity: "low",
      type: "broad_scope",
      principal: "app-sp@example.com",
      role: "Contributor",
      scope: "/subscriptions/sub-1",
      recommendation: "Scope down to resource group level",
    },
  ],
  total_count: 3,
};

// ── Helper ──────────────────────────────────────────────────────────────────

function renderRBACPanel(projectId = "default") {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>
        <RBACPanel projectId={projectId} />
      </MemoryRouter>
    </FluentProvider>,
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("RBACPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", () => {
    mockedApi.governance.rbac.getSummary.mockReturnValue(new Promise(() => {}));
    mockedApi.governance.rbac.getResults.mockReturnValue(new Promise(() => {}));
    renderRBACPanel();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("shows health score after data loads", async () => {
    mockedApi.governance.rbac.getSummary.mockResolvedValue(sampleRBACSummary);
    mockedApi.governance.rbac.getResults.mockResolvedValue(sampleRBACResults);
    renderRBACPanel();
    await waitFor(() => {
      expect(screen.getByText(/78/)).toBeInTheDocument();
    });
  });

  it("displays total assignments count", async () => {
    mockedApi.governance.rbac.getSummary.mockResolvedValue(sampleRBACSummary);
    mockedApi.governance.rbac.getResults.mockResolvedValue(sampleRBACResults);
    renderRBACPanel();
    await waitFor(() => {
      expect(screen.getByText(/42/)).toBeInTheDocument();
    });
  });

  it("shows excessive permissions count", async () => {
    mockedApi.governance.rbac.getSummary.mockResolvedValue(sampleRBACSummary);
    mockedApi.governance.rbac.getResults.mockResolvedValue(sampleRBACResults);
    renderRBACPanel();
    await waitFor(() => {
      expect(screen.getByText(/5/)).toBeInTheDocument();
    });
  });

  it("renders findings list", async () => {
    mockedApi.governance.rbac.getSummary.mockResolvedValue(sampleRBACSummary);
    mockedApi.governance.rbac.getResults.mockResolvedValue(sampleRBACResults);
    renderRBACPanel();
    await waitFor(() => {
      expect(screen.getByText("user@example.com")).toBeInTheDocument();
    });
    expect(screen.getByText("deleted-user@example.com")).toBeInTheDocument();
    expect(screen.getByText("app-sp@example.com")).toBeInTheDocument();
  });

  it("displays severity badges for findings", async () => {
    mockedApi.governance.rbac.getSummary.mockResolvedValue(sampleRBACSummary);
    mockedApi.governance.rbac.getResults.mockResolvedValue(sampleRBACResults);
    renderRBACPanel();
    await waitFor(() => {
      expect(screen.getByText(/high/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/medium/i)).toBeInTheDocument();
    expect(screen.getByText(/low/i)).toBeInTheDocument();
  });

  it("renders scan button", async () => {
    mockedApi.governance.rbac.getSummary.mockResolvedValue(sampleRBACSummary);
    mockedApi.governance.rbac.getResults.mockResolvedValue(sampleRBACResults);
    renderRBACPanel();
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /scan/i }),
      ).toBeInTheDocument();
    });
  });

  it("calls scan API when scan button is clicked", async () => {
    const user = userEvent.setup();
    mockedApi.governance.rbac.getSummary.mockResolvedValue(sampleRBACSummary);
    mockedApi.governance.rbac.getResults.mockResolvedValue(sampleRBACResults);
    mockedApi.governance.rbac.scan.mockResolvedValue(sampleRBACSummary);
    renderRBACPanel();
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /scan/i }),
      ).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /scan/i }));
    await waitFor(() => {
      expect(mockedApi.governance.rbac.scan).toHaveBeenCalledWith("default");
    });
  });

  it("handles API error state", async () => {
    mockedApi.governance.rbac.getSummary.mockRejectedValue(
      new Error("Network error"),
    );
    mockedApi.governance.rbac.getResults.mockRejectedValue(
      new Error("Network error"),
    );
    renderRBACPanel();
    await waitFor(() => {
      expect(screen.getByText(/failed|error/i)).toBeInTheDocument();
    });
  });

  it("calls getSummary with correct project ID", async () => {
    mockedApi.governance.rbac.getSummary.mockResolvedValue(sampleRBACSummary);
    mockedApi.governance.rbac.getResults.mockResolvedValue(sampleRBACResults);
    renderRBACPanel("proj-789");
    await waitFor(() => {
      expect(mockedApi.governance.rbac.getSummary).toHaveBeenCalledWith(
        "proj-789",
      );
    });
  });

  it("shows last scan timestamp", async () => {
    mockedApi.governance.rbac.getSummary.mockResolvedValue(sampleRBACSummary);
    mockedApi.governance.rbac.getResults.mockResolvedValue(sampleRBACResults);
    renderRBACPanel();
    await waitFor(() => {
      expect(screen.getByText(/last scan/i)).toBeInTheDocument();
    });
  });
});
