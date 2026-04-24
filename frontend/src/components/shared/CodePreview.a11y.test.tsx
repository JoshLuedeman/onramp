/**
 * CodePreview WCAG 2.1 AA accessibility tests.
 *
 * Tests code block semantics, file tab ARIA, button labels,
 * and validation result announcements.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import CodePreview from "./CodePreview";
import type { CodeFile, ValidationResult } from "./CodePreview";

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const singleFile: CodeFile[] = [
  {
    name: "main.bicep",
    content: "targetScope = 'resourceGroup'\nparam location string",
    size_bytes: 1024,
  },
];

const multipleFiles: CodeFile[] = [
  {
    name: "main.bicep",
    content: "targetScope = 'resourceGroup'",
    size_bytes: 512,
  },
  {
    name: "modules/network.bicep",
    content: "param vnetName string",
    size_bytes: 256,
  },
  {
    name: "modules/storage.bicep",
    content: "param storageAccountName string",
    size_bytes: 384,
  },
];

const validResult: ValidationResult = {
  is_valid: true,
  errors: [],
  warnings: [],
};

const invalidResult: ValidationResult = {
  is_valid: false,
  errors: [
    { line: 5, message: "Missing required parameter", severity: "error" },
  ],
  warnings: [
    { line: 12, message: "Unused variable", severity: "warning" },
  ],
};

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function renderCodePreview(
  props: Partial<React.ComponentProps<typeof CodePreview>> = {},
) {
  const defaults = {
    files: multipleFiles,
    onDownload: vi.fn(),
    onValidate: vi.fn().mockResolvedValue(validResult),
  };
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <CodePreview {...defaults} {...props} />
    </FluentProvider>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("CodePreview Accessibility", () => {
  // 1 — Code block uses <pre> and <code> elements
  it("code content uses semantic <pre> and <code> elements", () => {
    renderCodePreview({ files: singleFile });
    const preEl = document.querySelector("pre");
    expect(preEl).toBeInTheDocument();

    const codeEl = preEl!.querySelector("code");
    expect(codeEl).toBeInTheDocument();
    expect(codeEl!.textContent).toContain("targetScope");
  });

  // 2 — File tab list has proper ARIA label when multiple files
  it("file tab list has aria-label for generated files", () => {
    renderCodePreview();
    const tablist = screen.getByRole("tablist", { name: "Generated files" });
    expect(tablist).toBeInTheDocument();
  });

  // 3 — File tabs have accessible names
  it("file tabs have accessible names matching file names", () => {
    renderCodePreview();
    const tabs = screen.getAllByRole("tab");
    expect(tabs.length).toBe(3);

    expect(screen.getByRole("tab", { name: /main\.bicep/ })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /network\.bicep/ })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /storage\.bicep/ })).toBeInTheDocument();
  });

  // 4 — Selected file tab has aria-selected="true"
  it("selected file tab has aria-selected=true", () => {
    renderCodePreview();
    const firstTab = screen.getByRole("tab", { name: /main\.bicep/ });
    expect(firstTab).toHaveAttribute("aria-selected", "true");
  });

  // 5 — Tab list is not rendered for single file
  it("tab list is not rendered when only one file exists", () => {
    renderCodePreview({ files: singleFile });
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
  });

  // 6 — Download button has accessible name
  it("Download button has accessible label", () => {
    renderCodePreview();
    const downloadBtn = screen.getByRole("button", { name: /download/i });
    expect(downloadBtn).toBeInTheDocument();
  });

  // 7 — Validate button has accessible name
  it("Validate button has accessible label", () => {
    renderCodePreview();
    const validateBtn = screen.getByRole("button", { name: /validate/i });
    expect(validateBtn).toBeInTheDocument();
  });

  // 8 — Validation success is announced with a status message
  it("validation success result is displayed in a status message", async () => {
    const user = userEvent.setup();
    renderCodePreview({
      onValidate: vi.fn().mockResolvedValue(validResult),
    });

    await user.click(screen.getByRole("button", { name: /validate/i }));

    const successMsg = await screen.findByText(/Validation passed/);
    expect(successMsg).toBeInTheDocument();
    expect(successMsg).toBeVisible();
  });

  // 9 — Validation failure shows error details
  it("validation failure result displays error and warning details", async () => {
    const user = userEvent.setup();
    renderCodePreview({
      onValidate: vi.fn().mockResolvedValue(invalidResult),
    });

    await user.click(screen.getByRole("button", { name: /validate/i }));

    const failureMsg = await screen.findByText(/Validation failed/);
    expect(failureMsg).toBeInTheDocument();

    // Error details are visible
    expect(screen.getByText(/Missing required parameter/)).toBeInTheDocument();
    expect(screen.getByText(/Line 5/)).toBeInTheDocument();

    // Warning details are visible
    expect(screen.getByText(/Unused variable/)).toBeInTheDocument();
    expect(screen.getByText(/Line 12/)).toBeInTheDocument();
  });

  // 10 — Empty state is accessible
  it("empty state renders accessible text", () => {
    renderCodePreview({ files: [] });
    expect(
      screen.getByText(/No files generated yet/),
    ).toBeInTheDocument();
  });

  // 11 — Validate button is disabled during validation
  it("Validate button is disabled during validation", async () => {
    const user = userEvent.setup();
    let resolveValidation!: (value: ValidationResult) => void;
    const slowValidate = vi.fn(
      () => new Promise<ValidationResult>((resolve) => { resolveValidation = resolve; }),
    );

    renderCodePreview({ onValidate: slowValidate });

    await user.click(screen.getByRole("button", { name: /validate/i }));

    // Button should be disabled while validating
    expect(screen.getByRole("button", { name: /validate/i })).toBeDisabled();

    // Resolve to clean up
    resolveValidation(validResult);
    await screen.findByText(/Validation passed/);
  });

  // 12 — Download button is not rendered when no onDownload handler
  it("Download button is not rendered when onDownload is not provided", () => {
    renderCodePreview({ onDownload: undefined });
    expect(screen.queryByRole("button", { name: /download/i })).not.toBeInTheDocument();
  });

  // 13 — Validate button is not rendered when no onValidate handler
  it("Validate button is not rendered when onValidate is not provided", () => {
    renderCodePreview({ onValidate: undefined });
    expect(screen.queryByRole("button", { name: /validate/i })).not.toBeInTheDocument();
  });
});
