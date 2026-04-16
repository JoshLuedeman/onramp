import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";
import ChinaConfigPanel, { CHINA_REGIONS } from "./ChinaConfigPanel";
import type { ChinaConfig } from "./ChinaConfigPanel";

const defaultConfig: ChinaConfig = {
  icpLicenseStatus: "no",
  mlpsLevel: "level3",
  region: "chinanorth2",
  dataResidency: "mainland_only",
  supportTier: "standard",
};

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>{ui}</MemoryRouter>
    </FluentProvider>,
  );
}

describe("ChinaConfigPanel", () => {
  it("renders the panel header", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <ChinaConfigPanel config={defaultConfig} onConfigChange={onChange} />,
    );
    expect(
      screen.getByText(/azure china \(21vianet\) configuration/i),
    ).toBeInTheDocument();
  });

  it("shows data residency indicator for mainland only", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <ChinaConfigPanel config={defaultConfig} onConfigChange={onChange} />,
    );
    // "Mainland China only" appears in both the badge and radio label
    const matches = screen.getAllByText(/mainland china only/i);
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it("shows Hong Kong when data residency includes it", () => {
    const onChange = vi.fn();
    const config: ChinaConfig = { ...defaultConfig, dataResidency: "include_hongkong" };
    renderWithProviders(
      <ChinaConfigPanel config={config} onConfigChange={onChange} />,
    );
    const matches = screen.getAllByText(/hong kong included/i);
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it("calls onConfigChange when ICP status is changed", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderWithProviders(
      <ChinaConfigPanel config={defaultConfig} onConfigChange={onChange} />,
    );
    // Click "Yes — licensed" radio
    await user.click(screen.getByLabelText(/yes — licensed/i));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ icpLicenseStatus: "yes" }),
    );
  });

  it("calls onConfigChange when MLPS level is changed", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderWithProviders(
      <ChinaConfigPanel config={defaultConfig} onConfigChange={onChange} />,
    );
    await user.click(screen.getByLabelText(/level 4 — critical systems/i));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ mlpsLevel: "level4" }),
    );
  });

  it("shows paired region info for selected region", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <ChinaConfigPanel config={defaultConfig} onConfigChange={onChange} />,
    );
    expect(screen.getByText(/paired region/i)).toBeInTheDocument();
  });

  it("disables all inputs when disabled prop is true", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <ChinaConfigPanel config={defaultConfig} onConfigChange={onChange} disabled />,
    );
    const radios = screen.getAllByRole("radio");
    radios.forEach((radio) => {
      expect(radio).toBeDisabled();
    });
  });

  it("exports CHINA_REGIONS with six entries", () => {
    expect(CHINA_REGIONS).toHaveLength(6);
    const names = CHINA_REGIONS.map((r) => r.name);
    expect(names).toContain("chinanorth");
    expect(names).toContain("chinaeast3");
  });

  it("renders with testid for integration targeting", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <ChinaConfigPanel config={defaultConfig} onConfigChange={onChange} />,
    );
    expect(screen.getByTestId("china-config-panel")).toBeInTheDocument();
  });
});
