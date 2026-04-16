import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";
import CodePreview from "./CodePreview";
import type { CodeFile, ValidationResult } from "./CodePreview";

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>{ui}</MemoryRouter>
    </FluentProvider>,
  );
}

const sampleFiles: CodeFile[] = [
  {
    name: "main.bicep",
    content: "targetScope = 'managementGroup'",
    size_bytes: 32,
  },
  {
    name: "network.bicep",
    content: "resource vnet 'Microsoft.Network/virtualNetworks@2023-01-01'",
    size_bytes: 64,
  },
];

describe("CodePreview", () => {
  it("shows empty state when no files provided", () => {
    renderWithProviders(<CodePreview files={[]} />);
    expect(screen.getByText(/no files generated yet/i)).toBeInTheDocument();
  });

  it("renders file count", () => {
    renderWithProviders(<CodePreview files={sampleFiles} formatLabel="Bicep" />);
    expect(screen.getByText(/bicep — 2 files/i)).toBeInTheDocument();
  });

  it("renders file tabs when multiple files", () => {
    renderWithProviders(<CodePreview files={sampleFiles} />);
    expect(screen.getByRole("tab", { name: /main\.bicep/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /network\.bicep/i })).toBeInTheDocument();
  });

  it("displays first file content by default", () => {
    renderWithProviders(<CodePreview files={sampleFiles} />);
    expect(screen.getByTestId("code-content")).toHaveTextContent(
      "targetScope = 'managementGroup'",
    );
  });

  it("switches file content when tab is clicked", async () => {
    const user = userEvent.setup();
    renderWithProviders(<CodePreview files={sampleFiles} />);
    await user.click(screen.getByRole("tab", { name: /network\.bicep/i }));
    expect(screen.getByTestId("code-content")).toHaveTextContent(
      "resource vnet",
    );
  });

  it("does not show tabs for single file", () => {
    renderWithProviders(<CodePreview files={[sampleFiles[0]]} />);
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
  });

  it("renders download button when onDownload is provided", () => {
    const onDownload = vi.fn();
    renderWithProviders(
      <CodePreview files={sampleFiles} onDownload={onDownload} />,
    );
    expect(screen.getByRole("button", { name: /download/i })).toBeInTheDocument();
  });

  it("calls onDownload when download button is clicked", async () => {
    const user = userEvent.setup();
    const onDownload = vi.fn();
    renderWithProviders(
      <CodePreview files={sampleFiles} onDownload={onDownload} />,
    );
    await user.click(screen.getByRole("button", { name: /download/i }));
    expect(onDownload).toHaveBeenCalledOnce();
  });

  it("renders validate button when onValidate is provided", () => {
    const onValidate = vi.fn().mockResolvedValue({ is_valid: true, errors: [], warnings: [] });
    renderWithProviders(
      <CodePreview files={sampleFiles} onValidate={onValidate} />,
    );
    expect(screen.getByRole("button", { name: /validate/i })).toBeInTheDocument();
  });

  it("shows validation success result", async () => {
    const user = userEvent.setup();
    const onValidate = vi.fn().mockResolvedValue({
      is_valid: true,
      errors: [],
      warnings: [],
    } satisfies ValidationResult);
    renderWithProviders(
      <CodePreview files={sampleFiles} onValidate={onValidate} />,
    );
    await user.click(screen.getByRole("button", { name: /validate/i }));
    await waitFor(() => {
      expect(screen.getByText(/validation passed/i)).toBeInTheDocument();
    });
  });

  it("shows validation failure with errors", async () => {
    const user = userEvent.setup();
    const onValidate = vi.fn().mockResolvedValue({
      is_valid: false,
      errors: [{ line: 5, message: "Missing required property", severity: "error" }],
      warnings: [],
    } satisfies ValidationResult);
    renderWithProviders(
      <CodePreview files={sampleFiles} onValidate={onValidate} />,
    );
    await user.click(screen.getByRole("button", { name: /validate/i }));
    await waitFor(() => {
      expect(screen.getByText(/validation failed/i)).toBeInTheDocument();
      expect(screen.getByText(/line 5.*missing required property/i)).toBeInTheDocument();
    });
  });

  it("handles validate error gracefully", async () => {
    const user = userEvent.setup();
    const onValidate = vi.fn().mockRejectedValue(new Error("Network error"));
    renderWithProviders(
      <CodePreview files={sampleFiles} onValidate={onValidate} />,
    );
    await user.click(screen.getByRole("button", { name: /validate/i }));
    await waitFor(() => {
      expect(screen.getByText(/validation request failed/i)).toBeInTheDocument();
    });
  });

  it("shows file size badges", () => {
    renderWithProviders(<CodePreview files={sampleFiles} />);
    const badges = screen.getAllByText(/KB/);
    expect(badges.length).toBeGreaterThanOrEqual(2);
  });

  it("does not show download or validate buttons when callbacks omitted", () => {
    renderWithProviders(<CodePreview files={sampleFiles} />);
    expect(screen.queryByRole("button", { name: /download/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /validate/i })).not.toBeInTheDocument();
  });
});
