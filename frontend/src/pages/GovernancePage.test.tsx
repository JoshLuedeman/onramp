import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi, describe, it, expect, beforeEach } from "vitest";
import GovernancePage from "./GovernancePage";

// Mock the API
vi.mock("../services/api", () => ({
  api: {
    governance: {
      scorecard: {
        getScorecard: vi.fn(),
        getScoreTrend: vi.fn(),
        refreshScore: vi.fn(),
        getSummary: vi.fn(),
      },
    },
  },
}));

// Mock the useEventStream hook
vi.mock("../hooks/useEventStream", () => ({
  useEventStream: vi.fn(() => ({
    connected: true,
    reconnecting: false,
    subscriberCount: 1,
  })),
}));

import { api } from "../services/api";
import { useEventStream } from "../hooks/useEventStream";

const mockedApi = api as unknown as {
  governance: {
    scorecard: {
      getScorecard: ReturnType<typeof vi.fn>;
      getScoreTrend: ReturnType<typeof vi.fn>;
      refreshScore: ReturnType<typeof vi.fn>;
      getSummary: ReturnType<typeof vi.fn>;
    };
  };
};

const mockedUseEventStream = useEventStream as ReturnType<typeof vi.fn>;

function renderGovernancePage(projectId?: string) {
  if (projectId) {
    return render(
      <FluentProvider theme={teamsLightTheme}>
        <MemoryRouter initialEntries={[`/projects/${projectId}/governance`]}>
          <Routes>
            <Route
              path="/projects/:projectId/governance"
              element={<GovernancePage />}
            />
          </Routes>
        </MemoryRouter>
      </FluentProvider>
    );
  }
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>
        <GovernancePage />
      </MemoryRouter>
    </FluentProvider>
  );
}

const sampleScorecard = {
  overall_score: 82.5,
  categories: [
    { name: "compliance", score: 85.0, status: "healthy" as const, finding_count: 3 },
    { name: "security", score: 80.0, status: "healthy" as const, finding_count: 2 },
    { name: "cost", score: 75.0, status: "warning" as const, finding_count: 5 },
    { name: "drift", score: 90.0, status: "healthy" as const, finding_count: 0 },
    { name: "tagging", score: 70.0, status: "warning" as const, finding_count: 4 },
  ],
  executive_summary:
    "Your landing zone is 82.5% compliant. 14 issues require attention.",
  last_updated: "2024-06-15T10:30:00Z",
};

const criticalScorecard = {
  overall_score: 45.0,
  categories: [
    { name: "compliance", score: 40.0, status: "critical" as const, finding_count: 15 },
    { name: "security", score: 35.0, status: "critical" as const, finding_count: 12 },
    { name: "cost", score: 50.0, status: "warning" as const, finding_count: 8 },
    { name: "drift", score: 55.0, status: "warning" as const, finding_count: 6 },
    { name: "tagging", score: 45.0, status: "critical" as const, finding_count: 10 },
  ],
  executive_summary:
    "Your landing zone is 45.0% compliant. 51 issues require attention. Critical areas: compliance, security, tagging.",
  last_updated: "2024-06-15T10:30:00Z",
};

