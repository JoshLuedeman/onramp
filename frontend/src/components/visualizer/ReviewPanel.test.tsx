import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import {
  FluentProvider,
  teamsLightTheme,
} from "@fluentui/react-components";
import ReviewPanel from "./ReviewPanel";

// Mock the API
const mockGetStatus = vi.fn();
const mockGetHistory = vi.fn();
const mockSubmit = vi.fn();
const mockPerform = vi.fn();
const mockWithdraw = vi.fn();

vi.mock("../../services/api", () => ({
  api: {
    reviews: {
      getStatus: (...args: unknown[]) => mockGetStatus(...args),
      getHistory: (...args: unknown[]) => mockGetHistory(...args),
      submit: (...args: unknown[]) => mockSubmit(...args),
      perform: (...args: unknown[]) => mockPerform(...args),
      withdraw: (...args: unknown[]) => mockWithdraw(...args),
    },
  },
}));

const DEFAULT_STATUS = {
  status: "draft",
  is_locked: false,
  can_deploy: false,
  approvals_needed: 1,
  approvals_received: 0,
};

const DEFAULT_HISTORY = {
  reviews: [],
  current_status: "draft",
  required_approvals: 1,
  approvals_received: 0,
};

function renderPanel(props?: {
  architectureId?: string;
  onClose?: () => void;
}) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>
        <ReviewPanel
          architectureId={props?.architectureId ?? "test-arch-id"}
          onClose={props?.onClose}
        />
      </MemoryRouter>
    </FluentProvider>,
  );
}

