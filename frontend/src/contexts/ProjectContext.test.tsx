import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { ProjectProvider, useProject } from "./ProjectContext";

const mockGet = vi.fn();
const mockUpdate = vi.fn();

vi.mock("../services/api", () => ({
  api: {
    projects: {
      get: (...args: unknown[]) => mockGet(...args),
      update: (...args: unknown[]) => mockUpdate(...args),
    },
  },
}));

let mockProjectId: string | undefined;
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useParams: () => ({ projectId: mockProjectId }),
  };
});

function TestConsumer() {
  const { project, loading, error } = useProject();
  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (project) return <div>Project: {project.name}</div>;
  return <div>No project</div>;
}

function renderWithProvider() {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <ProjectProvider>
        <TestConsumer />
      </ProjectProvider>
    </FluentProvider>,
  );
}

describe("ProjectContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockProjectId = undefined;
  });

  it("loads project when projectId is present", async () => {
    mockProjectId = "proj-1";
    mockGet.mockResolvedValue({
      id: "proj-1",
      name: "Test Project",
      description: null,
      status: "draft",
      created_at: "2024-01-01",
      updated_at: "2024-01-01",
    });

    renderWithProvider();
    expect(screen.getByText("Loading...")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Project: Test Project")).toBeInTheDocument();
    });
    expect(mockGet).toHaveBeenCalledWith("proj-1");
  });

  it("shows error when project load fails", async () => {
    mockProjectId = "bad-id";
    mockGet.mockRejectedValue(new Error("Not found"));

    renderWithProvider();
    await waitFor(() => {
      expect(screen.getByText("Error: Not found")).toBeInTheDocument();
    });
  });

  it("does not load when no projectId", async () => {
    mockProjectId = undefined;
    renderWithProvider();
    // Should stay in loading state since refresh returns early
    await waitFor(() => {
      expect(mockGet).not.toHaveBeenCalled();
    });
  });

  it("throws when useProject is used outside provider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() =>
      render(
        <FluentProvider theme={teamsLightTheme}>
          <TestConsumer />
        </FluentProvider>,
      ),
    ).toThrow("useProject must be used within ProjectProvider");
    spy.mockRestore();
  });
});
