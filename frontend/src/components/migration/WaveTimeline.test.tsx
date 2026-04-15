import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";
import WaveTimeline from "./WaveTimeline";
import type { WaveResponse, ValidationWarning } from "../../services/api";

const MOCK_WAVES: WaveResponse[] = [
  {
    id: "wave-1",
    name: "Wave 1",
    order: 0,
    status: "planned",
    notes: null,
    workloads: [
      {
        id: "ww-1",
        workload_id: "wl-1",
        name: "Frontend App",
        type: "web-app",
        criticality: "standard",
        migration_strategy: "rehost",
        position: 0,
        dependencies: [],
      },
      {
        id: "ww-2",
        workload_id: "wl-2",
        name: "Cache Server",
        type: "container",
        criticality: "dev-test",
        migration_strategy: "rehost",
        position: 1,
        dependencies: [],
      },
    ],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "wave-2",
    name: "Wave 2",
    order: 1,
    status: "in_progress",
    notes: null,
    workloads: [
      {
        id: "ww-3",
        workload_id: "wl-3",
        name: "Database",
        type: "database",
        criticality: "mission-critical",
        migration_strategy: "refactor",
        position: 0,
        dependencies: ["wl-1"],
      },
    ],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
];

const MOCK_WARNINGS: ValidationWarning[] = [
  {
    type: "dependency_violation",
    message: "'Database' depends on 'Frontend App' in a later wave",
    wave_id: "wave-2",
    workload_id: "wl-3",
  },
];

function renderTimeline(
  props: Partial<React.ComponentProps<typeof WaveTimeline>> = {},
) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>
        <WaveTimeline
          waves={MOCK_WAVES}
          warnings={[]}
          {...props}
        />
      </MemoryRouter>
    </FluentProvider>,
  );
}

describe("WaveTimeline", () => {
  it("renders waves with workloads", () => {
    renderTimeline();
    expect(screen.getByText("Wave 1")).toBeInTheDocument();
    expect(screen.getByText("Wave 2")).toBeInTheDocument();
    expect(screen.getByText("Frontend App")).toBeInTheDocument();
    expect(screen.getByText("Cache Server")).toBeInTheDocument();
    expect(screen.getByText("Database")).toBeInTheDocument();
  });

  it("shows workload count per wave", () => {
    renderTimeline();
    expect(screen.getByText("2 workloads")).toBeInTheDocument();
    expect(screen.getByText("1 workloads")).toBeInTheDocument();
  });

  it("shows status badges", () => {
    renderTimeline();
    expect(screen.getByText("planned")).toBeInTheDocument();
    expect(screen.getByText("in_progress")).toBeInTheDocument();
  });

  it("shows criticality badges", () => {
    renderTimeline();
    expect(screen.getByText("standard")).toBeInTheDocument();
    expect(screen.getByText("dev-test")).toBeInTheDocument();
    expect(screen.getByText("mission-critical")).toBeInTheDocument();
  });

  it("shows strategy badges", () => {
    renderTimeline();
    expect(screen.getAllByText("rehost")).toHaveLength(2);
    expect(screen.getByText("refactor")).toBeInTheDocument();
  });

  it("renders empty state when no waves", () => {
    renderTimeline({ waves: [] });
    expect(screen.getByTestId("wave-empty")).toBeInTheDocument();
    expect(screen.getByText(/No waves generated/)).toBeInTheDocument();
  });

  it("renders move up/down buttons", () => {
    renderTimeline();
    expect(screen.getByLabelText("Move Frontend App up")).toBeInTheDocument();
    expect(screen.getByLabelText("Move Frontend App down")).toBeInTheDocument();
    expect(screen.getByLabelText("Move Cache Server up")).toBeInTheDocument();
    expect(screen.getByLabelText("Move Cache Server down")).toBeInTheDocument();
  });

  it("disables move up for first item", () => {
    renderTimeline();
    const moveUpBtn = screen.getByLabelText("Move Frontend App up");
    expect(moveUpBtn).toBeDisabled();
  });

  it("disables move down for last item", () => {
    renderTimeline();
    const moveDownBtn = screen.getByLabelText("Move Cache Server down");
    expect(moveDownBtn).toBeDisabled();
  });

  it("calls onReorder when move buttons clicked", async () => {
    const user = userEvent.setup();
    const onReorder = vi.fn();
    renderTimeline({ onReorder });

    const moveDownBtn = screen.getByLabelText("Move Frontend App down");
    await user.click(moveDownBtn);
    expect(onReorder).toHaveBeenCalledWith("wave-1", "wl-1", "down");
  });

  it("displays dependency warnings", () => {
    renderTimeline({ warnings: MOCK_WARNINGS });
    expect(screen.getByTestId("wave-warnings")).toBeInTheDocument();
    expect(
      screen.getAllByText(/Database.*depends on.*Frontend App/).length,
    ).toBeGreaterThanOrEqual(1);
  });

  it("shows no warnings section when empty", () => {
    renderTimeline({ warnings: [] });
    expect(screen.queryByTestId("wave-warnings")).not.toBeInTheDocument();
  });

  it("workload cards are draggable", () => {
    renderTimeline();
    const card = screen.getByTestId("workload-card-wl-1");
    expect(card).toHaveAttribute("draggable", "true");
  });
});
