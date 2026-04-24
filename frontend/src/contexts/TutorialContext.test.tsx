import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { TutorialProvider, useTutorialContext } from "./TutorialContext";
import { TUTORIAL_STORAGE_KEY } from "../hooks/useTutorial";

function createStorageMock(): Storage {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
    get length() {
      return Object.keys(store).length;
    },
    key: (index: number) => Object.keys(store)[index] ?? null,
  };
}

function TestConsumer() {
  const {
    isActive,
    currentStep,
    currentStepIndex,
    totalSteps,
    startTutorial,
  } = useTutorialContext();
  return (
    <div>
      <span data-testid="is-active">{String(isActive)}</span>
      <span data-testid="step-index">{currentStepIndex}</span>
      <span data-testid="total-steps">{totalSteps}</span>
      <span data-testid="step-title">{currentStep?.title ?? "none"}</span>
      <button onClick={startTutorial}>Start</button>
    </div>
  );
}

describe("TutorialContext", () => {
  let storageMock: Storage;

  beforeEach(() => {
    storageMock = createStorageMock();
    // Mark tutorial as completed so it doesn't auto-start
    storageMock.setItem(TUTORIAL_STORAGE_KEY, "true");
    vi.stubGlobal("localStorage", storageMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("throws when used outside provider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() =>
      render(
        <FluentProvider theme={teamsLightTheme}>
          <TestConsumer />
        </FluentProvider>,
      ),
    ).toThrow("useTutorialContext must be used within a TutorialProvider");
    spy.mockRestore();
  });

  it("provides tutorial values within provider", () => {
    render(
      <FluentProvider theme={teamsLightTheme}>
        <TutorialProvider currentPath="/wizard">
          <TestConsumer />
        </TutorialProvider>
      </FluentProvider>,
    );

    // Tutorial is completed, so not active
    expect(screen.getByTestId("is-active")).toHaveTextContent("false");
    expect(screen.getByTestId("total-steps")).toHaveTextContent("7");
    expect(screen.getByTestId("step-index")).toHaveTextContent("0");
  });

  it("children can access tutorial context and start tutorial", async () => {
    const user = userEvent.setup();
    render(
      <FluentProvider theme={teamsLightTheme}>
        <TutorialProvider currentPath="/">
          <TestConsumer />
        </TutorialProvider>
      </FluentProvider>,
    );

    // Initially not active (completed)
    expect(screen.getByTestId("is-active")).toHaveTextContent("false");

    // Start the tutorial via context
    await user.click(screen.getByRole("button", { name: "Start" }));

    // Now active with first step
    expect(screen.getByTestId("is-active")).toHaveTextContent("true");
    expect(screen.getByTestId("step-title")).toHaveTextContent(
      "Welcome to OnRamp!",
    );
  });
});
