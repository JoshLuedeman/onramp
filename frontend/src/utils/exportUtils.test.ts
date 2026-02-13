import { describe, it, expect, vi, beforeEach } from "vitest";
import { exportArchitectureJson, exportComplianceReport, exportDesignDocument } from "./exportUtils";

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("exportArchitectureJson", () => {
  it("creates a JSON blob and triggers download", () => {
    const mockClick = vi.fn();
    const mockCreateElement = vi.spyOn(document, "createElement").mockReturnValue({
      click: mockClick,
      href: "",
      download: "",
      set setAttribute(_: string) {},
    } as unknown as HTMLAnchorElement);
    const mockCreateObjectURL = vi.fn().mockReturnValue("blob:test");
    const mockRevokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { createObjectURL: mockCreateObjectURL, revokeObjectURL: mockRevokeObjectURL });

    exportArchitectureJson({ test: true });
    expect(mockCreateObjectURL).toHaveBeenCalled();
    expect(mockClick).toHaveBeenCalled();
    expect(mockRevokeObjectURL).toHaveBeenCalled();
    mockCreateElement.mockRestore();
  });
});

describe("exportComplianceReport", () => {
  it("generates HTML with compliance data", () => {
    const mockClick = vi.fn();
    const spy = vi.spyOn(document, "createElement").mockReturnValue({
      click: mockClick, href: "", download: "",
    } as unknown as HTMLAnchorElement);
    vi.stubGlobal("URL", { createObjectURL: vi.fn().mockReturnValue("blob:test"), revokeObjectURL: vi.fn() });

    exportComplianceReport({ overall_score: 85, frameworks: [] });
    expect(mockClick).toHaveBeenCalled();
    spy.mockRestore();
  });
});

describe("exportDesignDocument", () => {
  it("generates HTML design document", () => {
    const mockClick = vi.fn();
    const spy = vi.spyOn(document, "createElement").mockReturnValue({
      click: mockClick, href: "", download: "",
    } as unknown as HTMLAnchorElement);
    vi.stubGlobal("URL", { createObjectURL: vi.fn().mockReturnValue("blob:test"), revokeObjectURL: vi.fn() });

    exportDesignDocument({ management_groups: [], subscriptions: [] });
    expect(mockClick).toHaveBeenCalled();
    spy.mockRestore();
  });
});
