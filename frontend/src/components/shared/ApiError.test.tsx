import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import ApiError from "./ApiError";

function renderWithTheme(ui: React.ReactElement) {
  return render(<FluentProvider theme={teamsLightTheme}>{ui}</FluentProvider>);
}

describe("ApiError", () => {
  it("displays error message", () => {
    renderWithTheme(<ApiError message="Something failed" />);
    expect(screen.getByText("Something failed")).toBeInTheDocument();
  });

  it("shows retry button when onRetry provided", () => {
    renderWithTheme(<ApiError message="Error" onRetry={vi.fn()} />);
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("hides retry button when no onRetry", () => {
    renderWithTheme(<ApiError message="Error" />);
    expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();
  });

  it("calls onRetry when clicked", async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    renderWithTheme(<ApiError message="Error" onRetry={onRetry} />);
    await user.click(screen.getByRole("button", { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
