import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";
import IaCFormatSelector from "./IaCFormatSelector";
import type { IaCFormat } from "./IaCFormatSelector";

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>{ui}</MemoryRouter>
    </FluentProvider>,
  );
}

describe("IaCFormatSelector", () => {
  it("renders all five format tabs", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <IaCFormatSelector selectedFormat="bicep" onFormatChange={onChange} />,
    );
    expect(screen.getByRole("tab", { name: /bicep/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /terraform/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /arm/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /pulumi \(typescript\)/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /pulumi \(python\)/i })).toBeInTheDocument();
  });

  it("shows description for selected format", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <IaCFormatSelector selectedFormat="bicep" onFormatChange={onChange} />,
    );
    expect(screen.getByText(/azure-native declarative iac/i)).toBeInTheDocument();
  });

  it("shows terraform description when terraform is selected", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <IaCFormatSelector selectedFormat="terraform" onFormatChange={onChange} />,
    );
    expect(screen.getByText(/multi-cloud hcl configuration/i)).toBeInTheDocument();
  });

  it("calls onFormatChange when a tab is clicked", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderWithProviders(
      <IaCFormatSelector selectedFormat="bicep" onFormatChange={onChange} />,
    );
    await user.click(screen.getByRole("tab", { name: /terraform/i }));
    expect(onChange).toHaveBeenCalledWith("terraform");
  });

  it("defaults bicep as selected", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <IaCFormatSelector selectedFormat="bicep" onFormatChange={onChange} />,
    );
    const bicepTab = screen.getByRole("tab", { name: /bicep/i });
    expect(bicepTab).toHaveAttribute("aria-selected", "true");
  });

  it("has accessible tablist label", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <IaCFormatSelector selectedFormat="bicep" onFormatChange={onChange} />,
    );
    expect(screen.getByRole("tablist", { name: /infrastructure as code format/i })).toBeInTheDocument();
  });

  it("respects disabled prop", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <IaCFormatSelector selectedFormat="bicep" onFormatChange={onChange} disabled />,
    );
    const tabs = screen.getAllByRole("tab");
    tabs.forEach((tab) => {
      expect(tab).toBeDisabled();
    });
  });

  it("correctly types the format values", () => {
    const formats: IaCFormat[] = ["bicep", "terraform", "arm", "pulumi_ts", "pulumi_python"];
    expect(formats).toHaveLength(5);
  });
});
