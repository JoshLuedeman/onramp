import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import ArchitectureChat from "./ArchitectureChat";
import type { Architecture } from "../../services/api";

// Mock the api module so no real HTTP calls are made
vi.mock("../../services/api", () => ({
  api: {
    architecture: {
      refine: vi.fn().mockResolvedValue({
        response: "Here is a suggestion.",
        updated_architecture: null,
      }),
    },
  },
}));

const mockArchitecture: Architecture = {
  organization_size: "small",
  management_groups: {},
  subscriptions: [{ name: "prod", purpose: "production", management_group: "mg1" }],
  network_topology: {},
};

function renderChat(onUpdate = vi.fn()) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <ArchitectureChat
        architecture={mockArchitecture}
        onArchitectureUpdate={onUpdate}
      />
    </FluentProvider>,
  );
}

describe("ArchitectureChat", () => {
  it("renders without crashing", () => {
    const { container } = renderChat();
    expect(container).toBeTruthy();
  });

  it("shows the toggle button", () => {
    renderChat();
    expect(screen.getByText("💬 Refine with AI Chat")).toBeInTheDocument();
  });

  it("reveals the chat panel and suggested prompts when toggled open", async () => {
    const user = userEvent.setup();
    renderChat();

    await user.click(screen.getByText("💬 Refine with AI Chat"));

    expect(screen.getByText("Why did you choose this network topology?")).toBeInTheDocument();
    expect(screen.getByText("Add more security controls")).toBeInTheDocument();
    expect(screen.getByText("Reduce estimated costs")).toBeInTheDocument();
    expect(screen.getByText("Explain the management group hierarchy")).toBeInTheDocument();
  });

  it("shows the input field and send button when open", async () => {
    const user = userEvent.setup();
    renderChat();

    await user.click(screen.getByText("💬 Refine with AI Chat"));

    expect(
      screen.getByPlaceholderText("Ask about or refine your architecture..."),
    ).toBeInTheDocument();
    expect(screen.getByText("Send")).toBeInTheDocument();
  });

  it("disables Send button when input is empty", async () => {
    const user = userEvent.setup();
    renderChat();
    await user.click(screen.getByText("💬 Refine with AI Chat"));

    expect(screen.getByText("Send").closest("button")).toBeDisabled();
  });
});
