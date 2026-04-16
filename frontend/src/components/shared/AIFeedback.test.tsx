import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import AIFeedback, { type FeedbackPayload } from "./AIFeedback";

/* ------------------------------------------------------------------ */
/*  Helper                                                             */
/* ------------------------------------------------------------------ */

function renderFeedback(
  props: Partial<React.ComponentProps<typeof AIFeedback>> = {}
) {
  const defaultProps = {
    feature: "architecture",
    outputId: "output-123",
    onFeedback: vi.fn(),
    ...props,
  };

  return {
    ...render(
      <FluentProvider theme={teamsLightTheme}>
        <AIFeedback {...defaultProps} />
      </FluentProvider>
    ),
    onFeedback: defaultProps.onFeedback,
  };
}

/* ------------------------------------------------------------------ */
/*  Tests                                                              */
/* ------------------------------------------------------------------ */

describe("AIFeedback", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // 1 ─ renders the component
  it("renders the feedback widget", () => {
    renderFeedback();
    expect(screen.getByTestId("ai-feedback")).toBeInTheDocument();
    expect(screen.getByText("Was this helpful?")).toBeInTheDocument();
  });

  // 2 ─ renders thumbs-up button
  it("renders a thumbs-up button", () => {
    renderFeedback();
    expect(
      screen.getByRole("button", { name: /thumbs up/i })
    ).toBeInTheDocument();
  });

  // 3 ─ renders thumbs-down button
  it("renders a thumbs-down button", () => {
    renderFeedback();
    expect(
      screen.getByRole("button", { name: /thumbs down/i })
    ).toBeInTheDocument();
  });

  // 4 ─ positive click fires callback immediately
  it("calls onFeedback with positive rating on thumbs-up click", async () => {
    const user = userEvent.setup();
    const { onFeedback } = renderFeedback();

    await user.click(screen.getByRole("button", { name: /thumbs up/i }));

    expect(onFeedback).toHaveBeenCalledTimes(1);
    expect(onFeedback).toHaveBeenCalledWith({
      feature: "architecture",
      outputId: "output-123",
      rating: "positive",
    });
  });

  // 5 ─ negative click opens the dialog
  it("opens a comment dialog on thumbs-down click", async () => {
    const user = userEvent.setup();
    renderFeedback();

    await user.click(screen.getByRole("button", { name: /thumbs down/i }));

    expect(
      screen.getByText("What could be improved?")
    ).toBeInTheDocument();
  });

  // 6 ─ submit negative feedback with comment
  it("submits negative feedback with a comment via Submit button", async () => {
    const user = userEvent.setup();
    const { onFeedback } = renderFeedback();

    await user.click(screen.getByRole("button", { name: /thumbs down/i }));

    const textarea = screen.getByLabelText("Feedback comment");
    // Use fireEvent for reliable value setting with Fluent UI controlled Textarea
    fireEvent.change(textarea, { target: { value: "The cost estimate was way off" } });

    const submitBtn = await screen.findByText("Submit");
    await user.click(submitBtn);

    expect(onFeedback).toHaveBeenCalledTimes(1);
    expect(onFeedback).toHaveBeenCalledWith({
      feature: "architecture",
      outputId: "output-123",
      rating: "negative",
      comment: "The cost estimate was way off",
    });
  });

  // 7 ─ skip sends negative without comment
  it("sends negative feedback without comment when Skip is clicked", async () => {
    const user = userEvent.setup();
    const { onFeedback } = renderFeedback();

    await user.click(screen.getByRole("button", { name: /thumbs down/i }));
    await user.click(screen.getByRole("button", { name: /skip/i }));

    expect(onFeedback).toHaveBeenCalledTimes(1);
    expect(onFeedback).toHaveBeenCalledWith({
      feature: "architecture",
      outputId: "output-123",
      rating: "negative",
    });
  });

  // 8 ─ dialog closes after submit
  it("closes the dialog after submitting feedback", async () => {
    const user = userEvent.setup();
    renderFeedback();

    await user.click(screen.getByRole("button", { name: /thumbs down/i }));
    expect(screen.getByText("What could be improved?")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /submit/i }));

    await waitFor(() => {
      expect(
        screen.queryByText("What could be improved?")
      ).not.toBeInTheDocument();
    });
  });

  // 9 ─ renders without onFeedback prop (optional)
  it("renders without crashing when onFeedback is not provided", async () => {
    const user = userEvent.setup();
    render(
      <FluentProvider theme={teamsLightTheme}>
        <AIFeedback feature="compliance" outputId="out-1" />
      </FluentProvider>
    );

    // Should not throw
    await user.click(screen.getByRole("button", { name: /thumbs up/i }));
    expect(screen.getByTestId("ai-feedback")).toBeInTheDocument();
  });

  // 10 ─ passes correct feature and outputId to callback
  it("passes the correct feature and outputId to the callback", async () => {
    const user = userEvent.setup();
    const { onFeedback } = renderFeedback({
      feature: "bicep_generation",
      outputId: "bicep-456",
    });

    await user.click(screen.getByRole("button", { name: /thumbs up/i }));

    const payload = onFeedback.mock.calls[0][0] as FeedbackPayload;
    expect(payload.feature).toBe("bicep_generation");
    expect(payload.outputId).toBe("bicep-456");
  });

  // 11 ─ dialog has a textarea
  it("shows a textarea in the negative feedback dialog", async () => {
    const user = userEvent.setup();
    renderFeedback();

    await user.click(screen.getByRole("button", { name: /thumbs down/i }));

    expect(screen.getByLabelText("Feedback comment")).toBeInTheDocument();
  });

  // 12 ─ submit with empty comment sends undefined
  it("sends undefined comment when textarea is left empty on submit", async () => {
    const user = userEvent.setup();
    const { onFeedback } = renderFeedback();

    await user.click(screen.getByRole("button", { name: /thumbs down/i }));
    await user.click(screen.getByRole("button", { name: /submit/i }));

    expect(onFeedback).toHaveBeenCalledWith({
      feature: "architecture",
      outputId: "output-123",
      rating: "negative",
      comment: undefined,
    });
  });
});
