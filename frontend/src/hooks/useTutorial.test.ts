import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useTutorial } from "./useTutorial";

const STORAGE_KEY = "onramp-tutorial-completed";

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

describe("useTutorial", () => {
  beforeEach(() => {
    vi.stubGlobal("localStorage", createStorageMock());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("auto-starts when tutorial has not been completed", () => {
    const { result } = renderHook(() => useTutorial());
    expect(result.current.isActive).toBe(true);
    expect(result.current.isTutorialCompleted).toBe(false);
    expect(result.current.currentStepIndex).toBe(0);
  });

  it("does not auto-start when tutorial has been completed", () => {
    window.localStorage.setItem(STORAGE_KEY, "true");
    const { result } = renderHook(() => useTutorial());
    expect(result.current.isActive).toBe(false);
    expect(result.current.isTutorialCompleted).toBe(true);
  });

  it("navigates to the next step", () => {
    const { result } = renderHook(() => useTutorial());
    expect(result.current.currentStepIndex).toBe(0);

    act(() => {
      result.current.nextStep();
    });

    expect(result.current.currentStepIndex).toBe(1);
    expect(result.current.isActive).toBe(true);
  });

  it("navigates to the previous step", () => {
    const { result } = renderHook(() => useTutorial());

    act(() => {
      result.current.nextStep();
      result.current.nextStep();
    });
    expect(result.current.currentStepIndex).toBe(2);

    act(() => {
      result.current.prevStep();
    });
    expect(result.current.currentStepIndex).toBe(1);
  });

  it("does not go below step 0 on prevStep", () => {
    const { result } = renderHook(() => useTutorial());
    expect(result.current.currentStepIndex).toBe(0);

    act(() => {
      result.current.prevStep();
    });
    expect(result.current.currentStepIndex).toBe(0);
  });

  it("marks tutorial as completed when skipped", () => {
    const { result } = renderHook(() => useTutorial());
    expect(result.current.isActive).toBe(true);

    act(() => {
      result.current.skipTutorial();
    });

    expect(result.current.isActive).toBe(false);
    expect(result.current.isTutorialCompleted).toBe(true);
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe("true");
  });

  it("completes tutorial when advancing past last step", () => {
    const { result } = renderHook(() => useTutorial());
    const totalSteps = result.current.totalSteps;

    // Navigate to the last step
    for (let i = 0; i < totalSteps - 1; i++) {
      act(() => {
        result.current.nextStep();
      });
    }
    expect(result.current.currentStepIndex).toBe(totalSteps - 1);
    expect(result.current.isActive).toBe(true);

    // Advance past the last step
    act(() => {
      result.current.nextStep();
    });

    expect(result.current.isActive).toBe(false);
    expect(result.current.isTutorialCompleted).toBe(true);
  });

  it("restarts tutorial after completion", () => {
    const { result } = renderHook(() => useTutorial());

    act(() => {
      result.current.skipTutorial();
    });
    expect(result.current.isActive).toBe(false);
    expect(result.current.isTutorialCompleted).toBe(true);

    act(() => {
      result.current.startTutorial();
    });
    expect(result.current.isActive).toBe(true);
    expect(result.current.currentStepIndex).toBe(0);
  });

  it("provides the current step data when active", () => {
    const { result } = renderHook(() => useTutorial());
    expect(result.current.currentStep).not.toBeNull();
    expect(result.current.currentStep?.id).toBe("welcome");
    expect(result.current.currentStep?.title).toBe("Welcome to OnRamp!");
  });

  it("returns null currentStep when inactive", () => {
    const { result } = renderHook(() => useTutorial());

    act(() => {
      result.current.skipTutorial();
    });

    expect(result.current.currentStep).toBeNull();
  });

  it("exposes the total number of steps", () => {
    const { result } = renderHook(() => useTutorial());
    expect(result.current.totalSteps).toBe(7);
  });

  it("persists completion state in localStorage", () => {
    const { result } = renderHook(() => useTutorial());

    act(() => {
      result.current.skipTutorial();
    });

    // Re-render a new hook to simulate page reload
    const { result: result2 } = renderHook(() => useTutorial());
    expect(result2.current.isTutorialCompleted).toBe(true);
    expect(result2.current.isActive).toBe(false);
  });
});
