import { useState, useCallback } from "react";

const TUTORIAL_STORAGE_KEY = "onramp-tutorial-completed";

export interface TutorialStep {
  id: string;
  title: string;
  content: string;
  targetSelector: string;
  page: string;
}

export interface UseTutorialReturn {
  isActive: boolean;
  currentStep: TutorialStep | null;
  currentStepIndex: number;
  totalSteps: number;
  startTutorial: () => void;
  nextStep: () => void;
  prevStep: () => void;
  skipTutorial: () => void;
  isTutorialCompleted: boolean;
}

const TUTORIAL_STEPS: TutorialStep[] = [
  {
    id: "welcome",
    title: "Welcome to OnRamp!",
    content:
      "Start by creating a project for your Azure landing zone.",
    targetSelector: "[data-tutorial='home']",
    page: "/",
  },
  {
    id: "projects",
    title: "Projects",
    content:
      "Each project guides you through designing and deploying a landing zone.",
    targetSelector: "[data-tutorial='projects']",
    page: "/",
  },
  {
    id: "wizard",
    title: "Wizard",
    content:
      "Answer questions about your organization. Recommended options are highlighted.",
    targetSelector: "[data-tutorial='wizard']",
    page: "/wizard",
  },
  {
    id: "architecture",
    title: "Architecture",
    content: "Review your AI-generated landing zone architecture.",
    targetSelector: "[data-tutorial='architecture']",
    page: "/architecture",
  },
  {
    id: "compliance",
    title: "Compliance",
    content:
      "See how your architecture scores against compliance frameworks.",
    targetSelector: "[data-tutorial='compliance']",
    page: "/compliance",
  },
  {
    id: "bicep",
    title: "Bicep",
    content:
      "Download Infrastructure-as-Code templates for your landing zone.",
    targetSelector: "[data-tutorial='bicep']",
    page: "/bicep",
  },
  {
    id: "deploy",
    title: "Deploy",
    content: "Deploy your landing zone directly to Azure subscriptions.",
    targetSelector: "[data-tutorial='deploy']",
    page: "/deploy",
  },
];

function getIsCompleted(): boolean {
  try {
    return typeof localStorage !== "undefined" &&
      typeof localStorage.getItem === "function" &&
      localStorage.getItem(TUTORIAL_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

function setCompleted(value: boolean): void {
  try {
    if (typeof localStorage === "undefined" || typeof localStorage.setItem !== "function") {
      return;
    }
    if (value) {
      localStorage.setItem(TUTORIAL_STORAGE_KEY, "true");
    } else {
      localStorage.removeItem(TUTORIAL_STORAGE_KEY);
    }
  } catch {
    // localStorage may be unavailable; silently ignore
  }
}

export function useTutorial(): UseTutorialReturn {
  const [isTutorialCompleted, setIsTutorialCompleted] = useState(getIsCompleted);
  const [isActive, setIsActive] = useState(() => !getIsCompleted());
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  const startTutorial = useCallback(() => {
    setCurrentStepIndex(0);
    setIsActive(true);
  }, []);

  const skipTutorial = useCallback(() => {
    setIsActive(false);
    setIsTutorialCompleted(true);
    setCompleted(true);
  }, []);

  const nextStep = useCallback(() => {
    setCurrentStepIndex((prev) => {
      const next = prev + 1;
      if (next >= TUTORIAL_STEPS.length) {
        // Tutorial finished — mark completed
        setIsActive(false);
        setIsTutorialCompleted(true);
        setCompleted(true);
        return prev;
      }
      return next;
    });
  }, []);

  const prevStep = useCallback(() => {
    setCurrentStepIndex((prev) => Math.max(0, prev - 1));
  }, []);

  const currentStep = isActive ? TUTORIAL_STEPS[currentStepIndex] ?? null : null;

  return {
    isActive,
    currentStep,
    currentStepIndex,
    totalSteps: TUTORIAL_STEPS.length,
    startTutorial,
    nextStep,
    prevStep,
    skipTutorial,
    isTutorialCompleted,
  };
}
