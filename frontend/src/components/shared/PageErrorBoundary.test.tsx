import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import PageErrorBoundary from "./PageErrorBoundary";

function ThrowingComponent({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error("Test error");
  return <div>Content loaded</div>;
}

function renderWithTheme(ui: React.ReactElement) {
  return render(<FluentProvider theme={teamsLightTheme}>{ui}</FluentProvider>);
}

describe("PageErrorBoundary", () => {
  it("renders children when no error", () => {
    renderWithTheme(
      <PageErrorBoundary>
        <ThrowingComponent shouldThrow={false} />
      </PageErrorBoundary>,
    );
    expect(screen.getByText("Content loaded")).toBeInTheDocument();
  });

  it("shows error message when child throws", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    renderWithTheme(
      <PageErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </PageErrorBoundary>,
    );
    expect(screen.getByText(/Test error/)).toBeInTheDocument();
    expect(screen.getByTestId("page-error-boundary")).toBeInTheDocument();
    spy.mockRestore();
  });

  it("shows default title when pageName is not provided", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    renderWithTheme(
      <PageErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </PageErrorBoundary>,
    );
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    spy.mockRestore();
  });

  it("shows page name in error title when provided", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    renderWithTheme(
      <PageErrorBoundary pageName="Dashboard">
        <ThrowingComponent shouldThrow={true} />
      </PageErrorBoundary>,
    );
    expect(screen.getByText("Error in Dashboard")).toBeInTheDocument();
    spy.mockRestore();
  });

  it("retry button resets the error state", async () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    const user = userEvent.setup();

    // We need a component that can toggle its throwing behavior.
    // Since we can't change props after mount in a class-based error boundary reset,
    // we use a stateful wrapper to control whether the child throws.
    let shouldThrow = true;

    function ConditionalThrower() {
      if (shouldThrow) throw new Error("Test error");
      return <div>Content loaded</div>;
    }

    renderWithTheme(
      <PageErrorBoundary>
        <ConditionalThrower />
      </PageErrorBoundary>,
    );

    // Error state is shown
    expect(screen.getByText(/Test error/)).toBeInTheDocument();

    // Fix the error before retrying
    shouldThrow = false;

    await user.click(screen.getByRole("button", { name: /retry/i }));

    // After retry, children should render again
    expect(screen.getByText("Content loaded")).toBeInTheDocument();
    expect(screen.queryByTestId("page-error-boundary")).not.toBeInTheDocument();

    spy.mockRestore();
  });
});
