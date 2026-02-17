import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

describe("AuthProvider – dev mode (no client ID)", () => {
  it("renders children directly when no client ID", async () => {
    vi.resetModules();
    const { default: AuthProvider } = await import("./AuthProvider");
    render(
      <AuthProvider>
        <div>Child Content</div>
      </AuthProvider>
    );
    expect(screen.getByText("Child Content")).toBeInTheDocument();
  });

  it("exports msalInstance as null initially", async () => {
    vi.resetModules();
    const { msalInstance } = await import("./msalInstance");
    expect(msalInstance).toBeNull();
  });

  it("exports initMsal function", async () => {
    vi.resetModules();
    const { initMsal } = await import("./msalInstance");
    expect(typeof initMsal).toBe("function");
  });

  it("initMsal returns null when no client ID", async () => {
    vi.resetModules();
    const { initMsal } = await import("./msalInstance");
    const result = await initMsal();
    expect(result).toBeNull();
  });
});
