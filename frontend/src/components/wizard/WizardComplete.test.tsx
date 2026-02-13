import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import WizardComplete from "./WizardComplete";

function renderWizardComplete(onGenerate: () => void, answeredCount: number) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <WizardComplete onGenerate={onGenerate} answeredCount={answeredCount} />
    </FluentProvider>
  );
}

describe("WizardComplete", () => {
  it("shows completion message with count", () => {
    renderWizardComplete(vi.fn(), 24);
    expect(screen.getByText(/Questionnaire Complete/)).toBeInTheDocument();
    expect(screen.getByText(/24 questions/)).toBeInTheDocument();
  });

  it("calls onGenerate when button clicked", async () => {
    const onGenerate = vi.fn();
    const user = userEvent.setup();
    renderWizardComplete(onGenerate, 20);
    await user.click(screen.getByRole("button", { name: /generate architecture/i }));
    expect(onGenerate).toHaveBeenCalledOnce();
  });
});
