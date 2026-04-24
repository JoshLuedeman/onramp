import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import NotFoundPage from "./NotFoundPage";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function renderWithProviders() {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>
        <NotFoundPage />
      </MemoryRouter>
    </FluentProvider>,
  );
}

describe("NotFoundPage", () => {
  it("renders 404 text", () => {
    renderWithProviders();
    expect(screen.getByText("404")).toBeInTheDocument();
  });

  it("renders Page Not Found heading", () => {
    renderWithProviders();
    expect(screen.getByText("Page Not Found")).toBeInTheDocument();
  });

  it("has a button that navigates to dashboard", async () => {
    const user = userEvent.setup();
    renderWithProviders();

    const button = screen.getByRole("button", { name: /back to dashboard/i });
    await user.click(button);

    expect(mockNavigate).toHaveBeenCalledWith("/");
  });
});
