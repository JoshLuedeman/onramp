import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "./api";

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("api.questionnaire", () => {
  it("getCategories calls correct endpoint", async () => {
    const mockResponse = { categories: [{ id: "org", name: "Organization" }] };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    }));
    const result = await api.questionnaire.getCategories();
    expect(result.categories).toHaveLength(1);
    expect(fetch).toHaveBeenCalledWith(
      "/api/questionnaire/categories",
      expect.objectContaining({ headers: expect.any(Object) })
    );
  });

  it("getNextQuestion sends POST with answers", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ complete: false, question: null }),
    }));
    await api.questionnaire.getNextQuestion({ q1: "a" });
    expect(fetch).toHaveBeenCalledWith(
      "/api/questionnaire/next",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("throws on non-ok response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
    }));
    await expect(api.questionnaire.getCategories()).rejects.toThrow("API error: 500");
  });
});

describe("api.architecture", () => {
  it("generate sends answers and use_ai flag", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ architecture: {} }),
    }));
    await api.architecture.generate({ q1: "a" }, true);
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.use_ai).toBe(true);
  });

  it("refine sends architecture and message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ response: "ok", updated_architecture: null }),
    }));
    await api.architecture.refine({ mg: [] }, "add sandbox");
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.message).toBe("add sandbox");
  });

  it("estimateCosts calls correct endpoint", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ total_monthly: 1000 }),
    }));
    await api.architecture.estimateCosts({ mg: [] });
    expect(fetch).toHaveBeenCalledWith(
      "/api/architecture/estimate-costs",
      expect.any(Object)
    );
  });
});
