import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import SuggestedPrompts from "./SuggestedPrompts";

function renderWithTheme(ui: React.ReactElement) {
  return render(<FluentProvider theme={teamsLightTheme}>{ui}</FluentProvider>);
}

describe("SuggestedPrompts", () => {
  it("renders the prompt container", () => {
    renderWithTheme(<SuggestedPrompts onSelect={vi.fn()} />);
    expect(screen.getByTestId("suggested-prompts")).toBeInTheDocument();
  });

  it("displays the title", () => {
    renderWithTheme(<SuggestedPrompts onSelect={vi.fn()} />);
    expect(screen.getByText("What would you like to explore?")).toBeInTheDocument();
  });

  it("renders all six suggested prompt cards", () => {
    renderWithTheme(<SuggestedPrompts onSelect={vi.fn()} />);
    expect(screen.getByText("Add disaster recovery")).toBeInTheDocument();
    expect(screen.getByText("Optimize for cost")).toBeInTheDocument();
    expect(screen.getByText("Add HIPAA compliance")).toBeInTheDocument();
    expect(screen.getByText("Compare hub-spoke vs mesh")).toBeInTheDocument();
    expect(screen.getByText("Right-size my VMs")).toBeInTheDocument();
    expect(screen.getByText("Add security controls")).toBeInTheDocument();
  });

  it("calls onSelect when a prompt card is clicked", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    renderWithTheme(<SuggestedPrompts onSelect={onSelect} />);

    await user.click(screen.getByLabelText("Add disaster recovery"));
    expect(onSelect).toHaveBeenCalledWith("Add disaster recovery");
  });

  it("displays descriptions for each prompt", () => {
    renderWithTheme(<SuggestedPrompts onSelect={vi.fn()} />);
    expect(screen.getByText(/DR strategy/)).toBeInTheDocument();
    expect(screen.getByText(/cost savings/)).toBeInTheDocument();
  });

  it("renders prompt cards with aria labels", () => {
    renderWithTheme(<SuggestedPrompts onSelect={vi.fn()} />);
    expect(screen.getByLabelText("Optimize for cost")).toBeInTheDocument();
    expect(screen.getByLabelText("Add HIPAA compliance")).toBeInTheDocument();
  });

  it("calls onSelect with correct prompt for each card", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    renderWithTheme(<SuggestedPrompts onSelect={onSelect} />);

    await user.click(screen.getByLabelText("Optimize for cost"));
    expect(onSelect).toHaveBeenCalledWith("Optimize for cost");

    await user.click(screen.getByLabelText("Add security controls"));
    expect(onSelect).toHaveBeenCalledWith("Add security controls");
  });
});
