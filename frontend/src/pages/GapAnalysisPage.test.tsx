import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import GapAnalysisPage from "./GapAnalysisPage";
import type { GapAnalysisResponse, BrownfieldContextResponse } from "../services/api";

const mockGapResult: GapAnalysisResponse = {
  scan_id: "scan-123",
  total_findings: 1,
  critical_count: 1,
  high_count: 0,
  medium_count: 0,
  low_count: 0,
  findings: [
    {
      id: "f-1",
      category: "networking",
      severity: "critical",
      title: "Missing firewall",
      description: "No firewall detected.",
      remediation: "Deploy Azure Firewall.",
      caf_reference: "CAF/networking",
      can_auto_remediate: false,
    },
  ],
  areas_checked: ["networking"],
  areas_skipped: [],
};

const mockBrownfieldContext: BrownfieldContextResponse = {
  scan_id: "scan-123",
  discovered_answers: {
    subscription_count: {
      value: "2",
      confidence: "high",
      evidence: "Found 2 subscriptions",
      source: "azure_api",
    },
  },
  gap_summary: { networking: 1 },
};

vi.mock("../services/api", () => ({
  api: {
    discovery: {
      analyzeScanGaps: vi.fn(),
      getBrownfieldContext: vi.fn(),
    },
  },
  exportGapAnalysis: vi.fn(),
}));

import { api } from "../services/api";

function renderPage(scanId = "scan-123") {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter initialEntries={[`/gap-analysis/${scanId}`]}>
        <Routes>
          <Route path="/gap-analysis/:scanId" element={<GapAnalysisPage />} />
        </Routes>
      </MemoryRouter>
    </FluentProvider>
  );
}

describe("GapAnalysisPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("renders without crashing", () => {
    vi.mocked(api.discovery.analyzeScanGaps).mockResolvedValue(mockGapResult);
    vi.mocked(api.discovery.getBrownfieldContext).mockResolvedValue(mockBrownfieldContext);
    const { container } = renderPage();
    expect(container).toBeTruthy();
  });

  it("shows loading spinner initially", () => {
    vi.mocked(api.discovery.analyzeScanGaps).mockReturnValue(new Promise(() => {}));
    vi.mocked(api.discovery.getBrownfieldContext).mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText(/analyzing gaps/i)).toBeInTheDocument();
  });

  it("renders gap analysis title after loading", async () => {
    vi.mocked(api.discovery.analyzeScanGaps).mockResolvedValue(mockGapResult);
    vi.mocked(api.discovery.getBrownfieldContext).mockResolvedValue(mockBrownfieldContext);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Gap Analysis")).toBeInTheDocument();
    });
  });

  it("shows error message when API fails", async () => {
    vi.mocked(api.discovery.analyzeScanGaps).mockRejectedValue(new Error("Network error"));
    vi.mocked(api.discovery.getBrownfieldContext).mockResolvedValue(mockBrownfieldContext);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument();
    });
  });

  it("shows findings after loading", async () => {
    vi.mocked(api.discovery.analyzeScanGaps).mockResolvedValue(mockGapResult);
    vi.mocked(api.discovery.getBrownfieldContext).mockResolvedValue(mockBrownfieldContext);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Missing firewall")).toBeInTheDocument();
    });
  });

  it("shows summary bar with counts", async () => {
    vi.mocked(api.discovery.analyzeScanGaps).mockResolvedValue(mockGapResult);
    vi.mocked(api.discovery.getBrownfieldContext).mockResolvedValue(mockBrownfieldContext);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/1 Critical/i)).toBeInTheDocument();
    });
  });

  it("shows Export Report button", async () => {
    vi.mocked(api.discovery.analyzeScanGaps).mockResolvedValue(mockGapResult);
    vi.mocked(api.discovery.getBrownfieldContext).mockResolvedValue(mockBrownfieldContext);
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /export report/i })).toBeInTheDocument();
    });
  });

  it("shows empty state when no findings", async () => {
    const emptyResult: GapAnalysisResponse = {
      ...mockGapResult,
      total_findings: 0,
      critical_count: 0,
      findings: [],
    };
    vi.mocked(api.discovery.analyzeScanGaps).mockResolvedValue(emptyResult);
    vi.mocked(api.discovery.getBrownfieldContext).mockResolvedValue(mockBrownfieldContext);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/no findings/i)).toBeInTheDocument();
    });
  });

  it("shows warning when no scanId in URL", () => {
    render(
      <FluentProvider theme={teamsLightTheme}>
        <MemoryRouter initialEntries={["/gap-analysis/"]}>
          <Routes>
            <Route path="/gap-analysis/" element={<GapAnalysisPage />} />
          </Routes>
        </MemoryRouter>
      </FluentProvider>
    );
    expect(screen.getByText(/no scan id provided/i)).toBeInTheDocument();
  });
});
