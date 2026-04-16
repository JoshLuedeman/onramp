import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";
import CloudEnvironmentSelector from "./CloudEnvironmentSelector";
import type { CloudEnvironmentName } from "./CloudEnvironmentSelector";
import { CLOUD_ENVIRONMENTS } from "./CloudEnvironmentSelector";

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>{ui}</MemoryRouter>
    </FluentProvider>,
  );
}

describe("CloudEnvironmentSelector", () => {
  it("renders with default commercial environment", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <CloudEnvironmentSelector
        selectedEnvironment="commercial"
        onChange={onChange}
      />,
    );
    expect(screen.getByText(/global azure public cloud/i)).toBeInTheDocument();
  });

  it("renders all three environment options in dropdown", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderWithProviders(
      <CloudEnvironmentSelector
        selectedEnvironment="commercial"
        onChange={onChange}
      />,
    );
    // Open the dropdown
    await user.click(screen.getByRole("combobox"));
    expect(screen.getByRole("option", { name: /azure commercial/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /azure government/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /azure china/i })).toBeInTheDocument();
  });

  it("calls onChange when a different environment is selected", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderWithProviders(
      <CloudEnvironmentSelector
        selectedEnvironment="commercial"
        onChange={onChange}
      />,
    );
    await user.click(screen.getByRole("combobox"));
    await user.click(screen.getByRole("option", { name: /azure government/i }));
    expect(onChange).toHaveBeenCalledWith("government");
  });

  it("shows restriction tooltip text for government environment", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <CloudEnvironmentSelector
        selectedEnvironment="government"
        onChange={onChange}
      />,
    );
    expect(screen.getByText(/restrictions apply/i)).toBeInTheDocument();
  });

  it("shows restriction tooltip text for china environment", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <CloudEnvironmentSelector
        selectedEnvironment="china"
        onChange={onChange}
      />,
    );
    expect(screen.getByText(/restrictions apply/i)).toBeInTheDocument();
  });

  it("does not show restrictions for commercial environment", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <CloudEnvironmentSelector
        selectedEnvironment="commercial"
        onChange={onChange}
      />,
    );
    expect(screen.queryByText(/restrictions apply/i)).not.toBeInTheDocument();
  });

  it("respects disabled prop", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <CloudEnvironmentSelector
        selectedEnvironment="commercial"
        onChange={onChange}
        disabled
      />,
    );
    const combobox = screen.getByRole("combobox");
    expect(combobox).toBeDisabled();
  });

  it("has accessible combobox label", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <CloudEnvironmentSelector
        selectedEnvironment="commercial"
        onChange={onChange}
      />,
    );
    expect(
      screen.getByRole("combobox", { name: /cloud environment/i }),
    ).toBeInTheDocument();
  });

  it("exports CLOUD_ENVIRONMENTS constant with three entries", () => {
    const values: CloudEnvironmentName[] = CLOUD_ENVIRONMENTS.map((e) => e.value);
    expect(values).toEqual(["commercial", "government", "china"]);
  });

  it("shows description for the selected environment", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <CloudEnvironmentSelector
        selectedEnvironment="china"
        onChange={onChange}
      />,
    );
    const matches = screen.getAllByText(/operated by 21vianet/i);
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });
});
