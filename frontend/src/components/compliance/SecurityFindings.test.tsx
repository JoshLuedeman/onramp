import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import SecurityFindings from "./SecurityFindings";
import type { SecurityAnalysisResultData, SecurityFindingData } from "./SecurityFindings";

const criticalFinding: SecurityFindingData = {
  id: "SEC-DEF-001",
  severity: "critical",
  category: "threat_protection",
  resource: "subscription",
  finding: "Defender for Cloud is not enabled",
  remediation: "Enable Defender for Cloud with all plans.",
  auto_fixable: true,
};

const highFinding: SecurityFindingData = {
  id: "SEC-NSG-002",
  severity: "high",
  category: "networking",
  resource: "hub/subnet/default",
  finding: "Subnets without NSGs",
  remediation: "Attach NSGs to every subnet.",
  auto_fixable: true,
};

const mediumFinding: SecurityFindingData = {
  id: "SEC-DDOS-003",
  severity: "medium",
  category: "networking",
  resource: "virtual_network",
  finding: "DDoS Protection not enabled",
  remediation: "Enable DDoS Protection Standard.",
  auto_fixable: true,
};

const lowFinding: SecurityFindingData = {
  id: "SEC-AI-004",
  severity: "low",
  category: "identity",
  resource: "entra_id",
  finding: "Conditional Access could be stricter",
  remediation: "Add compliant device requirement.",
  auto_fixable: false,
};

const mockResult: SecurityAnalysisResultData = {
  score: 42,
  findings: [criticalFinding, highFinding, mediumFinding, lowFinding],
  summary:
    "Security score: 42/100. Found 4 issue(s): 1 critical, 1 high, 1 medium, 1 low.",
  analyzed_at: "2025-01-15T10:30:00Z",
};

const healthyResult: SecurityAnalysisResultData = {
  score: 100,
  findings: [],
  summary: "Security score: 100/100. Found 0 issue(s): 0 critical, 0 high, 0 medium, 0 low.",
  analyzed_at: "2025-01-15T10:30:00Z",
};

function renderComponent(
  props: Partial<React.ComponentProps<typeof SecurityFindings>> = {},
) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <SecurityFindings {...props} />
    </FluentProvider>,
  );
}

