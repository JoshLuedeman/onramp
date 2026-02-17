import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import ErrorBoundary from "./ErrorBoundary";

function ThrowError({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error("Test error");
  return <div>Content</div>;
}

function renderWithTheme(ui: React.ReactElement) {
  return render(<FluentProvider theme={teamsLightTheme}>{ui}</FluentProvider>);
}

describe("ErrorBoundary", () => {
  it("renders children when no error", () => {
    renderWithTheme(
      <ErrorBoundary><ThrowError shouldThrow={false} /></ErrorBoundary>
    );
    expect(screen.getByText("Content")).toBeInTheDocument();
  });

  it("shows error message when child throws", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    renderWithTheme(
      <ErrorBoundary><ThrowError shouldThrow={true} /></ErrorBoundary>
    );
    expect(screen.getByText(/Test error/)).toBeInTheDocument();
    spy.mockRestore();
  });

  it("shows try again button", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    renderWithTheme(
      <ErrorBoundary><ThrowError shouldThrow={true} /></ErrorBoundary>
    );
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
    spy.mockRestore();
  });
});
