import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import DetailPanel from "./DetailPanel";

function renderPanel(
  component: { type: string; name: string; properties?: Record<string, unknown>; tags?: Record<string, string> },
  onClose = vi.fn(),
) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <DetailPanel component={component} onClose={onClose} />
    </FluentProvider>,
  );
}

describe("DetailPanel", () => {
  it("renders component name and type", () => {
    renderPanel({ type: "Subscription", name: "prod-sub" });

    expect(screen.getByText("prod-sub")).toBeInTheDocument();
    expect(screen.getByText("Subscription")).toBeInTheDocument();
  });

  it("renders properties when provided", () => {
    renderPanel({
      type: "VNet",
      name: "hub-vnet",
      properties: { addressSpace: "10.0.0.0/16", region: "eastus" },
    });

    expect(screen.getByText("addressSpace")).toBeInTheDocument();
    expect(screen.getByText("10.0.0.0/16")).toBeInTheDocument();
    expect(screen.getByText("region")).toBeInTheDocument();
    expect(screen.getByText("eastus")).toBeInTheDocument();
  });

  it("renders tags when provided", () => {
    renderPanel({
      type: "ResourceGroup",
      name: "rg-app",
      tags: { environment: "production", team: "platform" },
    });

    expect(screen.getByText("environment")).toBeInTheDocument();
    expect(screen.getByText("production")).toBeInTheDocument();
    expect(screen.getByText("team")).toBeInTheDocument();
    expect(screen.getByText("platform")).toBeInTheDocument();
  });

  it("does not render properties section when none provided", () => {
    renderPanel({ type: "Subscription", name: "dev-sub" });

    expect(screen.queryByText("Properties")).not.toBeInTheDocument();
  });

  it("does not render tags section when tags are empty", () => {
    renderPanel({ type: "Subscription", name: "dev-sub", tags: {} });

    expect(screen.queryByText("Tags")).not.toBeInTheDocument();
  });
});
