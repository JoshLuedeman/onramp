import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import ProjectDetailPage from "./ProjectDetailPage";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate, useParams: () => ({}) };
});

let mockProjectCtx = {
  project: null as null | {
    id: string;
    name: string;
    description: string | null;
    status: string;
    created_at: string;
    updated_at: string;
  },
  loading: false,
  error: null as string | null,
  refresh: vi.fn(),
  updateStatus: vi.fn(),
};

vi.mock("../contexts/ProjectContext", () => ({
  useProject: () => mockProjectCtx,
}));

function renderPage() {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <ProjectDetailPage />
    </FluentProvider>,
  );
}

describe("ProjectDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockProjectCtx = {
      project: null,
      loading: false,
      error: null,
      refresh: vi.fn(),
      updateStatus: vi.fn(),
    };
  });

  it("shows spinner when loading", () => {
    mockProjectCtx.loading = true;
    renderPage();
    expect(screen.getByText("Loading project...")).toBeInTheDocument();
  });

  it("shows error when project not found", () => {
    mockProjectCtx.error = "Not found";
    renderPage();
    expect(screen.getByText("Project Not Found")).toBeInTheDocument();
    expect(screen.getByText("Not found")).toBeInTheDocument();
  });

  it("shows back to dashboard button on error", () => {
    mockProjectCtx.error = "Not found";
    renderPage();
    expect(screen.getByRole("button", { name: /back to dashboard/i })).toBeInTheDocument();
  });

  it("renders project name and status", () => {
    mockProjectCtx.project = {
      id: "p1",
      name: "My Landing Zone",
      description: null,
      status: "draft",
      created_at: "2024-01-01",
      updated_at: "2024-01-01",
    };
    renderPage();
    expect(screen.getByText("My Landing Zone")).toBeInTheDocument();
    expect(screen.getByText("Draft")).toBeInTheDocument();
  });

  it("renders all five steps", () => {
    mockProjectCtx.project = {
      id: "p1",
      name: "Test",
      description: null,
      status: "draft",
      created_at: "2024-01-01",
      updated_at: "2024-01-01",
    };
    renderPage();
    expect(screen.getByText("Questionnaire")).toBeInTheDocument();
    expect(screen.getByText("Architecture")).toBeInTheDocument();
    expect(screen.getByText("Compliance")).toBeInTheDocument();
    expect(screen.getByText("Bicep Preview")).toBeInTheDocument();
    expect(screen.getByText("Deploy")).toBeInTheDocument();
  });

  it("shows continue button for current step", () => {
    mockProjectCtx.project = {
      id: "p1",
      name: "Test",
      description: null,
      status: "draft",
      created_at: "2024-01-01",
      updated_at: "2024-01-01",
    };
    renderPage();
    expect(screen.getByRole("button", { name: /continue/i })).toBeInTheDocument();
  });

  it("shows locked buttons for future steps", () => {
    mockProjectCtx.project = {
      id: "p1",
      name: "Test",
      description: null,
      status: "draft",
      created_at: "2024-01-01",
      updated_at: "2024-01-01",
    };
    renderPage();
    const lockedButtons = screen.getAllByRole("button", { name: /locked/i });
    expect(lockedButtons.length).toBeGreaterThan(0);
    lockedButtons.forEach((btn) => expect(btn).toBeDisabled());
  });

  it("renders description when present", () => {
    mockProjectCtx.project = {
      id: "p1",
      name: "Test",
      description: "A test landing zone project",
      status: "draft",
      created_at: "2024-01-01",
      updated_at: "2024-01-01",
    };
    renderPage();
    expect(screen.getByText("A test landing zone project")).toBeInTheDocument();
  });

  it("shows review buttons for completed steps", () => {
    mockProjectCtx.project = {
      id: "p1",
      name: "Test",
      description: null,
      status: "architecture_generated",
      created_at: "2024-01-01",
      updated_at: "2024-01-01",
    };
    renderPage();
    const reviewButtons = screen.getAllByRole("button", { name: /review/i });
    expect(reviewButtons.length).toBeGreaterThanOrEqual(2);
  });

  it("renders back to dashboard link", () => {
    mockProjectCtx.project = {
      id: "p1",
      name: "Test",
      description: null,
      status: "draft",
      created_at: "2024-01-01",
      updated_at: "2024-01-01",
    };
    renderPage();
    expect(screen.getByRole("button", { name: /back to dashboard/i })).toBeInTheDocument();
  });
});