describe("ReviewPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetStatus.mockResolvedValue({ ...DEFAULT_STATUS });
    mockGetHistory.mockResolvedValue({ ...DEFAULT_HISTORY });
    mockSubmit.mockResolvedValue({
      architecture_id: "test-arch-id",
      status: "in_review",
      is_locked: true,
    });
    mockPerform.mockResolvedValue({
      id: "review-1",
      architecture_id: "test-arch-id",
      reviewer_id: "user-1",
      action: "approved",
      comments: null,
      created_at: new Date().toISOString(),
    });
    mockWithdraw.mockResolvedValue({
      architecture_id: "test-arch-id",
      status: "draft",
      is_locked: false,
    });
  });

  it("renders the panel with title", async () => {
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByText("Architecture Review"),
      ).toBeInTheDocument();
    });
  });

  it("shows loading spinner initially", () => {
    mockGetStatus.mockReturnValue(new Promise(() => {}));
    mockGetHistory.mockReturnValue(new Promise(() => {}));
    renderPanel();
    expect(
      screen.getByText("Loading review status…"),
    ).toBeInTheDocument();
  });

  it("shows draft status badge", async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("Draft")).toBeInTheDocument();
    });
  });

  it("shows Submit for Review button in draft state", async () => {
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByTestId("submit-for-review-btn"),
      ).toBeInTheDocument();
    });
  });

  it("shows In Review badge when status is in_review", async () => {
    mockGetStatus.mockResolvedValue({
      ...DEFAULT_STATUS,
      status: "in_review",
      is_locked: true,
    });
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("In Review")).toBeInTheDocument();
    });
  });

  it("shows lock indicator when architecture is locked", async () => {
    mockGetStatus.mockResolvedValue({
      ...DEFAULT_STATUS,
      status: "in_review",
      is_locked: true,
    });
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByTestId("lock-indicator"),
      ).toBeInTheDocument();
      expect(screen.getByText("Locked")).toBeInTheDocument();
    });
  });

  it("shows reviewer actions when in_review", async () => {
    mockGetStatus.mockResolvedValue({
      ...DEFAULT_STATUS,
      status: "in_review",
      is_locked: true,
    });
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByTestId("approve-btn"),
      ).toBeInTheDocument();
      expect(
        screen.getByTestId("request-changes-btn"),
      ).toBeInTheDocument();
      expect(
        screen.getByTestId("reject-btn"),
      ).toBeInTheDocument();
    });
  });

  it("shows Approved badge when status is approved", async () => {
    mockGetStatus.mockResolvedValue({
      ...DEFAULT_STATUS,
      status: "approved",
      can_deploy: true,
      approvals_received: 1,
    });
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("Approved")).toBeInTheDocument();
    });
  });

  it("shows Rejected badge when status is rejected", async () => {
    mockGetStatus.mockResolvedValue({
      ...DEFAULT_STATUS,
      status: "rejected",
    });
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("Rejected")).toBeInTheDocument();
    });
  });

  it("shows approval progress text", async () => {
    mockGetStatus.mockResolvedValue({
      ...DEFAULT_STATUS,
      status: "in_review",
      approvals_needed: 2,
      approvals_received: 1,
    });
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByText("1 of 2 approvals"),
      ).toBeInTheDocument();
    });
  });

  it("shows empty review history", async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("No reviews yet")).toBeInTheDocument();
    });
  });

  it("renders review history items", async () => {
    mockGetHistory.mockResolvedValue({
      reviews: [
        {
          id: "r-1",
          architecture_id: "test-arch-id",
          reviewer_id: "user-1",
          action: "approved",
          comments: "Looks great!",
          created_at: "2024-06-15T10:00:00Z",
        },
        {
          id: "r-2",
          architecture_id: "test-arch-id",
          reviewer_id: "user-2",
          action: "changes_requested",
          comments: "Fix networking",
          created_at: "2024-06-15T09:00:00Z",
        },
      ],
      current_status: "in_review",
      required_approvals: 2,
      approvals_received: 1,
    });
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("Looks great!")).toBeInTheDocument();
      expect(screen.getByText("Fix networking")).toBeInTheDocument();
    });
  });

  it("calls submit API when Submit for Review is clicked", async () => {
    const user = userEvent.setup();
    renderPanel();

    await waitFor(() => {
      expect(
        screen.getByTestId("submit-for-review-btn"),
      ).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("submit-for-review-btn"));
    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledWith("test-arch-id");
    });
  });

  it("calls withdraw API when Withdraw is clicked", async () => {
    const user = userEvent.setup();
    mockGetStatus.mockResolvedValue({
      ...DEFAULT_STATUS,
      status: "in_review",
      is_locked: true,
    });
    renderPanel();

    await waitFor(() => {
      expect(
        screen.getByTestId("withdraw-btn"),
      ).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("withdraw-btn"));
    await waitFor(() => {
      expect(mockWithdraw).toHaveBeenCalledWith("test-arch-id");
    });
  });

  it("opens dialog when approve is clicked", async () => {
    const user = userEvent.setup();
    mockGetStatus.mockResolvedValue({
      ...DEFAULT_STATUS,
      status: "in_review",
      is_locked: true,
    });
    renderPanel();

    await waitFor(() => {
      expect(
        screen.getByTestId("approve-btn"),
      ).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("approve-btn"));
    await waitFor(() => {
      expect(
        screen.getByText("Approve Architecture"),
      ).toBeInTheDocument();
    });
  });

  it("shows close button when onClose is provided", async () => {
    const onClose = vi.fn();
    renderPanel({ onClose });
    await waitFor(() => {
      expect(
        screen.getByLabelText("Close review panel"),
      ).toBeInTheDocument();
    });
  });

  it("calls onClose when close button is clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderPanel({ onClose });

    await waitFor(() => {
      expect(
        screen.getByLabelText("Close review panel"),
      ).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText("Close review panel"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("does not show close button when onClose is not provided", async () => {
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByText("Architecture Review"),
      ).toBeInTheDocument();
    });
    expect(
      screen.queryByLabelText("Close review panel"),
    ).not.toBeInTheDocument();
  });

  it("shows withdraw button when status is rejected", async () => {
    mockGetStatus.mockResolvedValue({
      ...DEFAULT_STATUS,
      status: "rejected",
    });
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByTestId("withdraw-btn"),
      ).toBeInTheDocument();
    });
  });

  it("does not show submit button when not in draft", async () => {
    mockGetStatus.mockResolvedValue({
      ...DEFAULT_STATUS,
      status: "approved",
      can_deploy: true,
    });
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByText("Approved"),
      ).toBeInTheDocument();
    });
    expect(
      screen.queryByTestId("submit-for-review-btn"),
    ).not.toBeInTheDocument();
  });

  it("handles API error gracefully", async () => {
    mockGetStatus.mockRejectedValue(new Error("Network error"));
    mockGetHistory.mockRejectedValue(new Error("Network error"));
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByText("Architecture Review"),
      ).toBeInTheDocument();
    });
  });

  it("has correct data-testid on panel", async () => {
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByTestId("review-panel"),
      ).toBeInTheDocument();
    });
  });

  it("renders Review History title", async () => {
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByText("Review History"),
      ).toBeInTheDocument();
    });
  });
});
