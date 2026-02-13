import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import BicepPage from "./BicepPage";

const mockArchitecture = {
  organization_size: "small",
  management_groups: {},
  subscriptions: [],
  network_topology: { type: "hub-spoke" },
};

// Mock fetch for generate endpoint
const mockFetch = vi.fn();

function renderPage() {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <BicepPage />
    </FluentProvider>,
  );
}

describe("BicepPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    sessionStorage.clear();
    vi.stubGlobal("fetch", mockFetch);
  });

  it("shows warning when no architecture is stored", () => {
    renderPage();
    expect(screen.getByText(/no architecture found/i)).toBeInTheDocument();
    expect(screen.getByText(/complete the wizard first/i)).toBeInTheDocument();
  });

  it("renders page title when architecture exists", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(screen.getByText(/bicep templates/i)).toBeInTheDocument();
  });

  it("renders the generate button when architecture exists", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(screen.getByRole("button", { name: /generate bicep/i })).toBeInTheDocument();
  });

  it("renders description text", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(
      screen.getByText(/generate deployable bicep infrastructure as code/i),
    ).toBeInTheDocument();
  });

  it("does not show download button before generating", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(screen.queryByRole("button", { name: /download all/i })).not.toBeInTheDocument();
  });

  it("renders without crashing", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    const { container } = renderPage();
    expect(container).toBeTruthy();
  });

  it("shows generated files after clicking generate", async () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        files: [
          { name: "main.bicep", content: "targetScope = 'managementGroup'", size_bytes: 32 },
          { name: "policies.bicep", content: "resource policy 'Microsoft.Authorization/policyDefinitions@2021-06-01'", size_bytes: 50 },
        ],
        total_files: 2,
        ai_generated: false,
      }),
    });
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("button", { name: /generate bicep/i }));
    expect(await screen.findByText(/main\.bicep/i)).toBeInTheDocument();
    expect(screen.getByText(/policies\.bicep/i)).toBeInTheDocument();
  });
});
