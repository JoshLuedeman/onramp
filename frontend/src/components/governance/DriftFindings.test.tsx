import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";
import type { DriftFinding } from "../../services/api";

// ── Mocks ───────────────────────────────────────────────────────────────────

const mockRemediate = vi.fn().mockResolvedValue({ id: "rem-1", status: "completed" });
const mockRemediateBatch = vi.fn().mockResolvedValue({
  results: [],
  total: 0,
  succeeded: 0,
  failed: 0,
});

vi.mock("../../services/api", async () => {
  const actual = await vi.importActual("../../services/api");
  return {
    ...actual,
    api: {
      governance: {
        drift: {
          remediate: (...args: unknown[]) => mockRemediate(...args),
          remediateBatch: (...args: unknown[]) => mockRemediateBatch(...args),
          getRemediation: vi.fn(),
          getRemediationHistory: vi.fn(),
        },
      },
    },
  };
});

import DriftFindings from "./DriftFindings";

// ── Test data ───────────────────────────────────────────────────────────────

const mockFindings: DriftFinding[] = [
  {
    id: "evt-1",
    resource_type: "Microsoft.Compute/virtualMachines",
    resource_id: "/subscriptions/sub-1/resourceGroups/rg-1/providers/Microsoft.Compute/virtualMachines/vm-web-01",
    drift_type: "modified",
    expected_value: { sku: "Standard_B2s" },
    actual_value: { sku: "Standard_D4s_v5" },
    severity: "high",
    detected_at: "2025-07-27T10:00:00Z",
    resolved_at: null,
    resolution_type: null,
  },
  {
    id: "evt-2",
    resource_type: "Microsoft.Network/networkSecurityGroups",
    resource_id: "/subscriptions/sub-1/resourceGroups/rg-1/providers/Microsoft.Network/networkSecurityGroups/nsg-web",
    drift_type: "modified",
    expected_value: { rules: ["allow-https"] },
    actual_value: { rules: ["allow-https", "allow-ssh"] },
    severity: "critical",
    detected_at: "2025-07-27T10:01:00Z",
    resolved_at: null,
    resolution_type: null,
  },
  {
    id: "evt-3",
    resource_type: "Microsoft.Cache/Redis",
    resource_id: "/subscriptions/sub-1/resourceGroups/rg-1/providers/Microsoft.Cache/Redis/redis-cache",
    drift_type: "added",
    expected_value: null,
    actual_value: { sku: "Basic" },
    severity: "medium",
    detected_at: "2025-07-27T10:02:00Z",
    resolved_at: "2025-07-27T11:00:00Z",
    resolution_type: "accept",
  },
];

// ── Helper ──────────────────────────────────────────────────────────────────

