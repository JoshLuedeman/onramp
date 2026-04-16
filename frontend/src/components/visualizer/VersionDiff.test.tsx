import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
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
      from_version: 1,
      to_version: 2,
      added_components: [],
      removed_components: [],
      modified_components: [],
      summary: "No changes detected",
    });
    renderDiff();
    await waitFor(() => {
      expect(screen.getByText("v1")).toBeInTheDocument();
    });
    expect(screen.getByText("v2")).toBeInTheDocument();
  });

  it("renders summary text", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue({
      from_version: 1,
      to_version: 2,
      added_components: [{ name: "policies", detail: "Added policies" }],
      removed_components: [],
      modified_components: [],
      summary: "1 component(s) added",
    });
    renderDiff();
    await waitFor(() => {
      expect(screen.getByText("1 component(s) added")).toBeInTheDocument();
    });
  });

  it("renders added components with green styling", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue({
      from_version: 1,
      to_version: 2,
      added_components: [
        { name: "compliance_frameworks", detail: "Added compliance_frameworks" },
      ],
      removed_components: [],
      modified_components: [],
      summary: "1 component(s) added",
    });
    renderDiff();
    await waitFor(() => {
      expect(screen.getByText("compliance_frameworks")).toBeInTheDocument();
    });
    expect(screen.getByText("Added")).toBeInTheDocument();
  });

  it("renders removed components", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue({
      from_version: 1,
      to_version: 2,
      added_components: [],
      removed_components: [
        { name: "subscriptions", detail: "Removed subscriptions" },
      ],
      modified_components: [],
      summary: "1 component(s) removed",
    });
    renderDiff();
    await waitFor(() => {
      expect(screen.getByText("subscriptions")).toBeInTheDocument();
    });
    expect(screen.getByText("Removed")).toBeInTheDocument();
  });

  it("renders modified components", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue({
      from_version: 1,
      to_version: 2,
      added_components: [],
      removed_components: [],
      modified_components: [
        { name: "network_topology", detail: "network_topology: 1 key(s) added" },
      ],
      summary: "1 component(s) modified",
    });
    renderDiff();
    await waitFor(() => {
      expect(screen.getByText("network_topology")).toBeInTheDocument();
    });
    expect(screen.getByText("Modified")).toBeInTheDocument();
  });

  it("renders all change types together", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue({
      from_version: 1,
      to_version: 3,
      added_components: [
        { name: "compliance_frameworks", detail: "Added compliance_frameworks" },
      ],
      removed_components: [
        { name: "policies", detail: "Removed policies" },
      ],
      modified_components: [
        { name: "subscriptions", detail: "subscriptions: 1 item(s) added" },
      ],
      summary: "1 component(s) added; 1 component(s) removed; 1 component(s) modified",
    });
    renderDiff();
    await waitFor(() => {
      expect(screen.getByText("Added")).toBeInTheDocument();
    });
    expect(screen.getByText("Removed")).toBeInTheDocument();
    expect(screen.getByText("Modified")).toBeInTheDocument();
  });

  it("shows empty state when no differences", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue({
      from_version: 1,
      to_version: 1,
      added_components: [],
      removed_components: [],
      modified_components: [],
      summary: "No changes detected",
    });
    renderDiff();
    await waitFor(() => {
      expect(
        screen.getByText(/no differences found/i),
      ).toBeInTheDocument();
    });
  });

  it("displays count badges for each section", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue({
      from_version: 1,
      to_version: 2,
      added_components: [
        { name: "a", detail: "" },
        { name: "b", detail: "" },
      ],
      removed_components: [{ name: "c", detail: "" }],
      modified_components: [
        { name: "d", detail: "" },
        { name: "e", detail: "" },
        { name: "f", detail: "" },
      ],
      summary: "2 added; 1 removed; 3 modified",
    });
    renderDiff();
    await waitFor(() => {
      expect(screen.getByText("2")).toBeInTheDocument(); // added count
    });
    expect(screen.getByText("1")).toBeInTheDocument(); // removed count
    expect(screen.getByText("3")).toBeInTheDocument(); // modified count
  });

  it("renders 'Version Diff' heading", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue({
      from_version: 1,
      to_version: 2,
      added_components: [],
      removed_components: [],
      modified_components: [],
      summary: "No changes detected",
    });
    renderDiff();
    await waitFor(() => {
      expect(screen.getByText("Version Diff")).toBeInTheDocument();
    });
  });

  it("shows detail text for components", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue({
      from_version: 1,
      to_version: 2,
      added_components: [
        { name: "policies", detail: "Added policies" },
      ],
      removed_components: [],
      modified_components: [],
      summary: "1 component(s) added",
    });
    renderDiff();
    await waitFor(() => {
      expect(screen.getByText("Added policies")).toBeInTheDocument();
    });
  });

  it("has accessible container label", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue({
      from_version: 1,
      to_version: 2,
      added_components: [],
      removed_components: [],
      modified_components: [],
      summary: "No changes detected",
    });
    renderDiff();
    await waitFor(() => {
      expect(screen.getByLabelText("Version diff")).toBeInTheDocument();
    });
  });

  it("calls API with correct params", async () => {
    vi.mocked(api.architectureVersions.diff).mockResolvedValue({
      from_version: 5,
      to_version: 8,
      added_components: [],
      removed_components: [],
      modified_components: [],
      summary: "No changes detected",
    });
    renderDiff({ architectureId: "my-arch", fromVersion: 5, toVersion: 8 });
    await waitFor(() => {
      expect(api.architectureVersions.diff).toHaveBeenCalledWith("my-arch", 5, 8);
    });
  });
});
