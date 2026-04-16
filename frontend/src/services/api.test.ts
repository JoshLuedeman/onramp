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

  it("download returns a Blob from the response", async () => {
    const fakeBlob = new Blob(["bicep content"], { type: "text/plain" });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(fakeBlob),
    }));
    const result = await api.bicep.download({ mg: {} });
    expect(fetch).toHaveBeenCalledWith(
      "/api/bicep/download",
      expect.objectContaining({ method: "POST" })
    );
    expect(result).toBeInstanceOf(Blob);
  });

  it("download throws on non-ok response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
    }));
    await expect(api.bicep.download({ mg: {} })).rejects.toThrow("API error: 500");
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

  it("get fetches a single project by id", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: "p1", name: "My Project" }),
    }));
    await api.projects.get("p1");
    expect(fetch).toHaveBeenCalledWith(
      "/api/projects/p1",
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

  it("update sends PUT with partial fields", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: "p1", name: "Updated" }),
    }));
    await api.projects.update("p1", { name: "Updated" });
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/api/projects/p1");
    expect(call[1].method).toBe("PUT");
    const body = JSON.parse(call[1].body);
    expect(body.name).toBe("Updated");
  });

  it("getStats fetches aggregate project statistics", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ total: 5, by_status: { draft: 3, deployed: 2 } }),
    }));
    const result = await api.projects.getStats();
    expect(fetch).toHaveBeenCalledWith(
      "/api/projects/stats",
      expect.any(Object)
    );
    expect(result.total).toBe(5);
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

describe("api.deployment list with projectId", () => {
  it("list with projectId encodes the query parameter", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ deployments: [] }),
    }));
    await api.deployment.list("my project/id");
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toContain(encodeURIComponent("my project/id"));
  });
});

describe("api.workloads", () => {
  it("list calls correct endpoint with project_id", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ workloads: [], total: 0 }),
    }));
    await api.workloads.list("proj-1");
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toContain("/api/workloads");
    expect(call[0]).toContain("project_id=proj-1");
  });

  it("list with projectId includes project_id query param", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ workloads: [], total: 0 }),
    }));
    await api.workloads.list("proj-2");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("project_id=proj-2"),
      expect.any(Object)
    );
  });

  it("create sends POST with workload body", async () => {
    const body = { project_id: "proj-1", name: "MyVM", type: "vm", source_platform: "other" };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: "w1", ...body }),
    }));
    await api.workloads.create(body);
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/api/workloads");
    expect(call[1].method).toBe("POST");
    const parsed = JSON.parse(call[1].body);
    expect(parsed.name).toBe("MyVM");
    expect(parsed.project_id).toBe("proj-1");
  });

  it("update sends PATCH to correct endpoint", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: "w1", name: "Updated" }),
    }));
    await api.workloads.update("w1", { name: "Updated" });
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/api/workloads/w1");
    expect(call[1].method).toBe("PATCH");
    const parsed = JSON.parse(call[1].body);
    expect(parsed.name).toBe("Updated");
  });

  it("delete sends DELETE to correct endpoint", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ deleted: true }),
    }));
    await api.workloads.delete("w1");
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe("/api/workloads/w1");
    expect(call[1].method).toBe("DELETE");
  });

  it("importFile sends POST with file as form data and project_id as query param", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ imported_count: 1, failed_count: 0, errors: [], workloads: [] }),
    }));
    const fakeFile = new File(["name\nweb01"], "workloads.csv", { type: "text/csv" });
    await api.workloads.importFile(fakeFile, "proj-1");
    const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toContain("/api/workloads/import");
    expect(call[0]).toContain("project_id=proj-1");
    expect(call[1].method).toBe("POST");
    expect(call[1].body).toBeInstanceOf(FormData);
  });

  it("importFile throws on non-ok response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      text: () => Promise.resolve("Import failed"),
    }));
    const fakeFile = new File(["name\nweb01"], "workloads.csv", { type: "text/csv" });
    await expect(api.workloads.importFile(fakeFile, "proj-1")).rejects.toThrow("Import failed");
  });
});

describe("api.terraform", () => {
  it("generate sends POST with architecture", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ files: [] }),
    }));
    await api.terraform.generate({ name: "test" });
    expect(fetch).toHaveBeenCalledWith(
      "/api/terraform/generate",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("download sends POST with architecture", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(new Blob(["zip"])),
    }));
    await api.terraform.download({ name: "test" });
    expect(fetch).toHaveBeenCalledWith(
      "/api/terraform/download",
      expect.objectContaining({ method: "POST" })
    );
  });
});

describe("api.arm", () => {
  it("generate sends POST with architecture", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ files: [] }),
    }));
    await api.arm.generate({ name: "test" });
    expect(fetch).toHaveBeenCalledWith(
      "/api/arm/generate",
      expect.objectContaining({ method: "POST" })
    );
  });
});

describe("api.pulumi", () => {
  it("generate sends POST with architecture and language", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ files: [] }),
    }));
    await api.pulumi.generate({ name: "test" }, "typescript");
    expect(fetch).toHaveBeenCalledWith(
      "/api/pulumi/generate",
      expect.objectContaining({ method: "POST" })
    );
  });
});

describe("api.pipelines", () => {
  it("generate sends POST with pipeline request", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ files: [] }),
    }));
    await api.pipelines.generate({
      architecture: { name: "test" },
      pipeline_format: "github_actions",
      iac_format: "bicep",
    });
    expect(fetch).toHaveBeenCalledWith(
      "/api/pipelines/generate",
      expect.objectContaining({ method: "POST" })
    );
  });
});

describe("api.iacValidation", () => {
  it("validate sends POST with code and format", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ is_valid: true, errors: [], warnings: [] }),
    }));
    await api.iacValidation.validate("resource group", "bicep");
    expect(fetch).toHaveBeenCalledWith(
      "/api/iac/validate",
      expect.objectContaining({ method: "POST" })
    );
  });
});

describe("api.versions", () => {
  it("terraform calls GET /api/versions/terraform", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ terraform_version: "1.5", providers: [] }),
    }));
    await api.versions.terraform();
    expect(fetch).toHaveBeenCalledWith(
      "/api/versions/terraform",
      expect.objectContaining({ headers: expect.any(Object) })
    );
  });

  it("report calls GET /api/versions/report", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ total_entries: 0, stale_count: 0 }),
    }));
    await api.versions.report();
    expect(fetch).toHaveBeenCalledWith(
      "/api/versions/report",
      expect.objectContaining({ headers: expect.any(Object) })
    );
  });

  it("report with threshold calls correct URL", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ total_entries: 0, stale_count: 0 }),
    }));
    await api.versions.report(90);
    expect(fetch).toHaveBeenCalledWith(
      "/api/versions/report?threshold_days=90",
      expect.objectContaining({ headers: expect.any(Object) })
    );
  });
});
