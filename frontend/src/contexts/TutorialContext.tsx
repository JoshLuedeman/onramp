import { createContext, useContext, type ReactNode } from "react";
import { useTutorial, type UseTutorialReturn } from "../hooks/useTutorial";

const TutorialContext = createContext<UseTutorialReturn | null>(null);

export function TutorialProvider({
  children,
  currentPath,
}: {
  children: ReactNode;
  currentPath?: string;
}) {
  const tutorial = useTutorial(currentPath);

  return (
    <TutorialContext.Provider value={tutorial}>
      {children}
    </TutorialContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useTutorialContext(): UseTutorialReturn {
  const context = useContext(TutorialContext);
  if (!context) {
    throw new Error(
      "useTutorialContext must be used within a TutorialProvider",
    );
  }
  return context;
}
