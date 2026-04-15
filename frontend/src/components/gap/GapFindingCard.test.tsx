import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";
import GapFindingCard from "./GapFindingCard";
import type { GapFinding } from "../../services/api";

const mockFinding: GapFinding = {
  id: "f-1",
  category: "networking",
  severity: "critical",
  title: "Missing network segmentation",
  description: "No network segmentation found in the environment.",
  remediation: "Implement hub-spoke topology with Azure Firewall.",
  caf_reference: "CAF/networking/hub-spoke",
  can_auto_remediate: false,
};

const highFinding: GapFinding = {
  ...mockFinding,
  id: "f-2",
  severity: "high",
  title: "High severity issue",
};

const mediumFinding: GapFinding = {
  ...mockFinding,
  id: "f-3",
  severity: "medium",
  title: "Medium severity issue",
};

const lowFinding: GapFinding = {
  ...mockFinding,
  id: "f-4",
  severity: "low",
  title: "Low severity issue",
  caf_reference: undefined,
};

function renderCard(finding = mockFinding, onAddToArchitecture?: (f: GapFinding) => void) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>
        <GapFindingCard finding={finding} onAddToArchitecture={onAddToArchitecture} />
      </MemoryRouter>
    </FluentProvider>
  );
}

describe("GapFindingCard", () => {
  it("renders without crashing", () => {
    const { container } = renderCard();
    expect(container).toBeTruthy();
  });

  it("shows the finding title", () => {
    renderCard();
    expect(screen.getByText("Missing network segmentation")).toBeInTheDocument();
  });

  it("shows the severity badge for critical", () => {
    renderCard();
    expect(screen.getByText("Critical")).toBeInTheDocument();
  });

  it("shows the severity badge for high", () => {
    renderCard(highFinding);
    expect(screen.getByText("High")).toBeInTheDocument();
  });

  it("shows the severity badge for medium", () => {
    renderCard(mediumFinding);
    expect(screen.getByText("Medium")).toBeInTheDocument();
  });

  it("shows the severity badge for low", () => {
    renderCard(lowFinding);
    expect(screen.getByText("Low")).toBeInTheDocument();
  });

  it("is collapsed by default — description not visible", () => {
    renderCard();
    expect(screen.queryByText("No network segmentation found in the environment.")).not.toBeInTheDocument();
  });

  it("expands when clicked to show description", async () => {
    const user = userEvent.setup();
    renderCard();
    const header = screen.getAllByRole("button")[0];
    await user.click(header);
    expect(screen.getByText("No network segmentation found in the environment.")).toBeInTheDocument();
  });

  it("shows CAF reference when expanded", async () => {
    const user = userEvent.setup();
    renderCard();
    await user.click(screen.getAllByRole("button")[0]);
    expect(screen.getByText("CAF/networking/hub-spoke")).toBeInTheDocument();
  });

  it("shows remediation when expanded", async () => {
    const user = userEvent.setup();
    renderCard();
    await user.click(screen.getAllByRole("button")[0]);
    expect(screen.getByText("Implement hub-spoke topology with Azure Firewall.")).toBeInTheDocument();
  });

  it("shows Add to Architecture button when expanded", async () => {
    const user = userEvent.setup();
    renderCard();
    await user.click(screen.getAllByRole("button")[0]);
    expect(screen.getByRole("button", { name: /add to architecture/i })).toBeInTheDocument();
  });

  it("calls onAddToArchitecture when Add to Architecture is clicked", async () => {
    const onAdd = vi.fn();
    const user = userEvent.setup();
    renderCard(mockFinding, onAdd);
    await user.click(screen.getAllByRole("button")[0]);
    await user.click(screen.getByRole("button", { name: /add to architecture/i }));
    expect(onAdd).toHaveBeenCalledWith(mockFinding);
  });

  it("collapses again when clicked twice", async () => {
    const user = userEvent.setup();
    renderCard();
    const header = screen.getAllByRole("button")[0];
    await user.click(header);
    await user.click(header);
    expect(screen.queryByText("No network segmentation found in the environment.")).not.toBeInTheDocument();
  });
});
