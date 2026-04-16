import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import {
  FluentProvider,
  teamsLightTheme,
} from "@fluentui/react-components";
import ActivityFeed from "./ActivityFeed";

// Mock the API
const mockGetActivity = vi.fn();

vi.mock("../../services/api", () => ({
  api: {
    collaboration: {
      getActivity: (...args: unknown[]) => mockGetActivity(...args),
    },
  },
}));

function renderFeed(projectId = "test-project") {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>
        <ActivityFeed projectId={projectId} />
      </MemoryRouter>
    </FluentProvider>,
  );
}

describe("ActivityFeed", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetActivity.mockResolvedValue({ activities: [] });
  });

  it("renders the title", async () => {
    renderFeed();
    await waitFor(() => {
      expect(screen.getByText("Activity Feed")).toBeInTheDocument();
    });
  });

  it("shows loading spinner initially", () => {
    mockGetActivity.mockReturnValue(new Promise(() => {}));
    renderFeed();
    expect(screen.getByText("Loading activity…")).toBeInTheDocument();
  });

  it("shows empty state when no activities", async () => {
    renderFeed();
    await waitFor(() => {
      expect(screen.getByText("No activity yet")).toBeInTheDocument();
    });
  });

  it("renders activities from API", async () => {
    mockGetActivity.mockResolvedValue({
      activities: [
        {
          type: "member_joined",
          user_id: "u-1",
          description: "Alice joined as editor",
          timestamp: "2024-01-15T10:00:00Z",
        },
        {
          type: "comment_added",
          user_id: "u-2",
          description: "Bob commented on vnet-hub",
          timestamp: "2024-01-15T11:00:00Z",
        },
      ],
    });

    renderFeed();

    await waitFor(() => {
      expect(
        screen.getByText("Alice joined as editor"),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByText("Bob commented on vnet-hub"),
    ).toBeInTheDocument();
  });

  it("calls API with correct project ID", async () => {
    renderFeed("my-project");
    await waitFor(() => {
      expect(mockGetActivity).toHaveBeenCalledWith("my-project");
    });
  });

  it("handles API error gracefully", async () => {
    mockGetActivity.mockRejectedValue(new Error("Network error"));
    renderFeed();

    await waitFor(() => {
      expect(screen.getByText("No activity yet")).toBeInTheDocument();
    });
  });

  it("has correct data-testid", async () => {
    renderFeed();
    await waitFor(() => {
      expect(screen.getByTestId("activity-feed")).toBeInTheDocument();
    });
  });

  it("renders timestamps for entries", async () => {
    mockGetActivity.mockResolvedValue({
      activities: [
        {
          type: "member_joined",
          user_id: "u-1",
          description: "Alice joined",
          timestamp: "2024-06-01T12:00:00Z",
        },
      ],
    });

    renderFeed();

    await waitFor(() => {
      expect(screen.getByText("Alice joined")).toBeInTheDocument();
    });
  });

  it("renders multiple activity types", async () => {
    mockGetActivity.mockResolvedValue({
      activities: [
        {
          type: "member_joined",
          user_id: "u-1",
          description: "Joined team",
          timestamp: "2024-01-15T10:00:00Z",
        },
        {
          type: "comment_added",
          user_id: "u-2",
          description: "Added a comment",
          timestamp: "2024-01-15T11:00:00Z",
        },
        {
          type: "member_joined",
          user_id: "u-3",
          description: "New member",
          timestamp: "2024-01-15T12:00:00Z",
        },
      ],
    });

    renderFeed();

    await waitFor(() => {
      expect(screen.getByText("Joined team")).toBeInTheDocument();
      expect(
        screen.getByText("Added a comment"),
      ).toBeInTheDocument();
      expect(screen.getByText("New member")).toBeInTheDocument();
    });
  });

  it("re-fetches when projectId changes", async () => {
    const { rerender } = renderFeed("proj-a");

    await waitFor(() => {
      expect(mockGetActivity).toHaveBeenCalledWith("proj-a");
    });

    rerender(
      <FluentProvider theme={teamsLightTheme}>
        <MemoryRouter>
          <ActivityFeed projectId="proj-b" />
        </MemoryRouter>
      </FluentProvider>,
    );

    await waitFor(() => {
      expect(mockGetActivity).toHaveBeenCalledWith("proj-b");
    });
  });
});
