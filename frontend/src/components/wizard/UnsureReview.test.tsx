import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import UnsureReview from "./UnsureReview";

function renderWithTheme(ui: React.ReactElement) {
  return render(<FluentProvider theme={teamsLightTheme}>{ui}</FluentProvider>);
}

const mockRecommendations = [
  {
    question_id: "org_size",
    recommended_value: "medium",
    reason: "Based on your answers, a medium-size configuration is best.",
  },
  {
    question_id: "network_topology",
    recommended_value: "hub_spoke",
    reason: "Hub-spoke provides centralized security.",
  },
];

describe("UnsureReview", () => {
  it("renders recommendation cards", () => {
    renderWithTheme(
      <UnsureReview
        recommendations={mockRecommendations}
        onAccept={vi.fn()}
      />
    );
    expect(screen.getByText(/Medium/)).toBeInTheDocument();
    expect(screen.getByText(/Hub Spoke/)).toBeInTheDocument();
  });

  it("shows reason text", () => {
    renderWithTheme(
      <UnsureReview
        recommendations={mockRecommendations}
        onAccept={vi.fn()}
      />
    );
    expect(screen.getByText(/centralized security/i)).toBeInTheDocument();
  });

  it("displays the header with question count", () => {
    renderWithTheme(
      <UnsureReview
        recommendations={mockRecommendations}
        onAccept={vi.fn()}
      />
    );
    expect(screen.getByText(/AI Recommendations/i)).toBeInTheDocument();
    expect(screen.getByText(/2 questions/i)).toBeInTheDocument();
  });

  it("calls onAccept with resolved answers when continue is clicked", async () => {
    const onAccept = vi.fn();
    renderWithTheme(
      <UnsureReview
        recommendations={mockRecommendations}
        onAccept={onAccept}
      />
    );
    const button = screen.getByRole("button", { name: /continue with recommendations/i });
    await userEvent.click(button);
    expect(onAccept).toHaveBeenCalledWith({
      org_size: "medium",
      network_topology: "hub_spoke",
    });
  });
});
