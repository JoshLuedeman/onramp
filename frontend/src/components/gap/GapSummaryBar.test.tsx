import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";
import GapSummaryBar from "./GapSummaryBar";
import type { GapAnalysisResponse } from "../../services/api";

const mockResult: GapAnalysisResponse = {
  scan_id: "scan-1",
  total_findings: 6,
  critical_count: 1,
  high_count: 2,
  medium_count: 2,
  low_count: 1,
  findings: [],
  areas_checked: ["networking", "identity"],
  areas_skipped: [],
};

function renderBar(result = mockResult, onFixAll?: () => void) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>
        <GapSummaryBar result={result} onFixAll={onFixAll} />
      </MemoryRouter>
    </FluentProvider>
  );
}

describe("GapSummaryBar", () => {
  it("renders without crashing", () => {
    const { container } = renderBar();
    expect(container).toBeTruthy();
  });

  it("shows severity counts", () => {
    renderBar();
    expect(screen.getByText(/1 Critical/i)).toBeInTheDocument();
    expect(screen.getByText(/2 High/i)).toBeInTheDocument();
    expect(screen.getByText(/2 Medium/i)).toBeInTheDocument();
    expect(screen.getByText(/1 Low/i)).toBeInTheDocument();
  });

  it("shows the Fix All button", () => {
    renderBar();
    expect(screen.getByRole("button", { name: /fix all/i })).toBeInTheDocument();
  });

  it("shows Overall Health text", () => {
    renderBar();
    expect(screen.getByText(/Overall Health/i)).toBeInTheDocument();
  });

  it("shows 100% health when there are no findings", () => {
    const emptyResult: GapAnalysisResponse = {
      ...mockResult,
      total_findings: 0,
      critical_count: 0,
      high_count: 0,
      medium_count: 0,
      low_count: 0,
    };
    renderBar(emptyResult);
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("opens confirmation dialog when Fix All is clicked", async () => {
    const user = userEvent.setup();
    renderBar();
    await user.click(screen.getByRole("button", { name: /fix all/i }));
    expect(screen.getByText(/Confirm Fix All/i)).toBeInTheDocument();
  });

  it("calls onFixAll when Confirm is clicked in dialog", async () => {
    const onFixAll = vi.fn();
    const user = userEvent.setup();
    renderBar(mockResult, onFixAll);
    await user.click(screen.getByRole("button", { name: /fix all/i }));
    await user.click(screen.getByRole("button", { name: /^confirm$/i }));
    expect(onFixAll).toHaveBeenCalledOnce();
  });
});