function renderFindings(
  findings = mockFindings,
  onActionComplete?: () => void,
) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>
        <DriftFindings findings={findings} onActionComplete={onActionComplete} />
      </MemoryRouter>
    </FluentProvider>,
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("DriftFindings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without crashing", () => {
    const { container } = renderFindings();
    expect(container).toBeTruthy();
  });

  it("renders a table with the correct number of rows", () => {
    renderFindings();
    const table = screen.getByRole("table");
    // 3 data rows + 1 header row
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(4);
  });

  it("displays resource names from resource IDs", () => {
    renderFindings();
    expect(screen.getByText("vm-web-01")).toBeInTheDocument();
    expect(screen.getByText("nsg-web")).toBeInTheDocument();
    expect(screen.getByText("redis-cache")).toBeInTheDocument();
  });

  it("displays severity badges", () => {
    renderFindings();
    expect(screen.getByText("High")).toBeInTheDocument();
    expect(screen.getByText("Critical")).toBeInTheDocument();
    expect(screen.getByText("Medium")).toBeInTheDocument();
  });

  it("displays status labels", () => {
    renderFindings();
    const activeLabels = screen.getAllByText("Active");
    expect(activeLabels).toHaveLength(2);
    expect(screen.getByText("Resolved (accept)")).toBeInTheDocument();
  });

  it("shows Accept, Revert, Suppress buttons per finding", () => {
    renderFindings();
    const acceptButtons = screen.getAllByRole("button", { name: "Accept" });
    const revertButtons = screen.getAllByRole("button", { name: "Revert" });
    const suppressButtons = screen.getAllByRole("button", { name: "Suppress" });
    expect(acceptButtons).toHaveLength(3);
    expect(revertButtons).toHaveLength(3);
    expect(suppressButtons).toHaveLength(3);
  });

  it("disables action buttons for resolved findings", () => {
    renderFindings();
    // evt-3 is resolved; its buttons should be disabled
    const table = screen.getByRole("table");
    const rows = within(table).getAllByRole("row");
    // Row index 3 is the resolved finding (0=header, 1=evt-1, 2=evt-2, 3=evt-3)
    const resolvedRow = rows[3];
    const buttons = within(resolvedRow).getAllByRole("button");
    // All action buttons in this row should be disabled
    // (checkbox is not a button, so we filter to buttons with known names)
    const actionButtons = buttons.filter((b) =>
      ["Accept", "Revert", "Suppress"].includes(b.getAttribute("aria-label") ?? ""),
    );
    actionButtons.forEach((btn) => expect(btn).toBeDisabled());
  });

  it("calls remediate API when Accept button is clicked", async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    renderFindings(mockFindings, onComplete);

    const acceptButtons = screen.getAllByRole("button", { name: "Accept" });
    await user.click(acceptButtons[0]);

    expect(mockRemediate).toHaveBeenCalledWith({
      finding_id: "evt-1",
      action: "accept",
    });
    expect(onComplete).toHaveBeenCalled();
  });

  it("calls remediate API when Revert button is clicked", async () => {
    const user = userEvent.setup();
    renderFindings();

    const revertButtons = screen.getAllByRole("button", { name: "Revert" });
    await user.click(revertButtons[0]);

    expect(mockRemediate).toHaveBeenCalledWith({
      finding_id: "evt-1",
      action: "revert",
    });
  });

  // ── Batch selection ───────────────────────────────────────────────────

  it("shows batch toolbar when items are selected", async () => {
    const user = userEvent.setup();
    renderFindings();

    // No toolbar initially
    expect(screen.queryByText("Accept Selected")).not.toBeInTheDocument();

    // Click the first row checkbox (skip the "select all" checkbox)
    const checkboxes = screen.getAllByRole("checkbox");
    await user.click(checkboxes[1]); // first row checkbox

    expect(screen.getByText("Accept Selected")).toBeInTheDocument();
    expect(screen.getByText("Revert Selected")).toBeInTheDocument();
    expect(screen.getByText("Suppress Selected")).toBeInTheDocument();
    expect(screen.getByText(/1 of 3 selected/)).toBeInTheDocument();
  });

  it("select all checkbox toggles all findings", async () => {
    const user = userEvent.setup();
    renderFindings();

    const selectAll = screen.getAllByRole("checkbox")[0];
    await user.click(selectAll);

    expect(screen.getByText(/3 of 3 selected/)).toBeInTheDocument();

    // Click again to deselect all
    await user.click(selectAll);
    expect(screen.queryByText("Accept Selected")).not.toBeInTheDocument();
  });

  it("calls batch remediate API when Accept Selected is clicked", async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    renderFindings(mockFindings, onComplete);

    // Select all
    const selectAll = screen.getAllByRole("checkbox")[0];
    await user.click(selectAll);

    await user.click(screen.getByText("Accept Selected"));

    expect(mockRemediateBatch).toHaveBeenCalledWith({
      finding_ids: ["evt-1", "evt-2", "evt-3"],
      action: "accept",
    });
    expect(onComplete).toHaveBeenCalled();
  });

  // ── Suppress modal ───────────────────────────────────────────────────

  it("opens suppress dialog when Suppress button is clicked", async () => {
    const user = userEvent.setup();
    renderFindings();

    const suppressButtons = screen.getAllByRole("button", { name: "Suppress" });
    await user.click(suppressButtons[0]);

    expect(screen.getByText("Suppress Drift Finding")).toBeInTheDocument();
    expect(screen.getByTestId("suppress-justification")).toBeInTheDocument();
    expect(screen.getByTestId("suppress-confirm")).toBeInTheDocument();
  });

  it("submits suppress with justification and expiration", async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    renderFindings(mockFindings, onComplete);

    // Open suppress dialog for first finding
    const suppressButtons = screen.getAllByRole("button", { name: "Suppress" });
    await user.click(suppressButtons[0]);

    // Type justification using fireEvent to avoid Fluent UI keyboard interception
    const textarea = screen.getByPlaceholderText("Explain why this drift is intentional...");
    expect(textarea).toBeTruthy();
    fireEvent.change(textarea, { target: { value: "Planned change" } });

    // Click confirm
    await user.click(screen.getByTestId("suppress-confirm"));

    expect(mockRemediate).toHaveBeenCalledWith({
      finding_id: "evt-1",
      action: "suppress",
      justification: "Planned change",
      expiration_days: 30,
    });
    expect(onComplete).toHaveBeenCalled();
  });

  it("renders empty state without errors", () => {
    renderFindings([]);
    const table = screen.getByRole("table");
    const rows = within(table).getAllByRole("row");
    // Only header row
    expect(rows).toHaveLength(1);
  });

  it("shows low severity badge", () => {
    const lowFinding: DriftFinding = {
      ...mockFindings[0],
      id: "evt-low",
      severity: "low",
    };
    renderFindings([lowFinding]);
    expect(screen.getByText("Low")).toBeInTheDocument();
  });
});
