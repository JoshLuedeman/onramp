import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import { MemoryRouter } from "react-router-dom";
import { vi, describe, it, expect, beforeEach } from "vitest";
import MarketplacePage from "./MarketplacePage";

vi.mock("../services/api", () => ({
  api: {
    templates: {
      list: vi.fn(),
      get: vi.fn(),
      create: vi.fn(),
      use: vi.fn(),
      rate: vi.fn(),
    },
  },
}));

import { api } from "../services/api";

const mockedApi = api as unknown as {
  templates: {
    list: ReturnType<typeof vi.fn>;
    get: ReturnType<typeof vi.fn>;
    create: ReturnType<typeof vi.fn>;
    use: ReturnType<typeof vi.fn>;
    rate: ReturnType<typeof vi.fn>;
  };
};

function renderMarketplace() {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>
        <MarketplacePage />
      </MemoryRouter>
    </FluentProvider>,
  );
}

const sampleTemplates = [
  {
    id: "t1",
    name: "Healthcare HIPAA",
    description: "HIPAA compliant template",
    industry: "Healthcare",
    tags: ["hipaa", "healthcare"],
    architecture_json: "{}",
    visibility: "curated",
    download_count: 42,
    rating_up: 10,
    rating_down: 2,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
  {
    id: "t2",
    name: "Financial PCI",
    description: "PCI-DSS compliant for finance",
    industry: "Financial Services",
    tags: ["pci", "sox"],
    architecture_json: "{}",
    visibility: "curated",
    download_count: 25,
    rating_up: 8,
    rating_down: 1,
    created_at: "2024-01-02T00:00:00Z",
    updated_at: "2024-01-02T00:00:00Z",
  },
  {
    id: "t3",
    name: "Startup Basic",
    description: "Cost optimized for startups",
    industry: "Startup",
    tags: ["startup", "cost-optimized"],
    architecture_json: "{}",
    visibility: "public",
    download_count: 100,
    rating_up: 30,
    rating_down: 5,
    created_at: "2024-01-03T00:00:00Z",
    updated_at: "2024-01-03T00:00:00Z",
  },
];

describe("MarketplacePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedApi.templates.list.mockResolvedValue({
      templates: sampleTemplates,
      total: 3,
      page: 1,
      page_size: 20,
    });
    mockedApi.templates.use.mockResolvedValue({});
    mockedApi.templates.rate.mockResolvedValue({});
  });

  it("shows loading spinner initially", () => {
    mockedApi.templates.list.mockReturnValue(new Promise(() => {}));
    renderMarketplace();
    expect(screen.getByText("Loading templates...")).toBeInTheDocument();
  });

  it("renders the page title", async () => {
    renderMarketplace();
    await waitFor(() => {
      expect(screen.getByText("Template Marketplace")).toBeInTheDocument();
    });
  });

  it("renders template cards after loading", async () => {
    renderMarketplace();
    await waitFor(() => {
      expect(screen.getByText("Healthcare HIPAA")).toBeInTheDocument();
      expect(screen.getByText("Financial PCI")).toBeInTheDocument();
      expect(screen.getByText("Startup Basic")).toBeInTheDocument();
    });
  });

  it("shows template descriptions", async () => {
    renderMarketplace();
    await waitFor(() => {
      expect(
        screen.getByText("HIPAA compliant template"),
      ).toBeInTheDocument();
    });
  });

  it("shows industry badges", async () => {
    renderMarketplace();
    await waitFor(() => {
      expect(screen.getByText("Healthcare")).toBeInTheDocument();
      expect(screen.getByText("Financial Services")).toBeInTheDocument();
    });
  });

  it("shows tag badges", async () => {
    renderMarketplace();
    await waitFor(() => {
      expect(screen.getByText("hipaa")).toBeInTheDocument();
      expect(screen.getByText("pci")).toBeInTheDocument();
    });
  });

  it("shows download counts", async () => {
    renderMarketplace();
    await waitFor(() => {
      expect(screen.getByText("42")).toBeInTheDocument();
      expect(screen.getByText("25")).toBeInTheDocument();
    });
  });

  it("shows rating counts", async () => {
    renderMarketplace();
    await waitFor(() => {
      expect(screen.getByText("10")).toBeInTheDocument();
      expect(screen.getByText("8")).toBeInTheDocument();
    });
  });

  it("shows Use Template buttons", async () => {
    renderMarketplace();
    await waitFor(() => {
      const buttons = screen.getAllByText("Use Template");
      expect(buttons).toHaveLength(3);
    });
  });

  it("shows empty state when no templates", async () => {
    mockedApi.templates.list.mockResolvedValue({
      templates: [],
      total: 0,
      page: 1,
      page_size: 20,
    });
    renderMarketplace();
    await waitFor(() => {
      expect(screen.getByText("No templates found")).toBeInTheDocument();
    });
  });

  it("shows empty state message", async () => {
    mockedApi.templates.list.mockResolvedValue({
      templates: [],
      total: 0,
      page: 1,
      page_size: 20,
    });
    renderMarketplace();
    await waitFor(() => {
      expect(
        screen.getByText("Try adjusting your search or filters"),
      ).toBeInTheDocument();
    });
  });

  it("filters by search text in name", async () => {
    const user = userEvent.setup();
    renderMarketplace();
    await waitFor(() => {
      expect(screen.getByText("Healthcare HIPAA")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("Search templates...");
    await user.type(searchInput, "Financial");

    expect(screen.getByText("Financial PCI")).toBeInTheDocument();
    expect(screen.queryByText("Healthcare HIPAA")).not.toBeInTheDocument();
  });

  it("filters by search text in description", async () => {
    const user = userEvent.setup();
    renderMarketplace();
    await waitFor(() => {
      expect(screen.getByText("Healthcare HIPAA")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("Search templates...");
    await user.type(searchInput, "cost optimized");

    expect(screen.getByText("Startup Basic")).toBeInTheDocument();
    expect(screen.queryByText("Healthcare HIPAA")).not.toBeInTheDocument();
  });

  it("filters by search text in tags", async () => {
    const user = userEvent.setup();
    renderMarketplace();
    await waitFor(() => {
      expect(screen.getByText("Healthcare HIPAA")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("Search templates...");
    await user.type(searchInput, "sox");

    expect(screen.getByText("Financial PCI")).toBeInTheDocument();
    expect(screen.queryByText("Healthcare HIPAA")).not.toBeInTheDocument();
  });

  it("calls use template API on button click", async () => {
    const user = userEvent.setup();
    renderMarketplace();
    await waitFor(() => {
      expect(screen.getByText("Healthcare HIPAA")).toBeInTheDocument();
    });

    const buttons = screen.getAllByText("Use Template");
    await user.click(buttons[0]);

    expect(mockedApi.templates.use).toHaveBeenCalledWith(
      "t1",
      "default-project",
    );
  });

  it("calls rate up API on thumbs up click", async () => {
    const user = userEvent.setup();
    renderMarketplace();
    await waitFor(() => {
      expect(screen.getByText("Healthcare HIPAA")).toBeInTheDocument();
    });

    const rateUpBtn = screen.getByLabelText("Rate Healthcare HIPAA up");
    await user.click(rateUpBtn);

    expect(mockedApi.templates.rate).toHaveBeenCalledWith("t1", "up");
  });

  it("calls rate down API on thumbs down click", async () => {
    const user = userEvent.setup();
    renderMarketplace();
    await waitFor(() => {
      expect(screen.getByText("Healthcare HIPAA")).toBeInTheDocument();
    });

    const rateDownBtn = screen.getByLabelText(
      "Rate Healthcare HIPAA down",
    );
    await user.click(rateDownBtn);

    expect(mockedApi.templates.rate).toHaveBeenCalledWith("t1", "down");
  });

  it("handles API error gracefully on load", async () => {
    mockedApi.templates.list.mockRejectedValue(new Error("Network error"));
    renderMarketplace();
    await waitFor(() => {
      expect(screen.getByText("No templates found")).toBeInTheDocument();
    });
  });

  it("handles API error on use template gracefully", async () => {
    const user = userEvent.setup();
    mockedApi.templates.use.mockRejectedValue(new Error("fail"));
    renderMarketplace();
    await waitFor(() => {
      expect(screen.getByText("Healthcare HIPAA")).toBeInTheDocument();
    });

    const buttons = screen.getAllByText("Use Template");
    await user.click(buttons[0]);

    // Page should still be functional after error
    await waitFor(() => {
      expect(screen.getByText("Healthcare HIPAA")).toBeInTheDocument();
    });
  });

  it("has search input with aria-label", () => {
    renderMarketplace();
    expect(screen.getByLabelText("Search templates")).toBeInTheDocument();
  });

  it("has industry dropdown with aria-label", () => {
    renderMarketplace();
    expect(
      screen.getByLabelText("Filter by industry"),
    ).toBeInTheDocument();
  });

  it("has visibility dropdown with aria-label", () => {
    renderMarketplace();
    expect(
      screen.getByLabelText("Filter by visibility"),
    ).toBeInTheDocument();
  });

  it("calls list API on mount", async () => {
    renderMarketplace();
    await waitFor(() => {
      expect(mockedApi.templates.list).toHaveBeenCalled();
    });
  });

  it("renders subtitle text", async () => {
    renderMarketplace();
    await waitFor(() => {
      expect(
        screen.getByText(
          /Browse and use curated architecture templates/,
        ),
      ).toBeInTheDocument();
    });
  });

  it("renders search icon in input", () => {
    renderMarketplace();
    expect(
      screen.getByPlaceholderText("Search templates..."),
    ).toBeInTheDocument();
  });

  it("shows all templates when search is cleared", async () => {
    const user = userEvent.setup();
    renderMarketplace();
    await waitFor(() => {
      expect(screen.getByText("Healthcare HIPAA")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("Search templates...");
    await user.type(searchInput, "Financial");
    expect(screen.queryByText("Healthcare HIPAA")).not.toBeInTheDocument();

    await user.clear(searchInput);
    expect(screen.getByText("Healthcare HIPAA")).toBeInTheDocument();
    expect(screen.getByText("Financial PCI")).toBeInTheDocument();
  });

  it("limits tags shown to 4", async () => {
    mockedApi.templates.list.mockResolvedValue({
      templates: [
        {
          ...sampleTemplates[0],
          tags: ["tag1", "tag2", "tag3", "tag4", "tag5"],
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    });
    renderMarketplace();
    await waitFor(() => {
      expect(screen.getByText("tag1")).toBeInTheDocument();
      expect(screen.getByText("tag4")).toBeInTheDocument();
      expect(screen.queryByText("tag5")).not.toBeInTheDocument();
    });
  });
});
