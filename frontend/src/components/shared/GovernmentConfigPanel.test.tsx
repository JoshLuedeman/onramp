import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";
import GovernmentConfigPanel from "./GovernmentConfigPanel";
import type { GovernmentConfig } from "./GovernmentConfigPanel";

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>{ui}</MemoryRouter>
    </FluentProvider>,
  );
}

const DEFAULT_CONFIG: GovernmentConfig = {
  impactLevel: "IL2",
  dodWorkload: false,
  fedrampLevel: "high",
  itarRequired: false,
  region: "usgovvirginia",
};

describe("GovernmentConfigPanel", () => {
  it("renders the panel with header and all sections", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <GovernmentConfigPanel config={DEFAULT_CONFIG} onConfigChange={onChange} />,
    );
    expect(
      screen.getByText("Azure Government Configuration"),
    ).toBeInTheDocument();
    expect(screen.getByText("Impact Level (IL)")).toBeInTheDocument();
    expect(screen.getByText("FedRAMP Authorization Level")).toBeInTheDocument();
    expect(screen.getByText("DoD Workload")).toBeInTheDocument();
    expect(screen.getByText("ITAR Compliance Required")).toBeInTheDocument();
    expect(screen.getByText("Government Region")).toBeInTheDocument();
  });

  it("selects the correct impact level radio", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <GovernmentConfigPanel
        config={{ ...DEFAULT_CONFIG, impactLevel: "IL4" }}
        onConfigChange={onChange}
      />,
    );
    const il4Radio = screen.getByRole("radio", {
      name: /IL4 — Controlled Unclassified Information/i,
    });
    expect(il4Radio).toBeChecked();
  });

  it("calls onConfigChange when impact level changes", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderWithProviders(
      <GovernmentConfigPanel config={DEFAULT_CONFIG} onConfigChange={onChange} />,
    );
    const il5Radio = screen.getByRole("radio", {
      name: /IL5/i,
    });
    await user.click(il5Radio);
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ impactLevel: "IL5" }),
    );
  });

  it("displays region dropdown with grouped options", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderWithProviders(
      <GovernmentConfigPanel config={DEFAULT_CONFIG} onConfigChange={onChange} />,
    );
    await user.click(screen.getByRole("combobox"));
    expect(screen.getByText("Non-DoD Regions")).toBeInTheDocument();
    expect(screen.getByText("DoD Regions")).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: /US Gov Virginia/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: /US DoD Central/i }),
    ).toBeInTheDocument();
  });

  it("toggles ITAR checkbox", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderWithProviders(
      <GovernmentConfigPanel config={DEFAULT_CONFIG} onConfigChange={onChange} />,
    );
    const itarCheckbox = screen.getByRole("checkbox", {
      name: /ITAR Compliance Required/i,
    });
    await user.click(itarCheckbox);
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ itarRequired: true }),
    );
  });

  it("respects disabled prop on all inputs", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <GovernmentConfigPanel
        config={DEFAULT_CONFIG}
        onConfigChange={onChange}
        disabled
      />,
    );
    const radios = screen.getAllByRole("radio");
    for (const radio of radios) {
      expect(radio).toBeDisabled();
    }
    const checkboxes = screen.getAllByRole("checkbox");
    for (const cb of checkboxes) {
      expect(cb).toBeDisabled();
    }
    expect(screen.getByRole("combobox")).toBeDisabled();
  });
});
