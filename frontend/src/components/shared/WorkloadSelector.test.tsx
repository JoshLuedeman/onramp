import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FluentProvider, webLightTheme } from "@fluentui/react-components";
import WorkloadSelector, {
  DEFAULT_WORKLOADS,
} from "./WorkloadSelector";

function renderWithProvider(ui: React.ReactElement) {
  return render(
    <FluentProvider theme={webLightTheme}>{ui}</FluentProvider>
  );
}

describe("WorkloadSelector", () => {
  it("renders all default workload cards", () => {
    const onSelect = vi.fn();
    renderWithProvider(
      <WorkloadSelector selected={null} onSelect={onSelect} />
    );
    for (const wl of DEFAULT_WORKLOADS) {
      expect(screen.getByText(wl.display_name)).toBeTruthy();
    }
  });

  it("calls onSelect when a card is clicked", () => {
    const onSelect = vi.fn();
    renderWithProvider(
      <WorkloadSelector selected={null} onSelect={onSelect} />
    );
    fireEvent.click(screen.getByLabelText("AI / Machine Learning"));
    expect(onSelect).toHaveBeenCalledWith("ai_ml");
  });

  it("marks selected card with aria-checked", () => {
    const onSelect = vi.fn();
    renderWithProvider(
      <WorkloadSelector selected="sap" onSelect={onSelect} />
    );
    const card = screen.getByLabelText("SAP");
    expect(card.getAttribute("aria-checked")).toBe("true");
  });

  it("does not fire onSelect when disabled", () => {
    const onSelect = vi.fn();
    renderWithProvider(
      <WorkloadSelector selected={null} onSelect={onSelect} disabled />
    );
    fireEvent.click(screen.getByLabelText("IoT / Edge"));
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("renders custom workloads when provided", () => {
    const onSelect = vi.fn();
    const customWorkloads = [
      {
        workload_type: "custom",
        display_name: "Custom Workload",
        description: "A custom workload",
        icon: <span>🔧</span>,
        tag_count: 5,
      },
    ];
    renderWithProvider(
      <WorkloadSelector
        selected={null}
        onSelect={onSelect}
        workloads={customWorkloads}
      />
    );
    expect(screen.getByText("Custom Workload")).toBeTruthy();
  });

  it("renders badge with tag count", () => {
    const onSelect = vi.fn();
    renderWithProvider(
      <WorkloadSelector selected={null} onSelect={onSelect} />
    );
    // Default workloads have tag counts like "4 questions", "3 questions"
    expect(screen.getByText("4 questions")).toBeTruthy();
  });

  it("uses radiogroup role for accessibility", () => {
    const onSelect = vi.fn();
    renderWithProvider(
      <WorkloadSelector selected={null} onSelect={onSelect} />
    );
    expect(screen.getByRole("radiogroup")).toBeTruthy();
  });
});
