import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import ProtectedRoute from "./ProtectedRoute";

// Mock useAuth — default to dev mode (authenticated)
const mockUseAuth = vi.fn();
vi.mock("../../auth", () => ({
  useAuth: () => mockUseAuth(),
}));

function renderWithProviders(ui: React.ReactElement, { route = "/" } = {}) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </FluentProvider>,
  );
}

describe("ProtectedRoute", () => {
  it("renders children when authenticated", () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true });

    renderWithProviders(
      <ProtectedRoute>
        <div data-testid="protected-content">Secret Content</div>
      </ProtectedRoute>,
    );

    expect(screen.getByTestId("protected-content")).toBeInTheDocument();
  });

  it("redirects to / when not authenticated", () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false });

    renderWithProviders(
      <ProtectedRoute>
        <div data-testid="protected-content">Secret Content</div>
      </ProtectedRoute>,
      { route: "/projects/123" },
    );

    expect(screen.queryByTestId("protected-content")).not.toBeInTheDocument();
  });
});
