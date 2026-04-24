import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";

// useAuth checks import.meta.env.VITE_AZURE_CLIENT_ID at module scope.
// When it's empty (default in test), the hook returns a dev-mode stub
// without touching MSAL at all.

describe("useAuth – dev mode (no client ID)", () => {
  let useAuth: typeof import("./useAuth").useAuth;

  beforeEach(async () => {
    vi.resetModules();
    const mod = await import("./useAuth");
    useAuth = mod.useAuth;
  });

  it("returns isAuthenticated true in dev mode", () => {
    const { result } = renderHook(() => useAuth());
    expect(result.current.isAuthenticated).toBe(true);
  });

  it("returns login and logout functions", () => {
    const { result } = renderHook(() => useAuth());
    expect(typeof result.current.login).toBe("function");
    expect(typeof result.current.logout).toBe("function");
  });

  it("returns a mock dev user in dev mode", () => {
    const { result } = renderHook(() => useAuth());
    expect(result.current.user).toEqual({
      name: "Dev User",
      email: "dev@onramp.local",
      id: "dev-user-001",
    });
  });

  it("returns getAccessToken function", () => {
    const { result } = renderHook(() => useAuth());
    expect(typeof result.current.getAccessToken).toBe("function");
  });

  it("getAccessToken resolves to dev-token in dev mode", async () => {
    const { result } = renderHook(() => useAuth());
    const token = await result.current.getAccessToken();
    expect(token).toBe("dev-token");
  });

  it("login does not throw in dev mode", async () => {
    const { result } = renderHook(() => useAuth());
    await expect(result.current.login()).resolves.toBeUndefined();
  });

  it("logout does not throw in dev mode", async () => {
    const { result } = renderHook(() => useAuth());
    await expect(result.current.logout()).resolves.toBeUndefined();
  });
});
