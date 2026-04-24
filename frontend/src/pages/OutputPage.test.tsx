import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";
import OutputPage from "./OutputPage";

const mockArchitecture = {
  organization_size: "small",
  management_groups: {},
  subscriptions: [],
  network_topology: { type: "hub-spoke" },
};

const mockFetch = vi.fn();

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>{ui}</MemoryRouter>
    </FluentProvider>,
  );
}

describe("OutputPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    sessionStorage.clear();
    vi.stubGlobal("fetch", mockFetch);
    // Default: versions report returns empty
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          staleness_threshold_days: 90,
          terraform: [],
          pulumi_typescript: [],
          pulumi_python: [],
          arm: [],
          bicep: [],
          total_entries: 0,
          stale_count: 0,
        }),
    });
  });

  it("shows warning when no architecture is stored", () => {
    renderWithProviders(<OutputPage />);
    expect(screen.getByText(/no architecture found/i)).toBeInTheDocument();
  });

  it("renders page title when architecture exists", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderWithProviders(<OutputPage />);
    expect(screen.getByText(/infrastructure as code output/i)).toBeInTheDocument();
  });

  it("renders IaC format selector with all tabs", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderWithProviders(<OutputPage />);
    // Multiple IaC selectors on page (main + pipeline), just verify they exist
    const bicepTabs = screen.getAllByRole("tab", { name: /bicep/i });
    expect(bicepTabs.length).toBeGreaterThanOrEqual(1);
    const terraformTabs = screen.getAllByRole("tab", { name: /terraform/i });
    expect(terraformTabs.length).toBeGreaterThanOrEqual(1);
    const armTabs = screen.getAllByRole("tab", { name: /arm/i });
    expect(armTabs.length).toBeGreaterThanOrEqual(1);
  });

  it("renders generate button with default Bicep label", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderWithProviders(<OutputPage />);
    expect(screen.getByRole("button", { name: /generate bicep/i })).toBeInTheDocument();
  });

  it("updates generate button label when format changes", async () => {
    const user = userEvent.setup();
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderWithProviders(<OutputPage />);
    // Click the first Terraform tab (in the main IaC selector, not the pipeline one)
    const terraformTabs = screen.getAllByRole("tab", { name: /terraform/i });
    await user.click(terraformTabs[0]);
    expect(screen.getByRole("button", { name: /generate terraform/i })).toBeInTheDocument();
  });

  it("renders pipeline format selector section", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderWithProviders(<OutputPage />);
    expect(screen.getByText(/ci\/cd pipeline generation/i)).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /github actions/i })).toBeInTheDocument();
  });

  it("renders generate pipeline button", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderWithProviders(<OutputPage />);
    expect(screen.getByRole("button", { name: /generate pipeline/i })).toBeInTheDocument();
  });

  it("renders version pinning section", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderWithProviders(<OutputPage />);
    expect(screen.getByText(/version pinning/i)).toBeInTheDocument();
  });

  it("shows generated files after clicking generate", async () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    // First call: versions report; second call: generate
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            staleness_threshold_days: 90,
            terraform: [],
            pulumi_typescript: [],
            pulumi_python: [],
            arm: [],
            bicep: [],
            total_entries: 0,
            stale_count: 0,
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            files: [
              { name: "main.bicep", content: "targetScope = 'managementGroup'", size_bytes: 32 },
            ],
            total_files: 1,
            ai_generated: false,
          }),
      });
    const user = userEvent.setup();
    renderWithProviders(<OutputPage />);
    await user.click(screen.getByRole("button", { name: /generate bicep/i }));
    await waitFor(() => {
      expect(screen.getByText(/bicep — 1 file/i)).toBeInTheDocument();
    });
  });

  it("shows error when generation fails", async () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            staleness_threshold_days: 90,
            terraform: [],
            pulumi_typescript: [],
            pulumi_python: [],
            arm: [],
            bicep: [],
            total_entries: 0,
            stale_count: 0,
          }),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
      });
    const user = userEvent.setup();
    renderWithProviders(<OutputPage />);
    await user.click(screen.getByRole("button", { name: /generate bicep/i }));
    await waitFor(() => {
      expect(screen.getByText(/api error/i)).toBeInTheDocument();
    });
  });

  it("shows version entries when available", async () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          staleness_threshold_days: 90,
          terraform: [{ name: "azurerm", version: "3.75.0", is_stale: false, age_days: 10, release_date: "2024-01-01" }],
          pulumi_typescript: [],
          pulumi_python: [],
          arm: [],
          bicep: [],
          total_entries: 1,
          stale_count: 0,
        }),
    });
    renderWithProviders(<OutputPage />);
    await waitFor(() => {
      expect(screen.getByText("azurerm")).toBeInTheDocument();
      expect(screen.getByText("3.75.0")).toBeInTheDocument();
    });
  });

  it("renders without crashing", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    const { container } = renderWithProviders(<OutputPage />);
    expect(container).toBeTruthy();
  });
});
