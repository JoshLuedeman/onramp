import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import ExportMenu from "./ExportMenu";

const sampleArchitecture = {
  organization_size: "small",
  subscriptions: [{ name: "prod" }],
  management_groups: { name: "root" },
};

function renderMenu() {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <ExportMenu architecture={sampleArchitecture} />
    </FluentProvider>,
  );
}

describe("ExportMenu", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders without crashing", () => {
    const { container } = renderMenu();
    expect(container).toBeTruthy();
  });

  it("shows the Export trigger button", () => {
    renderMenu();
    expect(screen.getByText("Export")).toBeInTheDocument();
  });

  it("shows export menu items when clicked", async () => {
    const user = userEvent.setup();
    renderMenu();
    await user.click(screen.getByText("Export"));
    expect(screen.getByText("Export as JSON")).toBeInTheDocument();
    expect(screen.getByText("Export as SVG")).toBeInTheDocument();
    expect(screen.getByText("Export as Markdown")).toBeInTheDocument();
  });

  it("exports JSON when menu item clicked", async () => {
    const user = userEvent.setup();
    renderMenu();

    // Mock after render so jsdom can create elements normally
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL: vi.fn().mockReturnValue("blob:test"), revokeObjectURL });

    await user.click(screen.getByText("Export"));
    await user.click(screen.getByText("Export as JSON"));
    expect(revokeObjectURL).toHaveBeenCalled();
  });

  it("exports SVG when menu item clicked", async () => {
    const user = userEvent.setup();
    renderMenu();

    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL: vi.fn().mockReturnValue("blob:test"), revokeObjectURL });

    await user.click(screen.getByText("Export"));
    await user.click(screen.getByText("Export as SVG"));
    expect(revokeObjectURL).toHaveBeenCalled();
  });

  it("exports Markdown when menu item clicked", async () => {
    const user = userEvent.setup();
    renderMenu();

    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL: vi.fn().mockReturnValue("blob:test"), revokeObjectURL });

    await user.click(screen.getByText("Export"));
    await user.click(screen.getByText("Export as Markdown"));
    expect(revokeObjectURL).toHaveBeenCalled();
  });
});
