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

describe("api.bicep", () => {
  it("templates lists available templates", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ templates: [] }),
    }));
    await api.bicep.templates();
    expect(fetch).toHaveBeenCalledWith(
      "/api/bicep/templates",
      expect.objectContaining({ headers: expect.any(Object) })
    );
  });

  it("getTemplate fetches a specific template", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ name: "vnet", content: "param location string" }),
    }));
    await api.bicep.getTemplate("vnet");
    expect(fetch).toHaveBeenCalledWith(
      "/api/bicep/templates/vnet",
      expect.any(Object)
    );
  });

  it("generate sends architecture with POST", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ files: [] }),
    }));
    await api.bicep.generate({ mg: {} }, { use_ai: false, project_id: "p1" });
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/api/bicep/generate");
    const body = JSON.parse(call[1].body);
    expect(body.use_ai).toBe(false);
    expect(body.project_id).toBe("p1");
  });

  it("getByProject fetches bicep files for a project", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ files: [], project_id: "p1" }),
    }));
    await api.bicep.getByProject("p1");
    expect(fetch).toHaveBeenCalledWith(
      "/api/bicep/project/p1",
      expect.any(Object)
    );
  });
});

describe("api.deployment", () => {
  it("validate sends subscription and region", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ready_to_deploy: true }),
    }));
    await api.deployment.validate("sub-123", "westus2");
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/api/deployment/validate");
    const body = JSON.parse(call[1].body);
    expect(body.subscription_id).toBe("sub-123");
    expect(body.region).toBe("westus2");
  });

  it("create sends project data", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: "d1", status: "pending" }),
    }));
    await api.deployment.create("p1", { mg: {} }, ["sub-1"]);
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/api/deployment/create");
    const body = JSON.parse(call[1].body);
    expect(body.project_id).toBe("p1");
    expect(body.subscription_ids).toEqual(["sub-1"]);
  });

  it("start posts to correct endpoint", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: "d1", status: "running" }),
    }));
    await api.deployment.start("d1");
    expect(fetch).toHaveBeenCalledWith(
      "/api/deployment/d1/start",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("status fetches deployment by id", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: "d1", status: "complete" }),
    }));
    await api.deployment.status("d1");
    expect(fetch).toHaveBeenCalledWith(
      "/api/deployment/d1",
      expect.any(Object)
    );
  });

  it("rollback posts to correct endpoint", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: "d1", status: "rolled_back" }),
    }));
    await api.deployment.rollback("d1");
    expect(fetch).toHaveBeenCalledWith(
      "/api/deployment/d1/rollback",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("audit fetches deployment audit log", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ deployment_id: "d1", entries: [] }),
    }));
    await api.deployment.audit("d1");
    expect(fetch).toHaveBeenCalledWith(
      "/api/deployment/d1/audit",
      expect.any(Object)
    );
  });

  it("list fetches all deployments", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ deployments: [] }),
    }));
    await api.deployment.list();
    expect(fetch).toHaveBeenCalledWith(
      "/api/deployment/",
      expect.any(Object)
    );
  });
});

describe("api.scoring", () => {
  it("evaluate sends architecture and frameworks", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ results: {}, overall_score: 85 }),
    }));
    await api.scoring.evaluate({ mg: {} }, ["cis", "nist"]);
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/api/scoring/evaluate");
    const body = JSON.parse(call[1].body);
    expect(body.frameworks).toEqual(["cis", "nist"]);
  });

  it("getByProject fetches scoring results", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ results: [], project_id: "p1" }),
    }));
    await api.scoring.getByProject("p1");
    expect(fetch).toHaveBeenCalledWith(
      "/api/scoring/project/p1",
      expect.any(Object)
    );
  });
});

describe("api.users", () => {
  it("me fetches current user profile", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: "u1", name: "Test User" }),
    }));
    await api.users.me();
    expect(fetch).toHaveBeenCalledWith(
      "/api/users/me",
      expect.any(Object)
    );
  });

  it("projects fetches user projects", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ projects: [] }),
    }));
    await api.users.projects();
    expect(fetch).toHaveBeenCalledWith(
      "/api/users/me/projects",
      expect.any(Object)
    );
  });
});

describe("api.projects", () => {
  it("list fetches all projects", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ projects: [] }),
    }));
    await api.projects.list();
    expect(fetch).toHaveBeenCalledWith(
      "/api/projects/",
      expect.any(Object)
    );
  });

  it("create sends project data", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: "p1", name: "Test" }),
    }));
    await api.projects.create({ name: "Test", tags: ["prod"] });
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body);
    expect(body.name).toBe("Test");
    expect(body.tags).toEqual(["prod"]);
  });

  it("delete sends DELETE request", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ deleted: true }),
    }));
    await api.projects.delete("p1");
    expect(fetch).toHaveBeenCalledWith(
      "/api/projects/p1",
      expect.objectContaining({ method: "DELETE" })
    );
  });
});
