import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";

// ── Mocks ───────────────────────────────────────────────────────────────────

vi.mock("../../services/api", () => ({
  api: {
    governance: {
      tagging: {
        getSummary: vi.fn(),
      },
    },
  },
}));

import TaggingPanel from "./TaggingPanel";
import { api } from "../../services/api";

const mockedApi = api as unknown as {
  governance: {
    tagging: {
      getSummary: ReturnType<typeof vi.fn>;
    };
  };
};

// ── Test data ───────────────────────────────────────────────────────────────

const sampleTaggingSummary = {
  compliance_percentage: 72.5,
  total_resources: 120,
  compliant_resources: 87,
  non_compliant_resources: 33,
  required_tags: ["environment", "cost-center", "owner", "application"],
  violations: [
    {
      id: "tag-1",
      resource_id: "/subscriptions/sub-1/resourceGroups/rg-1/providers/Microsoft.Compute/virtualMachines/vm-01",
      resource_name: "vm-01",
      missing_tags: ["cost-center", "owner"],
      resource_type: "Microsoft.Compute/virtualMachines",
    },
    {
      id: "tag-2",
      resource_id: "/subscriptions/sub-1/resourceGroups/rg-1/providers/Microsoft.Storage/storageAccounts/sa01",
      resource_name: "sa01",
      missing_tags: ["owner"],
      resource_type: "Microsoft.Storage/storageAccounts",
    },
    {
      id: "tag-3",
      resource_id: "/subscriptions/sub-1/resourceGroups/rg-2/providers/Microsoft.Sql/servers/sql-01",
      resource_name: "sql-01",
      missing_tags: ["environment", "cost-center", "owner"],
      resource_type: "Microsoft.Sql/servers",
    },
  ],
  last_updated: "2025-07-27T10:00:00Z",
};

const perfectTaggingSummary = {
  compliance_percentage: 100,
  total_resources: 50,
  compliant_resources: 50,
  non_compliant_resources: 0,
  required_tags: ["environment", "cost-center", "owner"],
  violations: [],
  last_updated: "2025-07-27T10:00:00Z",
};

// ── Helper ──────────────────────────────────────────────────────────────────

function renderTaggingPanel(projectId = "default") {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>
        <TaggingPanel projectId={projectId} />
      </MemoryRouter>
    </FluentProvider>,
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("TaggingPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state initially", () => {
    mockedApi.governance.tagging.getSummary.mockReturnValue(
      new Promise(() => {}),
    );
    renderTaggingPanel();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("shows compliance percentage after data loads", async () => {
    mockedApi.governance.tagging.getSummary.mockResolvedValue(
      sampleTaggingSummary,
    );
    renderTaggingPanel();
    await waitFor(() => {
      expect(screen.getByText(/72\.5%/)).toBeInTheDocument();
    });
  });

  it("displays total and compliant resource counts", async () => {
    mockedApi.governance.tagging.getSummary.mockResolvedValue(
      sampleTaggingSummary,
    );
    renderTaggingPanel();
    await waitFor(() => {
      expect(screen.getByText(/120/)).toBeInTheDocument();
    });
    expect(screen.getByText(/87/)).toBeInTheDocument();
  });

  it("shows non-compliant resource count", async () => {
    mockedApi.governance.tagging.getSummary.mockResolvedValue(
      sampleTaggingSummary,
    );
    renderTaggingPanel();
    await waitFor(() => {
      expect(screen.getByText(/33/)).toBeInTheDocument();
    });
  });

  it("displays violations list", async () => {
    mockedApi.governance.tagging.getSummary.mockResolvedValue(
      sampleTaggingSummary,
    );
    renderTaggingPanel();
    await waitFor(() => {
      expect(screen.getByText("vm-01")).toBeInTheDocument();
    });
    expect(screen.getByText("sa01")).toBeInTheDocument();
    expect(screen.getByText("sql-01")).toBeInTheDocument();
  });

  it("shows missing tags for violations", async () => {
    mockedApi.governance.tagging.getSummary.mockResolvedValue(
      sampleTaggingSummary,
    );
    renderTaggingPanel();
    await waitFor(() => {
      expect(screen.getByText(/cost-center/)).toBeInTheDocument();
    });
    expect(screen.getByText(/owner/)).toBeInTheDocument();
  });

  it("shows required tags list", async () => {
    mockedApi.governance.tagging.getSummary.mockResolvedValue(
      sampleTaggingSummary,
    );
    renderTaggingPanel();
    await waitFor(() => {
      expect(screen.getByText(/environment/)).toBeInTheDocument();
    });
    expect(screen.getByText(/application/)).toBeInTheDocument();
  });

  it("handles API error state", async () => {
    mockedApi.governance.tagging.getSummary.mockRejectedValue(
      new Error("Network error"),
    );
    renderTaggingPanel();
    await waitFor(() => {
      expect(screen.getByText(/failed|error/i)).toBeInTheDocument();
    });
  });

  it("calls getSummary with correct project ID", async () => {
    mockedApi.governance.tagging.getSummary.mockResolvedValue(
      sampleTaggingSummary,
    );
    renderTaggingPanel("proj-abc");
    await waitFor(() => {
      expect(mockedApi.governance.tagging.getSummary).toHaveBeenCalledWith(
        "proj-abc",
      );
    });
  });

  it("shows 100% compliance when all resources are tagged", async () => {
    mockedApi.governance.tagging.getSummary.mockResolvedValue(
      perfectTaggingSummary,
    );
    renderTaggingPanel();
    await waitFor(() => {
      expect(screen.getByText(/100%/)).toBeInTheDocument();
    });
  });

  it("handles empty violations list gracefully", async () => {
    mockedApi.governance.tagging.getSummary.mockResolvedValue(
      perfectTaggingSummary,
    );
    renderTaggingPanel();
    await waitFor(() => {
      expect(screen.getByText(/100%/)).toBeInTheDocument();
    });
    // No violation rows should be present
    expect(screen.queryByText("vm-01")).not.toBeInTheDocument();
  });
});
