import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";

// ── Mocks ───────────────────────────────────────────────────────────────────

vi.mock("../../services/api", () => ({
  api: {
    governance: {
      audit: {
        list: vi.fn(),
      },
    },
  },
}));

import AuditPanel from "./AuditPanel";
import { api } from "../../services/api";

const mockedApi = api as unknown as {
  governance: {
    audit: {
      list: ReturnType<typeof vi.fn>;
    };
  };
};

// ── Test data ───────────────────────────────────────────────────────────────

const sampleAuditEntries = {
  entries: [
    {
      id: "audit-1",
      timestamp: "2025-07-27T10:00:00Z",
      actor: "admin@contoso.com",
      action: "policy.assigned",
      resource: "/subscriptions/sub-1",
      details: "Assigned 'Require tagging' policy to subscription",
      severity: "info",
    },
    {
      id: "audit-2",
      timestamp: "2025-07-27T09:30:00Z",
      actor: "deploy-sp@contoso.com",
      action: "rbac.role_assigned",
      resource: "/subscriptions/sub-1/resourceGroups/rg-prod",
      details: "Assigned Contributor role to deploy-sp",
      severity: "warning",
    },
    {
      id: "audit-3",
      timestamp: "2025-07-27T09:00:00Z",
      actor: "security-team@contoso.com",
      action: "drift.remediated",
      resource: "/subscriptions/sub-1/resourceGroups/rg-prod/providers/Microsoft.Network/nsg-web",
      details: "Reverted NSG rule change",
      severity: "high",
    },
    {
      id: "audit-4",
      timestamp: "2025-07-26T18:00:00Z",
      actor: "system",
      action: "scorecard.refreshed",
      resource: "governance-scorecard",
      details: "Automatic scorecard refresh completed",
      severity: "info",
    },
  ],
  total_count: 4,
};

const emptyAuditEntries = {
  entries: [],
  total_count: 0,
};

// ── Helper ──────────────────────────────────────────────────────────────────

function renderAuditPanel(projectId = "default") {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>
        <AuditPanel projectId={projectId} />
      </MemoryRouter>
    </FluentProvider>,
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("AuditPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", () => {
    mockedApi.governance.audit.list.mockReturnValue(new Promise(() => {}));
    renderAuditPanel();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("shows audit entries after data loads", async () => {
    mockedApi.governance.audit.list.mockResolvedValue(sampleAuditEntries);
    renderAuditPanel();
    await waitFor(() => {
      expect(
        screen.getByText(/Assigned 'Require tagging' policy/),
      ).toBeInTheDocument();
    });
  });

  it("displays entry timestamps", async () => {
    mockedApi.governance.audit.list.mockResolvedValue(sampleAuditEntries);
    renderAuditPanel();
    await waitFor(() => {
      // Timestamps should be rendered (format may vary by locale)
      expect(screen.getByText(/7\/27\/2025|27\/07\/2025|Jul 27/)).toBeInTheDocument();
    });
  });

  it("displays actor names", async () => {
    mockedApi.governance.audit.list.mockResolvedValue(sampleAuditEntries);
    renderAuditPanel();
    await waitFor(() => {
      expect(screen.getByText("admin@contoso.com")).toBeInTheDocument();
    });
    expect(screen.getByText("deploy-sp@contoso.com")).toBeInTheDocument();
    expect(screen.getByText("security-team@contoso.com")).toBeInTheDocument();
    expect(screen.getByText("system")).toBeInTheDocument();
  });

  it("displays action types", async () => {
    mockedApi.governance.audit.list.mockResolvedValue(sampleAuditEntries);
    renderAuditPanel();
    await waitFor(() => {
      expect(screen.getByText(/policy\.assigned/)).toBeInTheDocument();
    });
    expect(screen.getByText(/rbac\.role_assigned/)).toBeInTheDocument();
    expect(screen.getByText(/drift\.remediated/)).toBeInTheDocument();
    expect(screen.getByText(/scorecard\.refreshed/)).toBeInTheDocument();
  });

  it("renders detail descriptions", async () => {
    mockedApi.governance.audit.list.mockResolvedValue(sampleAuditEntries);
    renderAuditPanel();
    await waitFor(() => {
      expect(
        screen.getByText("Reverted NSG rule change"),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByText("Automatic scorecard refresh completed"),
    ).toBeInTheDocument();
  });

  it("handles empty state", async () => {
    mockedApi.governance.audit.list.mockResolvedValue(emptyAuditEntries);
    renderAuditPanel();
    await waitFor(() => {
      expect(screen.getByText(/no audit|no entries|empty/i)).toBeInTheDocument();
    });
  });

  it("handles API error state", async () => {
    mockedApi.governance.audit.list.mockRejectedValue(
      new Error("Network error"),
    );
    renderAuditPanel();
    await waitFor(() => {
      expect(screen.getByText(/failed|error/i)).toBeInTheDocument();
    });
  });

  it("calls list API with correct project ID", async () => {
    mockedApi.governance.audit.list.mockResolvedValue(sampleAuditEntries);
    renderAuditPanel("proj-xyz");
    await waitFor(() => {
      expect(mockedApi.governance.audit.list).toHaveBeenCalledWith("proj-xyz");
    });
  });

  it("renders all four audit entries", async () => {
    mockedApi.governance.audit.list.mockResolvedValue(sampleAuditEntries);
    renderAuditPanel();
    await waitFor(() => {
      expect(screen.getByText("admin@contoso.com")).toBeInTheDocument();
    });
    // Verify all entries are rendered by checking for unique details
    expect(
      screen.getByText("Assigned Contributor role to deploy-sp"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Reverted NSG rule change"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Automatic scorecard refresh completed"),
    ).toBeInTheDocument();
  });

  it("shows total count of entries", async () => {
    mockedApi.governance.audit.list.mockResolvedValue(sampleAuditEntries);
    renderAuditPanel();
    await waitFor(() => {
      expect(screen.getByText(/4/)).toBeInTheDocument();
    });
  });
});
