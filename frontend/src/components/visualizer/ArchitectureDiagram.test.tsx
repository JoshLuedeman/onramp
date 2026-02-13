import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import ArchitectureDiagram from "./ArchitectureDiagram";

const mockManagementGroups = {
  "tenant-root": {
    display_name: "Tenant Root Group",
    children: {
      platform: {
        display_name: "Platform",
        children: {
          identity: { display_name: "Identity", children: {} },
          management: { display_name: "Management", children: {} },
        },
      },
      "landing-zones": {
        display_name: "Landing Zones",
        children: {
          corp: { display_name: "Corp", children: {} },
          online: { display_name: "Online", children: {} },
        },
      },
    },
  },
};

const mockSubscriptions = [
  { name: "Prod-Corp", purpose: "Production", management_group: "corp", budget: 5000 },
  { name: "Dev-Online", purpose: "Development", management_group: "online", budget: 2000 },
];

function renderDiagram(
  groups = mockManagementGroups,
  subscriptions = mockSubscriptions,
) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <ArchitectureDiagram
        managementGroups={groups}
        subscriptions={subscriptions}
      />
    </FluentProvider>,
  );
}

describe("ArchitectureDiagram", () => {
  it("renders the tree with management group names", () => {
    renderDiagram();
    expect(screen.getByText("Tenant Root Group")).toBeInTheDocument();
    expect(screen.getByText("Platform")).toBeInTheDocument();
    expect(screen.getByText("Landing Zones")).toBeInTheDocument();
    expect(screen.getByText("Identity")).toBeInTheDocument();
    expect(screen.getByText("Management")).toBeInTheDocument();
    expect(screen.getByText("Corp")).toBeInTheDocument();
    expect(screen.getByText("Online")).toBeInTheDocument();
  });

  it("renders subscription names under their groups", () => {
    renderDiagram();
    expect(screen.getByText("Prod-Corp")).toBeInTheDocument();
    expect(screen.getByText("Dev-Online")).toBeInTheDocument();
  });

  it("renders the tree with aria label", () => {
    renderDiagram();
    expect(screen.getByRole("tree", { name: /management group hierarchy/i })).toBeInTheDocument();
  });

  it("renders the collapse all button (default is expanded)", () => {
    renderDiagram();
    expect(screen.getByRole("button", { name: /collapse all/i })).toBeInTheDocument();
  });

  it("toggles to expand all after collapsing", async () => {
    const user = userEvent.setup();
    renderDiagram();

    const button = screen.getByRole("button", { name: /collapse all/i });
    await user.click(button);

    expect(screen.getByRole("button", { name: /expand all/i })).toBeInTheDocument();
  });

  it("shows subscription count badges", () => {
    renderDiagram();
    const badges = screen.getAllByText("1 sub");
    expect(badges.length).toBe(2);
  });

  it("renders without subscriptions", () => {
    renderDiagram(mockManagementGroups, []);
    expect(screen.getByText("Tenant Root Group")).toBeInTheDocument();
    expect(screen.queryByText("Prod-Corp")).not.toBeInTheDocument();
  });
});
