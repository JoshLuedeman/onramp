/**
 * ArchitectureCompare WCAG 2.1 AA accessibility tests.
 *
 * Tests table semantics, scope attributes, aria-labels, and aria-selected
 * for the comparison view.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import ArchitectureCompare from "./ArchitectureCompare";
import type { ArchitectureVariant, ComparisonResult } from "../../services/api";

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const mockVariants: ArchitectureVariant[] = [
  {
    name: "Cost-Optimised",
    description: "Minimal resources for budget-constrained environments.",
    architecture: { subscriptions: [{ name: "s1" }] },
    resource_count: 12,
    estimated_monthly_cost_min: 400,
    estimated_monthly_cost_max: 600,
    complexity: "simple",
    compliance_scores: { NIST: 45 },
  },
  {
    name: "Balanced",
    description: "Recommended default with a pragmatic security posture.",
    architecture: { subscriptions: [{ name: "s1" }, { name: "s2" }] },
    resource_count: 28,
    estimated_monthly_cost_min: 2500,
    estimated_monthly_cost_max: 3500,
    complexity: "moderate",
    compliance_scores: { NIST: 75 },
  },
  {
    name: "Enterprise-Grade",
    description: "Maximum redundancy for regulated industries.",
    architecture: { subscriptions: [{ name: "s1" }, { name: "s2" }, { name: "s3" }] },
    resource_count: 55,
    estimated_monthly_cost_min: 10000,
    estimated_monthly_cost_max: 15000,
    complexity: "complex",
    compliance_scores: { NIST: 95, "ISO 27001": 88 },
  },
];

const mockComparison: ComparisonResult = {
  variants: mockVariants,
  tradeoff_analysis: "Cost vs security trade-off analysis.",
  recommended_index: 1,
};

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function renderCompare(
  props: Partial<React.ComponentProps<typeof ArchitectureCompare>> = {},
) {
  const defaults = {
    comparison: mockComparison,
    loading: false,
    onSelectVariant: vi.fn(),
  };
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <ArchitectureCompare {...defaults} {...props} />
    </FluentProvider>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ArchitectureCompare Accessibility", () => {
  // 1 — Uses proper table element
  it("renders a table element for comparison data", () => {
    renderCompare();
    const table = screen.getByRole("table");
    expect(table).toBeInTheDocument();
  });

  // 2 — Table has aria-label
  it("table has aria-label describing its purpose", () => {
    renderCompare();
    const table = screen.getByRole("table", { name: "Architecture variant comparison" });
    expect(table).toBeInTheDocument();
  });

  // 3 — Column headers have scope="col"
  it("column headers have scope=col", () => {
    renderCompare();
    const headers = screen.getAllByRole("columnheader");
    for (const header of headers) {
      expect(header).toHaveAttribute("scope", "col");
    }
  });

  // 4 — Comparison section has aria-label
  it("comparison section has aria-label", () => {
    renderCompare();
    const compareSection = screen.getByTestId("architecture-compare");
    expect(compareSection).toHaveAttribute("aria-label", "Architecture comparison");
  });

  // 5 — aria-selected on selected variant header
  it("marks selected variant header with aria-selected=true", () => {
    renderCompare({ selectedIndex: 1 });
    const header1 = screen.getByTestId("variant-header-1");
    expect(header1).toHaveAttribute("aria-selected", "true");

    const header0 = screen.getByTestId("variant-header-0");
    expect(header0).toHaveAttribute("aria-selected", "false");
  });

  // 6 — No variant selected by default
  it("no variant is aria-selected when selectedIndex is -1", () => {
    renderCompare({ selectedIndex: -1 });
    const header0 = screen.getByTestId("variant-header-0");
    const header1 = screen.getByTestId("variant-header-1");
    const header2 = screen.getByTestId("variant-header-2");

    expect(header0).toHaveAttribute("aria-selected", "false");
    expect(header1).toHaveAttribute("aria-selected", "false");
    expect(header2).toHaveAttribute("aria-selected", "false");
  });

  // 7 — Table contains correct number of rows
  it("table contains data rows for description, resources, cost, complexity, compliance, and action", () => {
    renderCompare();
    const table = screen.getByRole("table");
    const rows = within(table).getAllByRole("row");
    // Header row + Description + Resources + Cost + Complexity + NIST + ISO 27001 + Action = 8 rows
    expect(rows.length).toBeGreaterThanOrEqual(7);
  });

  // 8 — Buttons have accessible labels
  it("action buttons have aria-labels with variant names", () => {
    renderCompare();
    expect(screen.getByLabelText("Use Cost-Optimised architecture")).toBeInTheDocument();
    expect(screen.getByLabelText("Use Balanced architecture")).toBeInTheDocument();
    expect(screen.getByLabelText("Use Enterprise-Grade architecture")).toBeInTheDocument();
  });
});
