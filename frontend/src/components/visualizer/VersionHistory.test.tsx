import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import VersionHistory from "./VersionHistory";
import type { ArchitectureVersionItem } from "../../services/api";

// Mock the api module
vi.mock("../../services/api", () => ({
  api: {
    architectureVersions: {
      list: vi.fn(),
      restore: vi.fn(),
    },
  },
}));

import { api } from "../../services/api";

const mockVersions: ArchitectureVersionItem[] = [
  {
    id: "v-3",
    version_number: 3,
    architecture_json: '{"management_groups":{}}',
    change_summary: "Restored from version 1",
    created_by: "user-1",
    created_at: "2025-01-03T12:00:00Z",
  },
  {
    id: "v-2",
    version_number: 2,
    architecture_json: '{"management_groups":{},"subscriptions":[]}',
    change_summary: "Added subscriptions",
    created_by: "user-1",
    created_at: "2025-01-02T12:00:00Z",
  },
  {
    id: "v-1",
    version_number: 1,
    architecture_json: '{"management_groups":{}}',
    change_summary: "Initial generation",
    created_by: null,
    created_at: "2025-01-01T12:00:00Z",
  },
];

function renderVersionHistory(
  props: Partial<React.ComponentProps<typeof VersionHistory>> = {},
) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <VersionHistory architectureId="arch-1" {...props} />
    </FluentProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("VersionHistory", () => {
  it("shows loading spinner initially", () => {
    vi.mocked(api.architectureVersions.list).mockReturnValue(
      new Promise(() => {}), // never resolves
    );
    renderVersionHistory();
    expect(screen.getByText(/loading version history/i)).toBeInTheDocument();
  });

  it("renders empty state when no versions exist", async () => {
    vi.mocked(api.architectureVersions.list).mockResolvedValue({
      versions: [],
      total: 0,
    });
    renderVersionHistory();
    await waitFor(() => {
      expect(screen.getByText(/no versions recorded/i)).toBeInTheDocument();
    });
  });

  it("renders version list", async () => {
    vi.mocked(api.architectureVersions.list).mockResolvedValue({
      versions: mockVersions,
      total: 3,
    });
    renderVersionHistory();
    await waitFor(() => {
      expect(screen.getByText("v3")).toBeInTheDocument();
    });
    expect(screen.getByText("v2")).toBeInTheDocument();
    expect(screen.getByText("v1")).toBeInTheDocument();
  });

  it("displays change summaries", async () => {
    vi.mocked(api.architectureVersions.list).mockResolvedValue({
      versions: mockVersions,
      total: 3,
    });
    renderVersionHistory();
    await waitFor(() => {
      expect(screen.getByText("Restored from version 1")).toBeInTheDocument();
    });
    expect(screen.getByText("Added subscriptions")).toBeInTheDocument();
    expect(screen.getByText("Initial generation")).toBeInTheDocument();
  });

  it("shows version count badge", async () => {
    vi.mocked(api.architectureVersions.list).mockResolvedValue({
      versions: mockVersions,
      total: 3,
    });
    renderVersionHistory();
    await waitFor(() => {
      expect(screen.getByText("3")).toBeInTheDocument();
    });
  });

  it("renders View and Restore buttons for each version", async () => {
    vi.mocked(api.architectureVersions.list).mockResolvedValue({
      versions: mockVersions,
      total: 3,
    });
    renderVersionHistory();
    await waitFor(() => {
      expect(screen.getAllByRole("button", { name: /view version/i })).toHaveLength(3);
    });
    expect(screen.getAllByRole("button", { name: /restore version/i })).toHaveLength(3);
  });

  it("calls onViewVersion when View is clicked", async () => {
    vi.mocked(api.architectureVersions.list).mockResolvedValue({
      versions: mockVersions,
      total: 3,
    });
    const onView = vi.fn();
    const user = userEvent.setup();
    renderVersionHistory({ onViewVersion: onView });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /view version 3/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /view version 3/i }));
    expect(onView).toHaveBeenCalledWith(mockVersions[0]);
  });

  it("calls API restore when Restore is clicked", async () => {
    vi.mocked(api.architectureVersions.list).mockResolvedValue({
      versions: mockVersions,
      total: 3,
    });
    vi.mocked(api.architectureVersions.restore).mockResolvedValue({
      id: "v-4",
      version_number: 4,
      architecture_json: "{}",
      change_summary: "Restored from version 1",
      created_by: "user-1",
      created_at: "2025-01-04T12:00:00Z",
    });
    const onRestore = vi.fn();
    const user = userEvent.setup();
    renderVersionHistory({ onRestoreVersion: onRestore });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /restore version 1/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /restore version 1/i }));

    await waitFor(() => {
      expect(api.architectureVersions.restore).toHaveBeenCalledWith("arch-1", 1);
    });
    expect(onRestore).toHaveBeenCalled();
  });

  it("shows error message on API failure", async () => {
    vi.mocked(api.architectureVersions.list).mockRejectedValue(
      new Error("Network error"),
    );
    renderVersionHistory();
    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });

  it("has accessible list structure", async () => {
    vi.mocked(api.architectureVersions.list).mockResolvedValue({
      versions: mockVersions,
      total: 3,
    });
    renderVersionHistory();
    await waitFor(() => {
      expect(screen.getByRole("list", { name: /architecture versions/i })).toBeInTheDocument();
    });
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
  });

  it("displays created_by when present", async () => {
    vi.mocked(api.architectureVersions.list).mockResolvedValue({
      versions: [mockVersions[0]],
      total: 1,
    });
    renderVersionHistory();
    await waitFor(() => {
      expect(screen.getByText("user-1")).toBeInTheDocument();
    });
  });

  it("displays fallback text when change_summary is null", async () => {
    vi.mocked(api.architectureVersions.list).mockResolvedValue({
      versions: [{
        id: "v-x",
        version_number: 1,
        architecture_json: "{}",
        change_summary: null,
        created_by: null,
        created_at: "2025-01-01T00:00:00Z",
      }],
      total: 1,
    });
    renderVersionHistory();
    await waitFor(() => {
      expect(screen.getByText("Version 1")).toBeInTheDocument();
    });
  });

  it("disables restore buttons while restoring", async () => {
    vi.mocked(api.architectureVersions.list).mockResolvedValue({
      versions: mockVersions,
      total: 3,
    });
    // Never-resolving restore to test disabled state
    vi.mocked(api.architectureVersions.restore).mockReturnValue(
      new Promise(() => {}),
    );
    const user = userEvent.setup();
    renderVersionHistory();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /restore version 1/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /restore version 1/i }));

    // All restore buttons should be disabled during restore
    const restoreButtons = screen.getAllByRole("button", { name: /restore version/i });
    restoreButtons.forEach((btn) => {
      expect(btn).toBeDisabled();
    });
  });

  it("renders 'Version History' heading", async () => {
    vi.mocked(api.architectureVersions.list).mockResolvedValue({
      versions: [],
      total: 0,
    });
    renderVersionHistory();
    await waitFor(() => {
      expect(screen.getByText("Version History")).toBeInTheDocument();
    });
  });
});
