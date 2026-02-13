import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";

// Mock MSAL
vi.mock("./auth/AuthProvider", () => ({
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Replace BrowserRouter with MemoryRouter to avoid nested router error
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    BrowserRouter: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

// Mock lazy-loaded pages so we don't need full Suspense resolution
vi.mock("./pages/HomePage", () => ({
  default: () => <div data-testid="home-page">Home Page</div>,
}));

vi.mock("./pages/WizardPage", () => ({
  default: () => <div data-testid="wizard-page">Wizard Page</div>,
}));

vi.mock("./pages/ArchitecturePage", () => ({
  default: () => <div data-testid="architecture-page">Architecture Page</div>,
}));

vi.mock("./pages/CompliancePage", () => ({
  default: () => <div data-testid="compliance-page">Compliance Page</div>,
}));

vi.mock("./pages/BicepPage", () => ({
  default: () => <div data-testid="bicep-page">Bicep Page</div>,
}));

vi.mock("./pages/DeployPage", () => ({
  default: () => <div data-testid="deploy-page">Deploy Page</div>,
}));

// We need to import App after mocks
import App from "./App";

describe("App", () => {
  it("renders without crashing", () => {
    const { container } = render(
      <FluentProvider theme={teamsLightTheme}>
        <MemoryRouter initialEntries={["/"]}>
          <App />
        </MemoryRouter>
      </FluentProvider>
    );
    expect(container).toBeTruthy();
  });

  it("renders home page at root route", async () => {
    render(
      <FluentProvider theme={teamsLightTheme}>
        <MemoryRouter initialEntries={["/"]}>
          <App />
        </MemoryRouter>
      </FluentProvider>
    );
    // Wait for lazy load
    expect(await screen.findByTestId("home-page")).toBeInTheDocument();
  });
});
