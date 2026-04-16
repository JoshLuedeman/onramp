import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import VersionDiff from "./VersionDiff";

// Mock the api module
vi.mock("../../services/api", () => ({
  api: {
    architectureVersions: {
      diff: vi.fn(),
    },
  },
}));

import { api } from "../../services/api";

function renderDiff(
  props: Partial<React.ComponentProps<typeof VersionDiff>> = {},
) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <VersionDiff
        architectureId="arch-1"
        fromVersion={1}
        toVersion={2}
        {...props}
      />
    </FluentProvider>,
  );
}

const enhancedDiffData = {
  from_version: 1,
  to_version: 2,
  added_components: [
    {
      name: "compliance_frameworks",
      detail: "Added compliance_frameworks",
      category: "security",
      property_diffs: [],
    },
  ],
  removed_components: [
    {
      name: "subscriptions",
      detail: "Removed subscriptions",
      category: "networking",
      property_diffs: [],
    },
  ],
  modified_components: [
    {
      name: "network_topology",
      detail: "network_topology: 1 key(s) added",
      category: "networking",
      property_diffs: [
        {
          property_name: "hub",
          old_value: "10.0.0.0/16",
          new_value: "10.1.0.0/16",
          change_type: "modified" as const,
        },
        {
          property_name: "spoke",
          old_value: null,
          new_value: "10.2.0.0/16",
          change_type: "added" as const,
        },
      ],
    },
  ],
  summary: "Added 1: compliance_frameworks; Removed 1: subscriptions; Modified 1: network_topology",
  change_counts: { added: 1, removed: 1, modified: 1, total: 3 },
  category_groups: [
    {
      category: "networking",
      display_name: "Networking & Management",
      added: [],
      removed: [
        {
          name: "subscriptions",
          detail: "Removed subscriptions",
          category: "networking",
          property_diffs: [],
        },
      ],
      modified: [
        {
          name: "network_topology",
          detail: "network_topology: 1 key(s) added",
          category: "networking",
          property_diffs: [
            {
              property_name: "hub",
              old_value: "10.0.0.0/16",
              new_value: "10.1.0.0/16",
              change_type: "modified" as const,
            },
          ],
        },
      ],
    },
    {
      category: "security",
      display_name: "Security & Compliance",
      added: [
        {
          name: "compliance_frameworks",
          detail: "Added compliance_frameworks",
          category: "security",
          property_diffs: [],
        },
      ],
      removed: [],
      modified: [],
    },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("VersionDiff", () => {
  it("shows loading spinner initially", () => {
    vi.mocked(api.architectureVersions.diff).mockReturnValue(
      new Promise(() => {}),
    );
    renderDiff();
    expect(screen.getByText(/computing diff/i)).toBeInTheDocument();
  });

  it("shows error on API failure", async () => {
    vi.mocked(api.architectureVersions.diff).mockRejectedValue(
      new Error("Server error"),
    );
    renderDiff();
    await waitFor(() => {
      expect(screen.getByText("Server error")).toBeInTheDocument();
    });
  });

  it("renders version range badges", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue({
      ...enhancedDiffData,
      added_components: [],
      removed_components: [],
      modified_components: [],
      summary: "No changes detected",
      change_counts: { added: 0, removed: 0, modified: 0, total: 0 },
      category_groups: [],
    });
    renderDiff();
    await waitFor(() => {
      expect(screen.getByText("v1")).toBeInTheDocument();
    });
    expect(screen.getByText("v2")).toBeInTheDocument();
  });

  it("renders summary text", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue(
      enhancedDiffData,
    );
    renderDiff();
    await waitFor(() => {
      expect(
        screen.getByText(enhancedDiffData.summary),
      ).toBeInTheDocument();
    });
  });

  it("renders added components", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue(
      enhancedDiffData,
    );
    renderDiff();
    await waitFor(() => {
      expect(
        screen.getByText("compliance_frameworks"),
      ).toBeInTheDocument();
    });
  });

  it("renders removed components", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue(
      enhancedDiffData,
    );
    renderDiff();
    await waitFor(() => {
      expect(screen.getByText("subscriptions")).toBeInTheDocument();
    });
  });

  it("renders modified components", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue(
      enhancedDiffData,
    );
    renderDiff();
    await waitFor(() => {
      expect(
        screen.getByText("network_topology"),
      ).toBeInTheDocument();
    });
  });

  it("shows empty state when no differences", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue({
      ...enhancedDiffData,
      from_version: 1,
      to_version: 1,
      added_components: [],
      removed_components: [],
      modified_components: [],
      summary: "No changes detected",
      change_counts: { added: 0, removed: 0, modified: 0, total: 0 },
      category_groups: [],
    });
    renderDiff();
    await waitFor(() => {
      expect(
        screen.getByText(/no differences found/i),
      ).toBeInTheDocument();
    });
  });

  it("renders 'Version Diff' heading", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue(
      enhancedDiffData,
    );
    renderDiff();
    await waitFor(() => {
      expect(screen.getByText("Version Diff")).toBeInTheDocument();
    });
  });

  it("has accessible container label", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue(
      enhancedDiffData,
    );
    renderDiff();
    await waitFor(() => {
      expect(
        screen.getByLabelText("Version diff"),
      ).toBeInTheDocument();
    });
  });

  it("calls API with correct params", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue(
      enhancedDiffData,
    );
    renderDiff({
      architectureId: "my-arch",
      fromVersion: 5,
      toVersion: 8,
    });
    await waitFor(() => {
      expect(api.architectureVersions.diff).toHaveBeenCalledWith(
        "my-arch", 5, 8,
      );
    });
  });

  // ── Enhanced: View Mode Toggle ──────────────────────────────────────

  it("shows inline and side-by-side toggle buttons", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue(
      enhancedDiffData,
    );
    renderDiff();
    await waitFor(() => {
      expect(screen.getByTestId("view-inline")).toBeInTheDocument();
    });
    expect(
      screen.getByTestId("view-side-by-side"),
    ).toBeInTheDocument();
  });

  it("switches to side-by-side view when clicked", async () => {
    const user = userEvent.setup();
    vi.mocked(api.architectureVersions.diff).mockResolvedValue(
      enhancedDiffData,
    );
    renderDiff();
    await waitFor(() => {
      expect(
        screen.getByTestId("view-side-by-side"),
      ).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("view-side-by-side"));
    await waitFor(() => {
      expect(
        screen.getByTestId("side-by-side-view"),
      ).toBeInTheDocument();
    });
  });

  it("side-by-side view shows before/after columns", async () => {
    const user = userEvent.setup();
    vi.mocked(api.architectureVersions.diff).mockResolvedValue(
      enhancedDiffData,
    );
    renderDiff();
    await waitFor(() => {
      expect(
        screen.getByTestId("view-side-by-side"),
      ).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("view-side-by-side"));
    await waitFor(() => {
      expect(
        screen.getByText("v1 (Before)"),
      ).toBeInTheDocument();
      expect(
        screen.getByText("v2 (After)"),
      ).toBeInTheDocument();
    });
  });

  // ── Enhanced: Category Groups ─────────────────────────────────────

  it("renders category group headers", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue(
      enhancedDiffData,
    );
    renderDiff();
    await waitFor(() => {
      expect(
        screen.getByText("Networking & Management"),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByText("Security & Compliance"),
    ).toBeInTheDocument();
  });

  // ── Enhanced: Property-Level Diffs ────────────────────────────────

  it("shows property diffs in modified components", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue(
      enhancedDiffData,
    );
    renderDiff();
    await waitFor(() => {
      expect(screen.getByText("hub")).toBeInTheDocument();
    });
  });

  // ── Enhanced: Change Count Badges ─────────────────────────────────

  it("shows change count badges in summary", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue(
      enhancedDiffData,
    );
    renderDiff();
    await waitFor(() => {
      expect(screen.getByText("+1")).toBeInTheDocument(); // added
    });
    expect(screen.getByText("−1")).toBeInTheDocument(); // removed
    expect(screen.getByText("~1")).toBeInTheDocument(); // modified
  });

  // ── Enhanced: Revert Button ───────────────────────────────────────

  it("shows revert button when onRestore provided", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue(
      enhancedDiffData,
    );
    renderDiff({ onRestore: vi.fn() });
    await waitFor(() => {
      expect(
        screen.getByTestId("revert-button"),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("Revert to v1")).toBeInTheDocument();
  });

  it("calls onRestore with fromVersion when revert clicked", async () => {
    const user = userEvent.setup();
    const onRestore = vi.fn();
    vi.mocked(api.architectureVersions.diff).mockResolvedValue(
      enhancedDiffData,
    );
    renderDiff({ onRestore });
    await waitFor(() => {
      expect(
        screen.getByTestId("revert-button"),
      ).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("revert-button"));
    expect(onRestore).toHaveBeenCalledWith(1);
  });

  it("does not show revert button without onRestore", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue(
      enhancedDiffData,
    );
    renderDiff();
    await waitFor(() => {
      expect(screen.getByText("Version Diff")).toBeInTheDocument();
    });
    expect(
      screen.queryByTestId("revert-button"),
    ).not.toBeInTheDocument();
  });

  // ── Enhanced: Inline mode shows change detail ─────────────────────

  it("shows component detail text in inline mode", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue(
      enhancedDiffData,
    );
    renderDiff();
    await waitFor(() => {
      expect(
        screen.getByText("Added compliance_frameworks"),
      ).toBeInTheDocument();
    });
  });
});
