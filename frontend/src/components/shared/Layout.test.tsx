import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import Layout from "./Layout";
import { TUTORIAL_STORAGE_KEY } from "../../hooks/useTutorial";

// Mock useAuth used by AuthButton
vi.mock("../../auth", () => ({
  useAuth: () => ({
    isAuthenticated: false,
    user: null,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

const mockProjectsList = vi.fn();

vi.mock("../../services/api", () => ({
  api: {
    projects: {
      list: (...args: unknown[]) => mockProjectsList(...args),
    },
  },
}));

function createStorageMock(): Storage {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
    get length() {
      return Object.keys(store).length;
    },
    key: (index: number) => Object.keys(store)[index] ?? null,
  };
}

function renderLayout(children = <div>Test Content</div>, initialRoute = "/") {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter initialEntries={[initialRoute]}>
        <Layout>{children}</Layout>
      </MemoryRouter>
    </FluentProvider>
  );
}

describe("Layout", () => {
  let storageMock: Storage;

  beforeEach(() => {
    vi.clearAllMocks();
    mockProjectsList.mockResolvedValue({ projects: [] });
    // Provide a functional localStorage mock and mark tutorial as completed
    storageMock = createStorageMock();
    storageMock.setItem(TUTORIAL_STORAGE_KEY, "true");
    vi.stubGlobal("localStorage", storageMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders OnRamp title", () => {
    renderLayout();
    expect(screen.getByText("OnRamp", { exact: false })).toBeInTheDocument();
  });

  it("renders navigation tabs", () => {
    renderLayout();
    expect(screen.getByRole("tab", { name: /Home/ })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Wizard/ })).toBeInTheDocument();
  });

  it("renders children content", () => {
    renderLayout(<div>My Content</div>);
    expect(screen.getByText("My Content")).toBeInTheDocument();
  });

  it("has architecture tab", () => {
    renderLayout();
    expect(screen.getByRole("tab", { name: /Architecture/ })).toBeInTheDocument();
  });

  it("shows project switcher when projects exist", async () => {
    mockProjectsList.mockResolvedValue({
      projects: [
        { id: "p1", name: "Project Alpha", status: "draft", description: null, created_at: "2024-01-01", updated_at: "2024-01-01" },
      ],
    });
    renderLayout();
    await waitFor(() => {
      expect(screen.getByLabelText("Switch project")).toBeInTheDocument();
    });
  });

  it("hides project switcher when no projects", async () => {
    mockProjectsList.mockResolvedValue({ projects: [] });
    renderLayout();
    // Wait for the effect to settle
    await waitFor(() => {
      expect(mockProjectsList).toHaveBeenCalled();
    });
    expect(screen.queryByLabelText("Switch project")).not.toBeInTheDocument();
  });

  it("renders tutorial help button", () => {
    renderLayout();
    expect(
      screen.getByRole("button", { name: /start tutorial/i })
    ).toBeInTheDocument();
  });

  it("shows tutorial overlay when help button is clicked", async () => {
    // Tutorial is already marked as completed in beforeEach
    const user = userEvent.setup();
    renderLayout();

    // Tutorial should not be visible initially (already completed)
    expect(screen.queryByTestId("tutorial-overlay")).not.toBeInTheDocument();

    // Click the help button
    await user.click(
      screen.getByRole("button", { name: /start tutorial/i })
    );

    // Tutorial overlay should now be visible
    expect(screen.getByTestId("tutorial-overlay")).toBeInTheDocument();
  });
});
