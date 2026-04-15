import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";
import GapComparison from "./GapComparison";
import type { GapAnalysisResponse, BrownfieldContextResponse } from "../../services/api";

const mockGapResult: GapAnalysisResponse = {
  scan_id: "scan-1",
  total_findings: 2,
  critical_count: 1,
  high_count: 1,
  medium_count: 0,
  low_count: 0,
  findings: [
    {
      id: "f-1",
      category: "networking",
      severity: "critical",
      title: "No firewall",
      description: "No Azure Firewall detected.",
      remediation: "Deploy Azure Firewall in hub.",
      caf_reference: "CAF/networking/firewall",
      can_auto_remediate: false,
    },
    {
      id: "f-2",
      category: "identity",
      severity: "high",
      title: "No MFA",
      description: "MFA not enabled.",
      remediation: "Enable Conditional Access MFA.",
      caf_reference: "CAF/identity/mfa",
      can_auto_remediate: true,
    },
  ],
  areas_checked: ["networking", "identity", "governance"],
  areas_skipped: [],
};

const mockBrownfieldContext: BrownfieldContextResponse = {
  scan_id: "scan-1",
  discovered_answers: {
    subscription_count: {
      value: "3",
      confidence: "high",
      evidence: "Found 3 subscriptions",
      source: "azure_api",
    },
    has_firewall: {
      value: "false",
      confidence: "high",
      evidence: "No firewall resource found",
      source: "azure_api",
    },
  },
  gap_summary: {
    networking: 1,
    identity: 1,
  },
};

const emptyBrownfieldContext: BrownfieldContextResponse = {
  scan_id: "scan-1",
  discovered_answers: {},
  gap_summary: {},
};

function renderComparison(
  gapResult = mockGapResult,
  brownfieldContext = mockBrownfieldContext
) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>
        <GapComparison gapResult={gapResult} brownfieldContext={brownfieldContext} />
      </MemoryRouter>
    </FluentProvider>
  );
}

describe("GapComparison", () => {
  it("renders without crashing", () => {
    const { container } = renderComparison();
    expect(container).toBeTruthy();
  });

  it("shows the section title", () => {
    renderComparison();
    expect(screen.getByText(/current vs recommended architecture/i)).toBeInTheDocument();
  });

  it("shows Current State column", () => {
    renderComparison();
    expect(screen.getByText("Current State")).toBeInTheDocument();
  });

  it("shows Recommended State column", () => {
    renderComparison();
    expect(screen.getByText("Recommended State")).toBeInTheDocument();
  });

  it("renders discovered answer keys in current state", () => {
    renderComparison();
    expect(screen.getByText(/subscription count/i)).toBeInTheDocument();
  });

  it("renders area rows for checked areas", () => {
    renderComparison();
    expect(screen.getByText("networking")).toBeInTheDocument();
    expect(screen.getByText("governance")).toBeInTheDocument();
  });

  it("shows 'No discovered context available' when empty", () => {
    renderComparison(mockGapResult, emptyBrownfieldContext);
    expect(screen.getByText(/no discovered context available/i)).toBeInTheDocument();
  });

  it("shows compliant badge for areas with no findings", () => {
    renderComparison();
    expect(screen.getByText("Compliant")).toBeInTheDocument();
  });
});
