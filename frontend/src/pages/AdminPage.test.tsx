import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";
import { vi, describe, it, expect, beforeEach } from "vitest";

import AdminPage from "./AdminPage";

vi.mock("../services/api", () => ({
  api: {
    plugins: {
      list: vi.fn(),
      get: vi.fn(),
    },
  },
}));

import { api } from "../services/api";

const mockedApi = api as unknown as {
  plugins: {
    list: ReturnType<typeof vi.fn>;
    get: ReturnType<typeof vi.fn>;
  };
};

function renderPage() {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>
        <AdminPage />
      </MemoryRouter>
    </FluentProvider>,
  );
}

const samplePlugins = [
  {
    name: "CIS Azure Benchmark",
    version: "1.0.0",
    plugin_type: "compliance",
    description: "CIS Microsoft Azure Foundations Benchmark v2.0 (sample subset)",
    enabled: true,
  },
  {
    name: "Custom Archetype",
    version: "0.5.0",
    plugin_type: "architecture",
    description: "Custom architecture pattern for fintech",
    enabled: true,
  },
  {
    name: "Terraform Output",
    version: "2.0.0",
    plugin_type: "output",
    description: "Generate Terraform HCL output",
    enabled: false,
  },
];

beforeEach(() => {
  vi.resetAllMocks();
});

describe("AdminPage", () => {
  it("shows loading spinner initially", () => {
    mockedApi.plugins.list.mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText("Loading plugins...")).toBeInTheDocument();
  });

  it("renders empty state when no plugins are installed", async () => {
    mockedApi.plugins.list.mockResolvedValue({ plugins: [], total: 0 });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("No plugins installed")).toBeInTheDocument();
    });
    expect(
      screen.getByText(/Install plugins to extend OnRamp/),
    ).toBeInTheDocument();
  });

  it("renders plugin list from API", async () => {
    mockedApi.plugins.list.mockResolvedValue({
      plugins: samplePlugins,
      total: 3,
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("CIS Azure Benchmark")).toBeInTheDocument();
    });
    expect(screen.getByText("Custom Archetype")).toBeInTheDocument();
    expect(screen.getByText("Terraform Output")).toBeInTheDocument();
    expect(screen.getByText("1.0.0")).toBeInTheDocument();
    expect(screen.getByText("Compliance")).toBeInTheDocument();
    expect(screen.getByText("Architecture")).toBeInTheDocument();
    expect(screen.getByText("Output Format")).toBeInTheDocument();
  });

  it("fetches plugins from the API on mount", async () => {
    mockedApi.plugins.list.mockResolvedValue({ plugins: [], total: 0 });
    renderPage();
    await waitFor(() => {
      expect(mockedApi.plugins.list).toHaveBeenCalledTimes(1);
    });
  });

  it("shows enabled/disabled status badges", async () => {
    mockedApi.plugins.list.mockResolvedValue({
      plugins: samplePlugins,
      total: 3,
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("CIS Azure Benchmark")).toBeInTheDocument();
    });
    const enabledBadges = screen.getAllByText("Enabled");
    const disabledBadges = screen.getAllByText("Disabled");
    expect(enabledBadges.length).toBe(2);
    expect(disabledBadges.length).toBe(1);
  });

  it("refreshes plugin list when Refresh is clicked", async () => {
    const user = userEvent.setup();
    mockedApi.plugins.list.mockResolvedValue({
      plugins: samplePlugins,
      total: 3,
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("CIS Azure Benchmark")).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: /refresh/i }));
    await waitFor(() => {
      expect(mockedApi.plugins.list).toHaveBeenCalledTimes(2);
    });
  });

  it("shows error message when API call fails", async () => {
    mockedApi.plugins.list.mockRejectedValue(new Error("Network error"));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });
});
