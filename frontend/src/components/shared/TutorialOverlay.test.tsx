import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import TutorialOverlay from "./TutorialOverlay";
import type { TutorialOverlayProps } from "./TutorialOverlay";
import type { TutorialStep } from "../../hooks/useTutorial";

const sampleStep: TutorialStep = {
  id: "welcome",
  title: "Welcome to OnRamp!",
  content: "Start by creating a project for your Azure landing zone.",
  targetSelector: "[data-tutorial='home']",
  page: "/",
};

const defaultProps: TutorialOverlayProps = {
  isActive: true,
  currentStep: sampleStep,
  currentStepIndex: 0,
  totalSteps: 7,
  onNext: vi.fn(),
  onPrev: vi.fn(),
  onSkip: vi.fn(),
};

function renderOverlay(overrides: Partial<TutorialOverlayProps> = {}) {
  const props = { ...defaultProps, ...overrides };
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <TutorialOverlay {...props} />
    </FluentProvider>
  );
}

describe("TutorialOverlay", () => {
  it("renders when active with step content", () => {
    renderOverlay();
    expect(screen.getByText("Welcome to OnRamp!")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Start by creating a project for your Azure landing zone."
      )
    ).toBeInTheDocument();
  });

  it("does not render when inactive", () => {
    renderOverlay({ isActive: false });
    expect(screen.queryByTestId("tutorial-overlay")).not.toBeInTheDocument();
  });

  it("does not render when currentStep is null", () => {
    renderOverlay({ currentStep: null });
    expect(screen.queryByTestId("tutorial-overlay")).not.toBeInTheDocument();
  });

  it("calls onNext when Next button is clicked", async () => {
    const onNext = vi.fn();
    const user = userEvent.setup();
    renderOverlay({ onNext });

    await user.click(screen.getByRole("button", { name: /next step/i }));
    expect(onNext).toHaveBeenCalledOnce();
  });

  it("calls onSkip when Skip button is clicked", async () => {
    const onSkip = vi.fn();
    const user = userEvent.setup();
    renderOverlay({ onSkip });

    await user.click(screen.getByRole("button", { name: "Skip" }));
    expect(onSkip).toHaveBeenCalled();
  });

  it("disables Back button on first step", () => {
    renderOverlay({ currentStepIndex: 0 });
    const backButton = screen.getByRole("button", { name: /previous step/i });
    expect(backButton).toBeDisabled();
  });

  it("enables Back button on subsequent steps", () => {
    renderOverlay({ currentStepIndex: 2 });
    const backButton = screen.getByRole("button", { name: /previous step/i });
    expect(backButton).not.toBeDisabled();
  });

  it("calls onPrev when Back button is clicked", async () => {
    const onPrev = vi.fn();
    const user = userEvent.setup();
    renderOverlay({ onPrev, currentStepIndex: 2 });

    await user.click(screen.getByRole("button", { name: /previous step/i }));
    expect(onPrev).toHaveBeenCalledOnce();
  });

  it("shows correct progress indicator", () => {
    renderOverlay({ currentStepIndex: 2, totalSteps: 7 });
    expect(screen.getByText("Step 3 of 7")).toBeInTheDocument();
  });

  it("shows Finish button on last step", () => {
    renderOverlay({ currentStepIndex: 6, totalSteps: 7 });
    expect(
      screen.getByRole("button", { name: /finish tutorial/i })
    ).toBeInTheDocument();
  });

  it("has a dialog role for accessibility", () => {
    renderOverlay();
    expect(screen.getByRole("dialog", { name: /tutorial/i })).toBeInTheDocument();
  });
});
