import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import ArchitecturePage from "./ArchitecturePage";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock("../services/api", () => ({
  api: {
    architecture: {
      estimateCosts: vi.fn(),
    },
  },
}));

vi.mock("../components/visualizer/ArchitectureDiagram", () => ({
  default: () => <div data-testid="architecture-diagram">Diagram</div>,
}));

vi.mock("../components/visualizer/ArchitectureChat", () => ({
  default: () => <div data-testid="architecture-chat">Chat</div>,
}));

vi.mock("../utils/exportUtils", () => ({
  exportArchitectureJson: vi.fn(),
  exportDesignDocument: vi.fn(),
}));

const mockArchitecture = {
  organization_size: "medium",
  management_groups: {
    "tenant-root": {
      display_name: "Tenant Root Group",
      children: {
        platform: { display_name: "Platform", children: {} },
        "landing-zones": { display_name: "Landing Zones", children: {} },
      },
    },
  },
  subscriptions: [
    { name: "Prod-Corp", purpose: "Production workloads", management_group: "corp" },
  ],
  network_topology: { type: "hub-spoke", primary_region: "eastus2" },
};

function renderPage() {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <ArchitecturePage />
    </FluentProvider>,
  );
}

describe("ArchitecturePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it("shows warning when no architecture is stored", () => {
    renderPage();
    expect(screen.getByText("No architecture generated yet")).toBeInTheDocument();
    expect(
      screen.getByText(/complete the questionnaire first/i),
    ).toBeInTheDocument();
  });

  it("renders page title when architecture exists", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(screen.getByText("Your Landing Zone Architecture")).toBeInTheDocument();
  });

  it("renders organization badge", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(screen.getByText(/medium organization/i)).toBeInTheDocument();
  });

  it("renders the architecture diagram", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(screen.getByTestId("architecture-diagram")).toBeInTheDocument();
  });

  it("renders the architecture chat", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(screen.getByTestId("architecture-chat")).toBeInTheDocument();
  });

  it("renders Deploy to Azure button", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(screen.getByRole("button", { name: /deploy to azure/i })).toBeInTheDocument();
  });

  it("renders View Bicep Templates button", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(screen.getByRole("button", { name: /view bicep templates/i })).toBeInTheDocument();
  });

  it("renders Score Compliance button", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(screen.getByRole("button", { name: /score compliance/i })).toBeInTheDocument();
  });

  it("renders Export JSON button", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(screen.getByRole("button", { name: /export json/i })).toBeInTheDocument();
  });

  it("renders Export Design Document button", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(screen.getByRole("button", { name: /export design document/i })).toBeInTheDocument();
  });

  it("renders subscriptions list", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(screen.getByText("Prod-Corp")).toBeInTheDocument();
  });

  it("renders Estimate Costs button", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(screen.getByRole("button", { name: /estimate costs/i })).toBeInTheDocument();
  });
});
