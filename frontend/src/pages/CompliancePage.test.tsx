import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import CompliancePage from "./CompliancePage";

const mockArchitecture = {
  organization_size: "small",
  management_groups: {},
  subscriptions: [],
  network_topology: {},
};

function renderPage() {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <CompliancePage />
    </FluentProvider>
  );
}

describe("CompliancePage", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it("shows warning when no architecture is stored", () => {
    renderPage();
    expect(screen.getByText(/no architecture found/i)).toBeInTheDocument();
  });

  it("renders page title when architecture exists", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(screen.getByText(/compliance scoring/i)).toBeInTheDocument();
  });

  it("renders framework checkboxes when architecture exists", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(screen.getByText("SOC 2")).toBeInTheDocument();
    expect(screen.getByText("HIPAA")).toBeInTheDocument();
    expect(screen.getByText("PCI-DSS")).toBeInTheDocument();
  });

  it("renders without crashing", () => {
    const { container } = renderPage();
    expect(container).toBeTruthy();
  });

  it("toggles framework selection on click", async () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    const user = userEvent.setup();
    renderPage();
    const soc2Card = screen.getByText("SOC 2").closest("[role='option'], [role='checkbox'], div[class]")?.parentElement;
    if (soc2Card) await user.click(soc2Card);
    else await user.click(screen.getByText("SOC 2"));
  });

  it("score button exists", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(screen.getByRole("button", { name: /score architecture/i })).toBeInTheDocument();
  });
});
