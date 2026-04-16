import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
    compliance_scores: {},
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
  tradeoff_analysis:
    "The Cost-Optimised variant minimises spend. The Balanced variant is recommended. The Enterprise-Grade variant maximises isolation.",
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
  return {
    onSelectVariant: defaults.onSelectVariant,
    ...render(
      <FluentProvider theme={teamsLightTheme}>
        <ArchitectureCompare {...defaults} {...props} />
      </FluentProvider>,
    ),
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ArchitectureCompare", () => {
  it("renders three variant cards", () => {
    renderCompare();
    expect(screen.getByTestId("variant-card-0")).toBeInTheDocument();
    expect(screen.getByTestId("variant-card-1")).toBeInTheDocument();
    expect(screen.getByTestId("variant-card-2")).toBeInTheDocument();
  });

  it("displays variant names", () => {
    renderCompare();
    expect(screen.getByText("Cost-Optimised")).toBeInTheDocument();
    expect(screen.getByText("Balanced")).toBeInTheDocument();
    expect(screen.getByText("Enterprise-Grade")).toBeInTheDocument();
  });

  it("displays variant descriptions", () => {
    renderCompare();
    expect(
      screen.getByText("Minimal resources for budget-constrained environments."),
    ).toBeInTheDocument();
  });

  it("shows resource counts", () => {
    renderCompare();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("28")).toBeInTheDocument();
    expect(screen.getByText("55")).toBeInTheDocument();
  });

  it("shows estimated cost ranges", () => {
    renderCompare();
    expect(screen.getByText(/\$400/)).toBeInTheDocument();
    expect(screen.getByText(/\$10,000/)).toBeInTheDocument();
  });

  it("shows complexity badges", () => {
    renderCompare();
    expect(screen.getByText("simple")).toBeInTheDocument();
    expect(screen.getByText("moderate")).toBeInTheDocument();
    expect(screen.getByText("complex")).toBeInTheDocument();
  });

  it("shows Recommended badge on the balanced variant", () => {
    renderCompare();
    const badge = screen.getByTestId("recommended-badge");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent("Recommended");
  });

  it("displays compliance scores when present", () => {
    renderCompare();
    expect(screen.getByText("75%")).toBeInTheDocument();
    expect(screen.getByText("95%")).toBeInTheDocument();
    expect(screen.getByText("88%")).toBeInTheDocument();
  });

  it("calls onSelectVariant when button is clicked", async () => {
    const user = userEvent.setup();
    const { onSelectVariant } = renderCompare();

    await user.click(screen.getByTestId("select-variant-0"));
    expect(onSelectVariant).toHaveBeenCalledWith(mockVariants[0], 0);

    await user.click(screen.getByTestId("select-variant-2"));
    expect(onSelectVariant).toHaveBeenCalledWith(mockVariants[2], 2);
  });

  it("renders three 'Use this architecture' buttons", () => {
    renderCompare();
    const buttons = screen.getAllByText("Use this architecture");
    expect(buttons).toHaveLength(3);
  });

  it("shows trade-off analysis text", () => {
    renderCompare();
    expect(screen.getByTestId("tradeoff-analysis")).toBeInTheDocument();
    expect(screen.getByText(/Cost-Optimised variant minimises spend/)).toBeInTheDocument();
  });

  it("shows loading spinner when loading is true", () => {
    renderCompare({ loading: true, comparison: null });
    expect(screen.getByTestId("compare-loading")).toBeInTheDocument();
    expect(screen.getByText("Generating architecture variants…")).toBeInTheDocument();
  });

  it("renders nothing when comparison is null and not loading", () => {
    const { container } = renderCompare({ comparison: null });
    expect(container.querySelector("[data-testid='architecture-compare']")).not.toBeInTheDocument();
  });

  it("renders nothing when variants array is empty", () => {
    const empty: ComparisonResult = { variants: [], tradeoff_analysis: "", recommended_index: 0 };
    const { container } = renderCompare({ comparison: empty });
    expect(container.querySelector("[data-testid='architecture-compare']")).not.toBeInTheDocument();
  });
});
