import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import QuestionCard from "./QuestionCard";
import type { Question } from "../../services/api";

function renderWithTheme(ui: React.ReactElement) {
  return render(<FluentProvider theme={teamsLightTheme}>{ui}</FluentProvider>);
}

const singleChoiceQuestion: Question = {
  id: "q1",
  category: "org",
  caf_area: "resource_organization",
  text: "How large is your organization?",
  type: "single_choice",
  options: [
    { value: "small", label: "Small (1-100)", recommended: true },
    { value: "medium", label: "Medium (100-1000)" },
    { value: "_unsure", label: "I'm not sure" },
  ],
  required: true,
  order: 1,
};

const textQuestion: Question = {
  id: "q2",
  category: "org",
  caf_area: "billing_tenant",
  text: "What is your company name?",
  type: "text",
  required: true,
  order: 2,
};

describe("QuestionCard", () => {
  it("renders question text", () => {
    renderWithTheme(<QuestionCard question={singleChoiceQuestion} onAnswer={vi.fn()} />);
    expect(screen.getByText("How large is your organization?")).toBeInTheDocument();
  });

  it("renders CAF area badge", () => {
    renderWithTheme(<QuestionCard question={singleChoiceQuestion} onAnswer={vi.fn()} />);
    expect(screen.getByText("Resource Organization")).toBeInTheDocument();
  });

  it("marks recommended option", () => {
    renderWithTheme(<QuestionCard question={singleChoiceQuestion} onAnswer={vi.fn()} />);
    expect(screen.getByText(/Small.*Recommended/)).toBeInTheDocument();
  });

  it("renders unsure option separately", () => {
    renderWithTheme(<QuestionCard question={singleChoiceQuestion} onAnswer={vi.fn()} />);
    expect(screen.getByText("I'm not sure")).toBeInTheDocument();
  });

  it("renders text input for text questions", () => {
    renderWithTheme(<QuestionCard question={textQuestion} onAnswer={vi.fn()} />);
    expect(screen.getByPlaceholderText("Type your answer...")).toBeInTheDocument();
  });

  it("next button is disabled when no selection", () => {
    renderWithTheme(<QuestionCard question={singleChoiceQuestion} onAnswer={vi.fn()} />);
    expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
  });

  it("calls onAnswer with selected value", async () => {
    const onAnswer = vi.fn();
    const user = userEvent.setup();
    renderWithTheme(<QuestionCard question={singleChoiceQuestion} onAnswer={onAnswer} />);
    await user.click(screen.getByText(/Small.*Recommended/));
    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(onAnswer).toHaveBeenCalledWith("q1", "small");
  });

  it("renders multi_choice checkboxes", () => {
    const multiQuestion: Question = {
      id: "q3",
      category: "compliance",
      caf_area: "governance",
      text: "Which frameworks?",
      type: "multi_choice",
      options: [
        { value: "soc2", label: "SOC 2", recommended: true },
        { value: "hipaa", label: "HIPAA" },
        { value: "_unsure", label: "I'm not sure" },
      ],
      required: true,
      order: 3,
    };
    renderWithTheme(<QuestionCard question={multiQuestion} onAnswer={vi.fn()} />);
    expect(screen.getByText(/SOC 2.*Recommended/)).toBeInTheDocument();
    expect(screen.getByText("HIPAA")).toBeInTheDocument();
  });

  it("submits multi_choice values", async () => {
    const onAnswer = vi.fn();
    const user = userEvent.setup();
    const multiQuestion: Question = {
      id: "q3",
      category: "compliance",
      caf_area: "governance",
      text: "Which frameworks?",
      type: "multi_choice",
      options: [
        { value: "soc2", label: "SOC 2" },
        { value: "hipaa", label: "HIPAA" },
      ],
      required: true,
      order: 3,
    };
    renderWithTheme(<QuestionCard question={multiQuestion} onAnswer={onAnswer} />);
    await user.click(screen.getByText("SOC 2"));
    await user.click(screen.getByText("HIPAA"));
    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(onAnswer).toHaveBeenCalledWith("q3", ["soc2", "hipaa"]);
  });

  it("submits text value", async () => {
    const onAnswer = vi.fn();
    const user = userEvent.setup();
    renderWithTheme(<QuestionCard question={textQuestion} onAnswer={onAnswer} />);
    await user.type(screen.getByPlaceholderText("Type your answer..."), "Contoso");
    await user.click(screen.getByRole("button", { name: /next/i }));
    expect(onAnswer).toHaveBeenCalledWith("q2", "Contoso");
  });

  it("shows Auto-discovered banner when discoveredAnswer is present", () => {
    renderWithTheme(
      <QuestionCard
        question={singleChoiceQuestion}
        onAnswer={vi.fn()}
        discoveredAnswer={{
          value: "small",
          confidence: "high",
          evidence: "Found 50 users",
          source: "discovered",
        }}
      />
    );
    expect(screen.getByText(/Auto-discovered/)).toBeInTheDocument();
    expect(screen.getByText(/Found 50 users/)).toBeInTheDocument();
  });

  it("hides Auto-discovered banner when existingAnswer is provided", () => {
    renderWithTheme(
      <QuestionCard
        question={singleChoiceQuestion}
        onAnswer={vi.fn()}
        existingAnswer="medium"
        discoveredAnswer={{
          value: "small",
          confidence: "high",
          evidence: "Found 50 users",
          source: "discovered",
        }}
      />
    );
    expect(screen.queryByText(/Auto-discovered/)).not.toBeInTheDocument();
  });
});
