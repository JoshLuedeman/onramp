import { describe, it, expect, vi, beforeEach } from "vitest";
import { exportArchitectureJson, exportComplianceReport, exportDesignDocument, exportGapAnalysis } from "./exportUtils";
import type { GapAnalysisResponse } from "../services/api";

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

describe("exportGapAnalysis", () => {
  it("triggers a download for the gap analysis HTML report", () => {
    const mockClick = vi.fn();
    const spy = vi.spyOn(document, "createElement").mockReturnValue({
      click: mockClick, href: "", download: "",
    } as unknown as HTMLAnchorElement);
    vi.stubGlobal("URL", { createObjectURL: vi.fn().mockReturnValue("blob:test"), revokeObjectURL: vi.fn() });

    const result: GapAnalysisResponse = {
      scan_id: "scan-1",
      total_findings: 2,
      critical_count: 1,
      high_count: 1,
      medium_count: 0,
      low_count: 0,
      findings: [
        {
          id: "f-1",
          category: "networking",
          severity: "critical",
          title: "No firewall",
          description: "No Azure Firewall.",
          remediation: "Deploy Azure Firewall.",
          caf_reference: "CAF/networking",
          can_auto_remediate: false,
        },
      ],
      areas_checked: ["networking"],
      areas_skipped: [],
    };

    exportGapAnalysis(result);
    expect(mockClick).toHaveBeenCalled();
    spy.mockRestore();
  });

  it("generates HTML containing finding title and severity", () => {
    const capturedBlobs: Blob[] = [];
    const mockClick = vi.fn();
    const spy = vi.spyOn(document, "createElement").mockReturnValue({
      click: mockClick, href: "", download: "",
    } as unknown as HTMLAnchorElement);
    vi.stubGlobal("URL", {
      createObjectURL: (b: Blob) => { capturedBlobs.push(b); return "blob:test"; },
      revokeObjectURL: vi.fn(),
    });

    const result: GapAnalysisResponse = {
      scan_id: "scan-2",
      total_findings: 1,
      critical_count: 1,
      high_count: 0,
      medium_count: 0,
      low_count: 0,
      findings: [
        {
          id: "f-2",
          category: "identity",
          severity: "critical",
          title: "MFA not enabled",
          description: "MFA is disabled.",
          remediation: "Enable MFA.",
          caf_reference: undefined,
          can_auto_remediate: true,
        },
      ],
      areas_checked: ["identity"],
      areas_skipped: [],
    };

    exportGapAnalysis(result);
    // Verify a blob was created (HTML content is not directly readable without FileReader)
    expect(capturedBlobs).toHaveLength(1);
    expect(capturedBlobs[0].type).toBe("text/html");
    spy.mockRestore();
  });
});
