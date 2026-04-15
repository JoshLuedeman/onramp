import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import ADRPanel from "./ADRPanel";
import type { ADRRecord } from "../../services/api";

const mockAdrs: ADRRecord[] = [
  {
    id: "ADR-001",
    title: "Management Group Hierarchy",
    status: "Accepted",
    context: "Need a management group hierarchy.",
    decision: "Use CAF-aligned hierarchy.",
    consequences: "Policies cascade down.",
    category: "governance",
    created_at: "2025-01-01",
  },
  {
    id: "ADR-002",
    title: "Network Topology",
    status: "Accepted",
    context: "Need network connectivity.",
    decision: "Use hub-spoke topology.",
    consequences: "Traffic routes through hub.",
    category: "networking",
    created_at: "2025-01-01",
  },
  {
    id: "ADR-003",
    title: "Identity Model",
    status: "Accepted",
    context: "Need identity strategy.",
    decision: "Use centralized Entra ID.",
    consequences: "Single audit trail.",
    category: "identity",
    created_at: "2025-01-01",
  },
];

const mockGenerateAdrs = vi.fn();
const mockExportAdrs = vi.fn();

vi.mock("../../services/api", () => ({
  api: {
    architecture: {
      generateAdrs: (...args: unknown[]) => mockGenerateAdrs(...args),
      exportAdrs: (...args: unknown[]) => mockExportAdrs(...args),
    },
  },
}));

const defaultProps = {
  architecture: { management_groups: {}, subscriptions: [] },
  answers: { org_size: "small" },
  projectId: "proj-1",
};

function renderPanel(props = defaultProps) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <ADRPanel {...props} />
    </FluentProvider>,
  );
}

describe("ADRPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGenerateAdrs.mockResolvedValue({ adrs: mockAdrs, project_id: "proj-1" });
    mockExportAdrs.mockResolvedValue({ content: "# ADRs\n\nContent here" });
  });

  it("renders with no ADRs and shows generate button", () => {
    renderPanel();

    expect(screen.getByText("Generate ADRs")).toBeInTheDocument();
    expect(
      screen.getByText(/No ADRs generated yet/),
    ).toBeInTheDocument();
  });

  it("does not show export button when no ADRs exist", () => {
    renderPanel();

    expect(screen.queryByText("Export All")).not.toBeInTheDocument();
  });

  it("generates ADRs when button is clicked", async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.click(screen.getByText("Generate ADRs"));

    await waitFor(() => {
      expect(mockGenerateAdrs).toHaveBeenCalledWith(
        defaultProps.architecture,
        defaultProps.answers,
        false,
        defaultProps.projectId,
      );
    });

    await waitFor(() => {
      expect(screen.getByText("Management Group Hierarchy")).toBeInTheDocument();
      expect(screen.getByText("Network Topology")).toBeInTheDocument();
      expect(screen.getByText("Identity Model")).toBeInTheDocument();
    });
  });

  it("renders ADR list with titles and category badges", async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.click(screen.getByText("Generate ADRs"));

    await waitFor(() => {
      expect(screen.getByText("ADR-001")).toBeInTheDocument();
      expect(screen.getByText("ADR-002")).toBeInTheDocument();
      expect(screen.getByText("governance")).toBeInTheDocument();
      expect(screen.getByText("networking")).toBeInTheDocument();
    });
  });

  it("expands an ADR to show details", async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.click(screen.getByText("Generate ADRs"));

    await waitFor(() => {
      expect(screen.getByText("Management Group Hierarchy")).toBeInTheDocument();
    });

    // Click the accordion header to expand
    await user.click(screen.getByText("Management Group Hierarchy"));

    await waitFor(() => {
      expect(screen.getByText("Need a management group hierarchy.")).toBeInTheDocument();
      expect(screen.getByText("Use CAF-aligned hierarchy.")).toBeInTheDocument();
      expect(screen.getByText("Policies cascade down.")).toBeInTheDocument();
    });
  });

  it("shows export button after ADRs are generated", async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.click(screen.getByText("Generate ADRs"));

    await waitFor(() => {
      expect(screen.getByText("Export All")).toBeInTheDocument();
    });
  });

  it("calls export API when Export All is clicked", async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.click(screen.getByText("Generate ADRs"));

    await waitFor(() => {
      expect(screen.getByText("Export All")).toBeInTheDocument();
    });

    await user.click(screen.getByText("Export All"));

    await waitFor(() => {
      expect(mockExportAdrs).toHaveBeenCalledWith(mockAdrs, "combined");
    });
  });

  it("shows error message when generation fails", async () => {
    mockGenerateAdrs.mockRejectedValueOnce(new Error("Network error"));
    const user = userEvent.setup();
    renderPanel();

    await user.click(screen.getByText("Generate ADRs"));

    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });

  it("shows regenerate button after ADRs exist", async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.click(screen.getByText("Generate ADRs"));

    await waitFor(() => {
      expect(screen.getByText("Regenerate ADRs")).toBeInTheDocument();
    });
  });
});
