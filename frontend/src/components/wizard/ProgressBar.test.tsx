import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import WizardProgressBar from "./ProgressBar";

function renderProgressBar(progress: { answered: number; total: number; percent_complete: number }) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <WizardProgressBar progress={{ ...progress, remaining: progress.total - progress.answered }} />
    </FluentProvider>
  );
}

describe("WizardProgressBar", () => {
  it("displays question count", () => {
    renderProgressBar({ answered: 5, total: 24, percent_complete: 21 });
    expect(screen.getByText(/Question 6 of 24/)).toBeInTheDocument();
  });

  it("displays percentage", () => {
    renderProgressBar({ answered: 12, total: 24, percent_complete: 50 });
    expect(screen.getByText(/50% complete/)).toBeInTheDocument();
  });

  it("renders progress bar element", () => {
    const { container } = renderProgressBar({ answered: 0, total: 24, percent_complete: 0 });
    expect(container.querySelector("[role='progressbar']")).toBeInTheDocument();
  });
});
