import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";
import PipelineFormatSelector from "./PipelineFormatSelector";
import type { PipelineConfig } from "./PipelineFormatSelector";

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>{ui}</MemoryRouter>
    </FluentProvider>,
  );
}

const defaultConfig: PipelineConfig = {
  pipelineFormat: "github_actions",
  iacFormat: "bicep",
  serviceConnection: "",
};

describe("PipelineFormatSelector", () => {
  it("renders pipeline provider radio buttons", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <PipelineFormatSelector config={defaultConfig} onConfigChange={onChange} />,
    );
    expect(screen.getByRole("radio", { name: /github actions/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /azure devops pipelines/i })).toBeInTheDocument();
  });

  it("shows GitHub Actions description by default", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <PipelineFormatSelector config={defaultConfig} onConfigChange={onChange} />,
    );
    expect(screen.getByText(/generates workflow yaml files for github actions/i)).toBeInTheDocument();
  });

  it("calls onConfigChange when pipeline format is changed", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderWithProviders(
      <PipelineFormatSelector config={defaultConfig} onConfigChange={onChange} />,
    );
    await user.click(screen.getByRole("radio", { name: /azure devops pipelines/i }));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ pipelineFormat: "azure_devops" }),
    );
  });

  it("shows service connection input when Azure DevOps is selected", () => {
    const adoConfig: PipelineConfig = {
      ...defaultConfig,
      pipelineFormat: "azure_devops",
    };
    const onChange = vi.fn();
    renderWithProviders(
      <PipelineFormatSelector config={adoConfig} onConfigChange={onChange} />,
    );
    expect(screen.getByLabelText(/service connection name/i)).toBeInTheDocument();
  });

  it("does not show service connection input for GitHub Actions", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <PipelineFormatSelector config={defaultConfig} onConfigChange={onChange} />,
    );
    expect(screen.queryByLabelText(/service connection name/i)).not.toBeInTheDocument();
  });

  it("includes IaC format sub-selector", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <PipelineFormatSelector config={defaultConfig} onConfigChange={onChange} />,
    );
    expect(screen.getByText(/target iac format/i)).toBeInTheDocument();
    expect(screen.getByRole("tablist", { name: /infrastructure as code format/i })).toBeInTheDocument();
  });

  it("propagates IaC format change to config", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderWithProviders(
      <PipelineFormatSelector config={defaultConfig} onConfigChange={onChange} />,
    );
    await user.click(screen.getByRole("tab", { name: /terraform/i }));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ iacFormat: "terraform" }),
    );
  });

  it("updates service connection value", async () => {
    const user = userEvent.setup();
    const adoConfig: PipelineConfig = {
      ...defaultConfig,
      pipelineFormat: "azure_devops",
    };
    const onChange = vi.fn();
    renderWithProviders(
      <PipelineFormatSelector config={adoConfig} onConfigChange={onChange} />,
    );
    const input = screen.getByLabelText(/service connection name/i);
    await user.type(input, "MyConn");
    // The last call should contain at least the last typed char
    expect(onChange).toHaveBeenCalled();
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0] as PipelineConfig;
    expect(lastCall.serviceConnection).toBeTruthy();
  });

  it("respects disabled prop", () => {
    const onChange = vi.fn();
    renderWithProviders(
      <PipelineFormatSelector config={defaultConfig} onConfigChange={onChange} disabled />,
    );
    const radios = screen.getAllByRole("radio");
    radios.forEach((radio) => {
      expect(radio).toBeDisabled();
    });
  });
});
