import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import HomePage from "./HomePage";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

function renderHomePage() {
  return render(
    <MemoryRouter>
      <FluentProvider theme={teamsLightTheme}>
        <HomePage />
      </FluentProvider>
    </MemoryRouter>
  );
}

describe("HomePage", () => {
  it("renders title and subtitle", () => {
    renderHomePage();
    expect(screen.getByText("OnRamp")).toBeInTheDocument();
    expect(screen.getByText(/Azure Landing Zone/)).toBeInTheDocument();
  });

  it("renders start button", () => {
    renderHomePage();
    expect(screen.getByRole("button", { name: /start building/i })).toBeInTheDocument();
  });

  it("navigates to wizard on button click", async () => {
    const user = userEvent.setup();
    renderHomePage();
    await user.click(screen.getByRole("button", { name: /start building/i }));
    expect(mockNavigate).toHaveBeenCalledWith("/wizard");
  });
});
