import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import MigrationPage from "./MigrationPage";
import type { WavePlanResponse } from "../services/api";

const MOCK_EMPTY_PLAN: WavePlanResponse = {
  id: "plan-1",
  project_id: "proj-1",
  name: "Migration Plan",
  strategy: "complexity_first",
  is_active: true,
  waves: [],
  warnings: [],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const MOCK_PLAN_WITH_WAVES: WavePlanResponse = {
  id: "plan-1",
  project_id: "proj-1",
  name: "Migration Plan",
  strategy: "complexity_first",
  is_active: true,
  waves: [
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
          name: "App Server",
          type: "vm",
          criticality: "standard",
          migration_strategy: "rehost",
          position: 0,
          dependencies: [],
        },
      ],
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ],
  warnings: [],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

vi.mock("../services/api", () => ({
  api: {
    migration: {
      getWaves: vi.fn(),
      generateWaves: vi.fn(),
      moveWorkload: vi.fn(),
      validatePlan: vi.fn(),
      exportPlan: vi.fn(),
      deleteWave: vi.fn(),
    },
  },
}));

const { api } = await import("../services/api");
const mockedApi = vi.mocked(api.migration);

function renderPage() {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter initialEntries={["/projects/proj-1/migration"]}>
        <Routes>
          <Route
            path="/projects/:projectId/migration"
            element={<MigrationPage />}
          />
        </Routes>
      </MemoryRouter>
    </FluentProvider>,
  );
}

describe("MigrationPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedApi.getWaves.mockResolvedValue(MOCK_EMPTY_PLAN);
    mockedApi.generateWaves.mockResolvedValue(MOCK_PLAN_WITH_WAVES);
    mockedApi.validatePlan.mockResolvedValue({
      ...MOCK_PLAN_WITH_WAVES,
      warnings: [
        {
          type: "dependency_violation",
          message: "Test warning message",
          wave_id: null,
          workload_id: null,
        },
      ],
    });
    mockedApi.exportPlan.mockResolvedValue(new Blob(["test"]));
  });

  it("renders page with generate button", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Migration Wave Planner")).toBeInTheDocument();
    });
    expect(screen.getByTestId("generate-btn")).toBeInTheDocument();
    expect(screen.getByText("Generate Waves")).toBeInTheDocument();
  });

  it("loads existing plan on mount", async () => {
    renderPage();
    await waitFor(() => {
      expect(mockedApi.getWaves).toHaveBeenCalledWith("proj-1");
    });
  });

  it("generates waves when button clicked", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("generate-btn")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("generate-btn"));

    await waitFor(() => {
      expect(mockedApi.generateWaves).toHaveBeenCalledWith(
        expect.objectContaining({
          project_id: "proj-1",
          strategy: "complexity_first",
        }),
      );
    });
  });

  it("shows waves after generation", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("generate-btn")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("generate-btn"));

    await waitFor(() => {
      expect(screen.getByText("Wave 1")).toBeInTheDocument();
      expect(screen.getByText("App Server")).toBeInTheDocument();
    });
  });

  it("shows export buttons after waves are generated", async () => {
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("generate-btn")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("generate-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("export-csv-btn")).toBeInTheDocument();
      expect(screen.getByTestId("export-md-btn")).toBeInTheDocument();
    });
  });

  it("shows empty state when no waves", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("wave-empty")).toBeInTheDocument();
    });
  });

  it("handles API error gracefully", async () => {
    mockedApi.getWaves.mockRejectedValue(new Error("Network error"));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });
});
