import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import DeployPage from "./DeployPage";

vi.mock("../services/api", () => ({
  api: {
    deployment: {
      validate: vi.fn().mockResolvedValue({ ready_to_deploy: true }),
    },
  },
}));

const mockArchitecture = {
  organization_size: "small",
  management_groups: {},
  subscriptions: [],
  network_topology: {},
};

function renderPage() {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <DeployPage />
    </FluentProvider>
  );
}

describe("DeployPage", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it("shows warning when no architecture is stored", () => {
    renderPage();
    expect(screen.getByText(/no architecture found/i)).toBeInTheDocument();
  });

  it("renders page title when architecture exists", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(screen.getByText(/deploy landing zone/i)).toBeInTheDocument();
  });

  it("renders subscription input when architecture exists", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(screen.getByPlaceholderText(/subscription id/i)).toBeInTheDocument();
  });

  it("renders validate button when architecture exists", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(screen.getByRole("button", { name: /validate/i })).toBeInTheDocument();
  });

  it("validate button is disabled when no subscription ID entered", () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    renderPage();
    expect(screen.getByRole("button", { name: /validate/i })).toBeDisabled();
  });

  it("enables validate button when subscription ID is entered", async () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    const user = userEvent.setup();
    renderPage();
    await user.type(screen.getByPlaceholderText(/subscription id/i), "sub-123");
    expect(screen.getByRole("button", { name: /validate/i })).not.toBeDisabled();
  });

  it("shows success message after validation", async () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    const user = userEvent.setup();
    renderPage();
    await user.type(screen.getByPlaceholderText(/subscription id/i), "sub-123");
    await user.click(screen.getByRole("button", { name: /validate/i }));
    expect(await screen.findByText(/subscription validated/i)).toBeInTheDocument();
  });

  it("shows deploy button after validation", async () => {
    sessionStorage.setItem("onramp_architecture", JSON.stringify(mockArchitecture));
    const user = userEvent.setup();
    renderPage();
    await user.type(screen.getByPlaceholderText(/subscription id/i), "sub-123");
    await user.click(screen.getByRole("button", { name: /validate/i }));
    expect(await screen.findByRole("button", { name: /deploy to azure/i })).toBeInTheDocument();
  });
});