describe("SecurityFindings", () => {
  // ── Rendering ─────────────────────────────────────────────────────────

  it("renders empty state when no result is provided", () => {
    renderComponent({ onRunAnalysis: vi.fn() });
    expect(screen.getByText(/no security analysis results yet/i)).toBeInTheDocument();
  });

  it("renders the Run Analysis button", () => {
    renderComponent({ onRunAnalysis: vi.fn() });
    expect(screen.getByRole("button", { name: /run analysis/i })).toBeInTheDocument();
  });

  it("calls onRunAnalysis when Run Analysis is clicked", async () => {
    const onRun = vi.fn();
    const user = userEvent.setup();
    renderComponent({ onRunAnalysis: onRun });
    await user.click(screen.getByRole("button", { name: /run analysis/i }));
    expect(onRun).toHaveBeenCalledOnce();
  });

  it("shows loading state with Analyzing text", () => {
    renderComponent({ onRunAnalysis: vi.fn(), loading: true });
    expect(screen.getByRole("button", { name: /analyzing/i })).toBeDisabled();
  });

  // ── Score display ────────────────────────────────────────────────────

  it("displays the security score", () => {
    renderComponent({ result: mockResult });
    const scoreEl = screen.getByTestId("security-score");
    expect(scoreEl).toHaveTextContent("42");
  });

  it("displays score 100 for a healthy result", () => {
    renderComponent({ result: healthyResult });
    const scoreEl = screen.getByTestId("security-score");
    expect(scoreEl).toHaveTextContent("100");
  });

  it("shows summary text", () => {
    renderComponent({ result: mockResult });
    expect(screen.getByText(/found 4 issue/i)).toBeInTheDocument();
  });

  it("shows empty findings message when score is perfect", () => {
    renderComponent({ result: healthyResult });
    expect(screen.getByText(/no security issues found/i)).toBeInTheDocument();
  });

  // ── Severity badges ──────────────────────────────────────────────────

  it("shows Critical severity badge", () => {
    renderComponent({ result: mockResult });
    expect(screen.getByText("Critical")).toBeInTheDocument();
  });

  it("shows High severity badge", () => {
    renderComponent({ result: mockResult });
    expect(screen.getByText("High")).toBeInTheDocument();
  });

  it("shows Medium severity badge", () => {
    renderComponent({ result: mockResult });
    expect(screen.getByText("Medium")).toBeInTheDocument();
  });

  it("shows Low severity badge", () => {
    renderComponent({ result: mockResult });
    expect(screen.getByText("Low")).toBeInTheDocument();
  });

  // ── Finding expansion ────────────────────────────────────────────────

  it("does not show remediation by default (collapsed)", () => {
    renderComponent({ result: mockResult });
    expect(screen.queryByText("Enable Defender for Cloud with all plans.")).not.toBeInTheDocument();
  });

  it("expands finding to show remediation on click", async () => {
    const user = userEvent.setup();
    renderComponent({ result: mockResult });
    // Click the first finding header
    const headers = screen.getAllByRole("button");
    await user.click(headers[0]);
    expect(screen.getByText("Enable Defender for Cloud with all plans.")).toBeInTheDocument();
  });

  it("shows category when expanded", async () => {
    const user = userEvent.setup();
    renderComponent({ result: mockResult });
    const headers = screen.getAllByRole("button");
    await user.click(headers[0]);
    expect(screen.getByText("threat_protection")).toBeInTheDocument();
  });

  it("shows resource when expanded", async () => {
    const user = userEvent.setup();
    renderComponent({ result: mockResult });
    const headers = screen.getAllByRole("button");
    await user.click(headers[0]);
    expect(screen.getByText("subscription")).toBeInTheDocument();
  });

  // ── Fix button ───────────────────────────────────────────────────────

  it("shows Fix button for auto-fixable findings when expanded", async () => {
    const user = userEvent.setup();
    renderComponent({ result: mockResult, onFix: vi.fn() });
    const headers = screen.getAllByRole("button");
    await user.click(headers[0]);
    expect(screen.getByRole("button", { name: /fix/i })).toBeInTheDocument();
  });

  it("calls onFix with finding id when Fix is clicked", async () => {
    const onFix = vi.fn();
    const user = userEvent.setup();
    renderComponent({ result: mockResult, onFix });
    // Expand the first finding (critical, auto_fixable)
    const headers = screen.getAllByRole("button");
    await user.click(headers[0]);
    await user.click(screen.getByRole("button", { name: /fix/i }));
    expect(onFix).toHaveBeenCalledWith("SEC-DEF-001");
  });

  it("does not show Fix button for non-auto-fixable findings", async () => {
    const user = userEvent.setup();
    // Only show the low finding which is NOT auto_fixable
    const resultWithLow: SecurityAnalysisResultData = {
      ...mockResult,
      findings: [lowFinding],
    };
    renderComponent({ result: resultWithLow, onFix: vi.fn() });
    const headers = screen.getAllByRole("button");
    await user.click(headers[0]);
    expect(screen.queryByRole("button", { name: /fix/i })).not.toBeInTheDocument();
  });

  // ── Keyboard accessibility ───────────────────────────────────────────

  it("expands finding on Enter key press", async () => {
    const user = userEvent.setup();
    renderComponent({ result: mockResult });
    const headers = screen.getAllByRole("button");
    headers[0].focus();
    await user.keyboard("{Enter}");
    expect(screen.getByText("Enable Defender for Cloud with all plans.")).toBeInTheDocument();
  });

  // ── Security Posture heading ─────────────────────────────────────────

  it("renders Security Posture heading", () => {
    renderComponent();
    expect(screen.getByText("Security Posture")).toBeInTheDocument();
  });
});
