/**
 * QuestionCard WCAG 2.1 AA accessibility tests.
 *
 * Tests form input labels, recommended option indication,
 * question-group association, submit button accessibility,
 * and unsure option accessibility.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import QuestionCard from "./QuestionCard";
import type { Question } from "../../services/api";

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

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

const multiChoiceQuestion: Question = {
  id: "q3",
  category: "compliance",
  caf_area: "governance",
  text: "Which frameworks do you need?",
  type: "multi_choice",
  options: [
    { value: "soc2", label: "SOC 2", recommended: true },
    { value: "hipaa", label: "HIPAA" },
    { value: "_unsure", label: "I'm not sure" },
  ],
  required: true,
  order: 3,
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

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function renderWithTheme(ui: React.ReactElement) {
  return render(<FluentProvider theme={teamsLightTheme}>{ui}</FluentProvider>);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("QuestionCard Accessibility", () => {
  // 1 — RadioGroup renders with radio role inputs
  it("single_choice renders radio inputs with accessible labels", () => {
    renderWithTheme(
      <QuestionCard question={singleChoiceQuestion} onAnswer={vi.fn()} />,
    );
    const radios = screen.getAllByRole("radio");
    expect(radios.length).toBe(3); // 2 regular + 1 unsure

    // Each radio has an accessible label
    expect(screen.getByRole("radio", { name: /Small \(1-100\).*Recommended/ })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Medium (100-1000)" })).toBeInTheDocument();
  });

  // 2 — Recommended option has accessible "(Recommended)" text in label
  it("recommended option has 'Recommended' in its accessible label", () => {
    renderWithTheme(
      <QuestionCard question={singleChoiceQuestion} onAnswer={vi.fn()} />,
    );
    const recommendedRadio = screen.getByRole("radio", { name: /Recommended/ });
    expect(recommendedRadio).toBeInTheDocument();
    // The recommended text is part of the label, making it accessible to screen readers
    expect(screen.getByText(/Small \(1-100\).*\(Recommended\)/)).toBeInTheDocument();
  });

  // 3 — Multi-choice checkboxes have accessible labels
  it("multi_choice renders checkboxes with accessible labels", () => {
    renderWithTheme(
      <QuestionCard question={multiChoiceQuestion} onAnswer={vi.fn()} />,
    );
    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes.length).toBe(3); // 2 regular + 1 unsure

    expect(screen.getByRole("checkbox", { name: /SOC 2.*Recommended/ })).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "HIPAA" })).toBeInTheDocument();
  });

  // 4 — Multi-choice recommended option includes "(Recommended)" in label
  it("multi_choice recommended option has 'Recommended' in its accessible label", () => {
    renderWithTheme(
      <QuestionCard question={multiChoiceQuestion} onAnswer={vi.fn()} />,
    );
    const recommendedCheckbox = screen.getByRole("checkbox", { name: /Recommended/ });
    expect(recommendedCheckbox).toBeInTheDocument();
  });

  // 5 — Text input has accessible placeholder (serving as label)
  it("text input has an accessible placeholder", () => {
    renderWithTheme(
      <QuestionCard question={textQuestion} onAnswer={vi.fn()} />,
    );
    const input = screen.getByPlaceholderText("Type your answer...");
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute("type", "text");
  });

  // 6 — Question text is rendered as visible text associated with the form
  it("question text is visible and readable by screen readers", () => {
    renderWithTheme(
      <QuestionCard question={singleChoiceQuestion} onAnswer={vi.fn()} />,
    );
    const questionText = screen.getByText("How large is your organization?");
    expect(questionText).toBeInTheDocument();
    expect(questionText).toBeVisible();
  });

  // 7 — RadioGroup renders as a group (Fluent RadioGroup provides radiogroup role)
  it("single_choice renders as radiogroup role", () => {
    renderWithTheme(
      <QuestionCard question={singleChoiceQuestion} onAnswer={vi.fn()} />,
    );
    const radiogroup = screen.getByRole("radiogroup");
    expect(radiogroup).toBeInTheDocument();
  });

  // 8 — Next button has accessible name
  it("Next button has accessible label", () => {
    renderWithTheme(
      <QuestionCard question={singleChoiceQuestion} onAnswer={vi.fn()} />,
    );
    const nextButton = screen.getByRole("button", { name: /next/i });
    expect(nextButton).toBeInTheDocument();
  });

  // 9 — Next button shows disabled state accessibly
  it("Next button communicates disabled state when no selection", () => {
    renderWithTheme(
      <QuestionCard question={singleChoiceQuestion} onAnswer={vi.fn()} />,
    );
    const nextButton = screen.getByRole("button", { name: /next/i });
    expect(nextButton).toBeDisabled();
  });

  // 10 — Unsure option is accessible as a radio in single_choice
  it("'unsure' option is accessible as a radio input", () => {
    renderWithTheme(
      <QuestionCard question={singleChoiceQuestion} onAnswer={vi.fn()} />,
    );
    const unsureRadio = screen.getByRole("radio", { name: "I'm not sure" });
    expect(unsureRadio).toBeInTheDocument();
  });

  // 11 — Unsure option is accessible as a checkbox in multi_choice
  it("'unsure' option is accessible as a checkbox input", () => {
    renderWithTheme(
      <QuestionCard question={multiChoiceQuestion} onAnswer={vi.fn()} />,
    );
    const unsureCheckbox = screen.getByRole("checkbox", { name: "I'm not sure" });
    expect(unsureCheckbox).toBeInTheDocument();
  });

  // 12 — CAF area badge is visible (provides context)
  it("CAF area badge is visible and provides context", () => {
    renderWithTheme(
      <QuestionCard question={singleChoiceQuestion} onAnswer={vi.fn()} />,
    );
    expect(screen.getByText("Resource Organization")).toBeInTheDocument();
  });

  // 13 — Discovered answer banner is accessible
  it("auto-discovered banner is visible and accessible when present", () => {
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
      />,
    );
    expect(screen.getByText(/Auto-discovered/)).toBeInTheDocument();
    expect(screen.getByText(/Found 50 users/)).toBeInTheDocument();
  });
});