describe("GovernancePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedUseEventStream.mockReturnValue({
      connected: true,
      reconnecting: false,
      subscriberCount: 1,
    });
  });

  it("shows loading spinner initially", () => {
    mockedApi.governance.scorecard.getScorecard.mockReturnValue(
      new Promise(() => {})
    );
    renderGovernancePage();
    expect(
      screen.getByText("Loading governance scorecard...")
    ).toBeInTheDocument();
  });

  it("renders overall governance score", async () => {
    mockedApi.governance.scorecard.getScorecard.mockResolvedValue(
      sampleScorecard
    );
    renderGovernancePage();
    await waitFor(() => {
      expect(screen.getByText("83")).toBeInTheDocument();
    });
    expect(screen.getByText("Overall Governance Score")).toBeInTheDocument();
  });

  it("renders category cards for all five categories", async () => {
    mockedApi.governance.scorecard.getScorecard.mockResolvedValue(
      sampleScorecard
    );
    renderGovernancePage();
    await waitFor(() => {
      expect(screen.getByText("Policy Compliance")).toBeInTheDocument();
    });
    expect(screen.getByText("Security / RBAC")).toBeInTheDocument();
    expect(screen.getByText("Cost Management")).toBeInTheDocument();
    expect(screen.getByText("Drift Detection")).toBeInTheDocument();
    expect(screen.getByText("Tagging Compliance")).toBeInTheDocument();
  });

  it("displays finding count on category cards", async () => {
    mockedApi.governance.scorecard.getScorecard.mockResolvedValue(
      sampleScorecard
    );
    renderGovernancePage();
    await waitFor(() => {
      expect(screen.getByText("3 findings")).toBeInTheDocument();
    });
    expect(screen.getByText("2 findings")).toBeInTheDocument();
    expect(screen.getByText("5 findings")).toBeInTheDocument();
    expect(screen.getByText("0 findings")).toBeInTheDocument();
    expect(screen.getByText("4 findings")).toBeInTheDocument();
  });

  it("renders executive summary text", async () => {
    mockedApi.governance.scorecard.getScorecard.mockResolvedValue(
      sampleScorecard
    );
    renderGovernancePage();
    await waitFor(() => {
      expect(screen.getByText("Executive Summary")).toBeInTheDocument();
    });
    expect(
      screen.getByText(
        "Your landing zone is 82.5% compliant. 14 issues require attention."
      )
    ).toBeInTheDocument();
  });

  it("renders refresh button", async () => {
    mockedApi.governance.scorecard.getScorecard.mockResolvedValue(
      sampleScorecard
    );
    renderGovernancePage();
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /refresh/i })
      ).toBeInTheDocument();
    });
  });

  it("calls refresh API when refresh button is clicked", async () => {
    const user = userEvent.setup();
    mockedApi.governance.scorecard.getScorecard.mockResolvedValue(
      sampleScorecard
    );
    mockedApi.governance.scorecard.refreshScore.mockResolvedValue(
      sampleScorecard
    );
    renderGovernancePage();
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /refresh/i })
      ).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /refresh/i }));
    await waitFor(() => {
      expect(
        mockedApi.governance.scorecard.refreshScore
      ).toHaveBeenCalledWith("default");
    });
  });

  it("shows error state on API failure", async () => {
    mockedApi.governance.scorecard.getScorecard.mockRejectedValue(
      new Error("Network error")
    );
    renderGovernancePage();
    await waitFor(() => {
      expect(
        screen.getByText("Failed to load governance scorecard.")
      ).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("subscribes to SSE governance_score_updated events", () => {
    mockedApi.governance.scorecard.getScorecard.mockReturnValue(
      new Promise(() => {})
    );
    renderGovernancePage();
    expect(mockedUseEventStream).toHaveBeenCalledWith(
      ["governance_score_updated"],
      expect.any(Function)
    );
  });

  it("displays healthy badge for high scores", async () => {
    mockedApi.governance.scorecard.getScorecard.mockResolvedValue(
      sampleScorecard
    );
    renderGovernancePage();
    await waitFor(() => {
      expect(screen.getByText("Healthy")).toBeInTheDocument();
    });
  });

  it("displays critical badge for low scores", async () => {
    mockedApi.governance.scorecard.getScorecard.mockResolvedValue(
      criticalScorecard
    );
    renderGovernancePage();
    await waitFor(() => {
      expect(screen.getByText("Critical")).toBeInTheDocument();
    });
  });

  it("displays status badges on category cards", async () => {
    mockedApi.governance.scorecard.getScorecard.mockResolvedValue(
      sampleScorecard
    );
    renderGovernancePage();
    await waitFor(() => {
      expect(screen.getAllByText("healthy").length).toBeGreaterThanOrEqual(1);
    });
    expect(screen.getAllByText("warning").length).toBeGreaterThanOrEqual(1);
  });

  it("displays last updated timestamp", async () => {
    mockedApi.governance.scorecard.getScorecard.mockResolvedValue(
      sampleScorecard
    );
    renderGovernancePage();
    await waitFor(() => {
      expect(screen.getByText(/Last updated:/)).toBeInTheDocument();
    });
  });

  it("renders page title", async () => {
    mockedApi.governance.scorecard.getScorecard.mockResolvedValue(
      sampleScorecard
    );
    renderGovernancePage();
    await waitFor(() => {
      expect(screen.getByText("Governance Scorecard")).toBeInTheDocument();
    });
  });

  it("renders with project ID from URL params", async () => {
    mockedApi.governance.scorecard.getScorecard.mockResolvedValue(
      sampleScorecard
    );
    renderGovernancePage("proj-123");
    await waitFor(() => {
      expect(
        mockedApi.governance.scorecard.getScorecard
      ).toHaveBeenCalledWith("proj-123");
    });
  });

  it("renders category breakdown heading", async () => {
    mockedApi.governance.scorecard.getScorecard.mockResolvedValue(
      sampleScorecard
    );
    renderGovernancePage();
    await waitFor(() => {
      expect(screen.getByText("Category Breakdown")).toBeInTheDocument();
    });
  });

  it("renders all five category labels", async () => {
    mockedApi.governance.scorecard.getScorecard.mockResolvedValue(
      sampleScorecard
    );
    renderGovernancePage();
    await waitFor(() => {
      expect(screen.getByText("Policy Compliance")).toBeInTheDocument();
      expect(screen.getByText("Security / RBAC")).toBeInTheDocument();
      expect(screen.getByText("Cost Management")).toBeInTheDocument();
      expect(screen.getByText("Drift Detection")).toBeInTheDocument();
      expect(screen.getByText("Tagging Compliance")).toBeInTheDocument();
    });
  });

  it("renders category scores rounded", async () => {
    mockedApi.governance.scorecard.getScorecard.mockResolvedValue(
      sampleScorecard
    );
    renderGovernancePage();
    await waitFor(() => {
      expect(screen.getByText("85")).toBeInTheDocument();
      expect(screen.getByText("80")).toBeInTheDocument();
      expect(screen.getByText("75")).toBeInTheDocument();
      expect(screen.getByText("90")).toBeInTheDocument();
      expect(screen.getByText("70")).toBeInTheDocument();
    });
  });

  it("displays Needs Attention badge for warning-level overall score", async () => {
    const warningScorecard = {
      ...sampleScorecard,
      overall_score: 65.0,
    };
    mockedApi.governance.scorecard.getScorecard.mockResolvedValue(
      warningScorecard
    );
    renderGovernancePage();
    await waitFor(() => {
      expect(screen.getByText("Needs Attention")).toBeInTheDocument();
    });
  });

  it("retries loading when retry button is clicked after error", async () => {
    const user = userEvent.setup();
    mockedApi.governance.scorecard.getScorecard
      .mockRejectedValueOnce(new Error("fail"))
      .mockResolvedValueOnce(sampleScorecard);
    renderGovernancePage();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /retry/i }));
    await waitFor(() => {
      expect(screen.getByText("Governance Scorecard")).toBeInTheDocument();
      expect(screen.getByText("83")).toBeInTheDocument();
    });
  });
});
