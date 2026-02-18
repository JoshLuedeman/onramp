import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import WizardPage from "./WizardPage";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate, useParams: () => ({}) };
});

const mockGetNextQuestion = vi.fn();
const mockResolveUnsure = vi.fn();
const mockGenerate = vi.fn();

vi.mock("../services/api", () => ({
  api: {
    questionnaire: {
      getNextQuestion: (...args: unknown[]) => mockGetNextQuestion(...args),
      resolveUnsure: (...args: unknown[]) => mockResolveUnsure(...args),
    },
    architecture: {
      generate: (...args: unknown[]) => mockGenerate(...args),
    },
  },
}));

function renderPage() {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <WizardPage />
    </FluentProvider>,
  );
}

const mockQuestion = {
  id: "org_size",
  category: "Organization",
  caf_area: "ready",
  text: "What is the size of your organization?",
  type: "single_choice" as const,
  options: [
    { value: "small", label: "Small" },
    { value: "medium", label: "Medium" },
    { value: "large", label: "Large" },
  ],
  required: true,
  order: 1,
};

const mockProgress = {
  total: 10,
  answered: 0,
  remaining: 10,
  percent_complete: 0,
};

describe("WizardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    mockResolveUnsure.mockResolvedValue({ recommendations: [], resolved_answers: null });
  });

  it("shows loading spinner initially", () => {
    mockGetNextQuestion.mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("renders a question after loading", async () => {
    mockGetNextQuestion.mockResolvedValue({
      complete: false,
      question: mockQuestion,
      progress: mockProgress,
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(mockQuestion.text)).toBeInTheDocument();
    });
  });

  it("saves answer to sessionStorage", async () => {
    const user = userEvent.setup();
    const secondQuestion = { ...mockQuestion, id: "q2", text: "Second question?" };

    mockGetNextQuestion
      .mockResolvedValueOnce({
        complete: false,
        question: mockQuestion,
        progress: mockProgress,
      })
      .mockResolvedValueOnce({
        complete: false,
        question: secondQuestion,
        progress: { ...mockProgress, answered: 1, remaining: 9, percent_complete: 10 },
      });

    renderPage();
    await waitFor(() => {
      expect(screen.getByText(mockQuestion.text)).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText("Small"));
    await user.click(screen.getByRole("button", { name: /next/i }));

    await waitFor(() => {
      const saved = sessionStorage.getItem("onramp_wizard_answers");
      expect(saved).toBeTruthy();
      expect(JSON.parse(saved!)).toHaveProperty("org_size");
    });
  });

  it("shows back button after answering a question", async () => {
    const user = userEvent.setup();
    const secondQuestion = { ...mockQuestion, id: "q2", text: "Second question?" };

    mockGetNextQuestion
      .mockResolvedValueOnce({
        complete: false,
        question: mockQuestion,
        progress: mockProgress,
      })
      .mockResolvedValueOnce({
        complete: false,
        question: secondQuestion,
        progress: { ...mockProgress, answered: 1, remaining: 9, percent_complete: 10 },
      });

    renderPage();
    await waitFor(() => {
      expect(screen.getByText(mockQuestion.text)).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText("Small"));
    await user.click(screen.getByRole("button", { name: /next/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /back/i })).toBeInTheDocument();
    });
  });

  it("clears sessionStorage and resets on Start Over", async () => {
    const user = userEvent.setup();
    const secondQuestion = { ...mockQuestion, id: "q2", text: "Second question?" };

    mockGetNextQuestion
      .mockResolvedValueOnce({
        complete: false,
        question: mockQuestion,
        progress: mockProgress,
      })
      .mockResolvedValueOnce({
        complete: false,
        question: secondQuestion,
        progress: { ...mockProgress, answered: 1, remaining: 9, percent_complete: 10 },
      })
      .mockResolvedValueOnce({
        complete: false,
        question: mockQuestion,
        progress: mockProgress,
      });

    renderPage();
    await waitFor(() => {
      expect(screen.getByText(mockQuestion.text)).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText("Small"));
    await user.click(screen.getByRole("button", { name: /next/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /start over/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /start over/i }));

    expect(sessionStorage.getItem("onramp_wizard_answers")).toBeNull();
    expect(mockGetNextQuestion).toHaveBeenCalledWith({});
  });

  it("shows completion state when API returns complete", async () => {
    // Seed answers so the completion state renders with history
    sessionStorage.setItem("onramp_wizard_answers", JSON.stringify({ org_size: "small" }));

    mockGetNextQuestion.mockResolvedValue({
      complete: true,
      question: null,
      progress: { total: 10, answered: 10, remaining: 0, percent_complete: 100 },
    });

    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/questionnaire complete/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /generate architecture/i })).toBeInTheDocument();
  });

  it("restores answers from sessionStorage on mount", async () => {
    const savedAnswers = { org_size: "Medium" };
    sessionStorage.setItem("onramp_wizard_answers", JSON.stringify(savedAnswers));

    mockGetNextQuestion.mockResolvedValue({
      complete: false,
      question: { ...mockQuestion, id: "q2", text: "Second question?" },
      progress: { ...mockProgress, answered: 1, remaining: 9, percent_complete: 10 },
    });

    renderPage();
    await waitFor(() => {
      expect(mockGetNextQuestion).toHaveBeenCalledWith(savedAnswers);
    });
  });

  it("renders the page title", async () => {
    mockGetNextQuestion.mockResolvedValue({
      complete: false,
      question: mockQuestion,
      progress: mockProgress,
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Design Your Landing Zone")).toBeInTheDocument();
    });
  });
});
