import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { FluentProvider, teamsLightTheme } from "@fluentui/react-components";
import Layout from "./Layout";

// Mock useAuth used by AuthButton
vi.mock("../../auth", () => ({
  useAuth: () => ({
    isAuthenticated: false,
    user: null,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

function renderLayout(children = <div>Test Content</div>) {
  return render(
    <FluentProvider theme={teamsLightTheme}>
      <MemoryRouter>
        <Layout>{children}</Layout>
      </MemoryRouter>
    </FluentProvider>
  );
}

describe("Layout", () => {
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
});
