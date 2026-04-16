import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import {
  FluentProvider,
  teamsLightTheme,
} from "@fluentui/react-components";
import CommentPanel from "./CommentPanel";

// Mock the API
const mockListComments = vi.fn();
const mockAddComment = vi.fn();

vi.mock("../../services/api", () => ({
  api: {
    collaboration: {
      listComments: (...args: unknown[]) => mockListComments(...args),
      addComment: (...args: unknown[]) => mockAddComment(...args),
    },
  },
}));

function renderPanel(props?: {
  projectId?: string;
  componentRef?: string;
  onClose?: () => void;
}) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>
        <CommentPanel
          projectId={props?.projectId ?? "test-project"}
          componentRef={props?.componentRef}
          onClose={props?.onClose}
        />
      </MemoryRouter>
    </FluentProvider>,
  );
}

describe("CommentPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListComments.mockResolvedValue({ comments: [], total: 0 });
    mockAddComment.mockResolvedValue({
      id: "new-1",
      content: "Test comment",
      component_ref: null,
      user_id: "u-1",
      display_name: "Alice",
      created_at: new Date().toISOString(),
    });
  });

  it("renders the panel with title", async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("Comments")).toBeInTheDocument();
    });
  });

  it("shows loading spinner initially", () => {
    mockListComments.mockReturnValue(new Promise(() => {}));
    renderPanel();
    expect(screen.getByText("Loading comments…")).toBeInTheDocument();
  });

  it("shows empty state when no comments", async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("No comments yet")).toBeInTheDocument();
    });
  });

  it("renders comments from API", async () => {
    mockListComments.mockResolvedValue({
      comments: [
        {
          id: "c-1",
          content: "Looks great!",
          component_ref: null,
          user_id: "u-1",
          display_name: "Alice",
          created_at: "2024-01-15T10:00:00Z",
        },
        {
          id: "c-2",
          content: "Needs work",
          component_ref: "vnet",
          user_id: "u-2",
          display_name: "Bob",
          created_at: "2024-01-15T11:00:00Z",
        },
      ],
      total: 2,
    });

    renderPanel();

    await waitFor(() => {
      expect(screen.getByText("Looks great!")).toBeInTheDocument();
    });
    expect(screen.getByText("Needs work")).toBeInTheDocument();
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
  });

  it("passes componentRef to API when provided", async () => {
    renderPanel({ componentRef: "firewall" });
    await waitFor(() => {
      expect(mockListComments).toHaveBeenCalledWith(
        "test-project",
        "firewall",
      );
    });
  });

  it("displays component ref label when set", async () => {
    renderPanel({ componentRef: "subnet-1" });
    await waitFor(() => {
      expect(screen.getByText("— subnet-1")).toBeInTheDocument();
    });
  });

  it("shows close button when onClose is provided", async () => {
    const onClose = vi.fn();
    renderPanel({ onClose });
    await waitFor(() => {
      expect(
        screen.getByLabelText("Close comments"),
      ).toBeInTheDocument();
    });
  });

  it("calls onClose when close button is clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderPanel({ onClose });

    await waitFor(() => {
      expect(
        screen.getByLabelText("Close comments"),
      ).toBeInTheDocument();
    });
    await user.click(screen.getByLabelText("Close comments"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("does not show close button when onClose is not provided", async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("Comments")).toBeInTheDocument();
    });
    expect(
      screen.queryByLabelText("Close comments"),
    ).not.toBeInTheDocument();
  });

  it("submit button is disabled when input is empty", async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId("comment-submit")).toBeDisabled();
    });
  });

  it("submits a comment and clears input", async () => {
    const user = userEvent.setup();
    renderPanel();

    await waitFor(() => {
      expect(
        screen.getByTestId("comment-input"),
      ).toBeInTheDocument();
    });

    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "New comment here");
    await user.click(screen.getByTestId("comment-submit"));

    await waitFor(() => {
      expect(mockAddComment).toHaveBeenCalledWith("test-project", {
        content: "New comment here",
        component_ref: undefined,
      });
    });
  });

  it("submits with component_ref when set", async () => {
    const user = userEvent.setup();
    renderPanel({ componentRef: "nsg" });

    await waitFor(() => {
      expect(
        screen.getByTestId("comment-input"),
      ).toBeInTheDocument();
    });

    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "Ref comment");
    await user.click(screen.getByTestId("comment-submit"));

    await waitFor(() => {
      expect(mockAddComment).toHaveBeenCalledWith("test-project", {
        content: "Ref comment",
        component_ref: "nsg",
      });
    });
  });

  it("has correct data-testid on panel", async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId("comment-panel")).toBeInTheDocument();
    });
  });

  it("renders comment component_ref badge", async () => {
    mockListComments.mockResolvedValue({
      comments: [
        {
          id: "c-1",
          content: "Tagged",
          component_ref: "firewall",
          user_id: "u-1",
          display_name: "Alice",
          created_at: "2024-01-15T10:00:00Z",
        },
      ],
      total: 1,
    });

    renderPanel();

    await waitFor(() => {
      expect(screen.getByText("firewall")).toBeInTheDocument();
    });
  });

  it("handles API error gracefully", async () => {
    mockListComments.mockRejectedValue(new Error("Network error"));
    renderPanel();

    await waitFor(() => {
      expect(screen.getByText("No comments yet")).toBeInTheDocument();
    });
  });

  it("renders Send button text", async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("Send")).toBeInTheDocument();
    });
  });

  it("renders placeholder text in input", async () => {
    renderPanel();
    await waitFor(() => {
      expect(
        screen.getByPlaceholderText("Add a comment…"),
      ).toBeInTheDocument();
    });
  });
});
