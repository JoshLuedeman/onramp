"""Performance tests for OnRamp API."""

import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_latency():
    """Health endpoint should respond in < 100ms."""
    start = time.perf_counter()
    r = client.get("/health")
    elapsed = time.perf_counter() - start
    assert r.status_code == 200
    assert elapsed < 0.1, f"Health check took {elapsed:.3f}s"


def test_questionnaire_categories_latency():
    """Categories endpoint should respond quickly."""
    start = time.perf_counter()
    r = client.get("/api/questionnaire/categories")
    elapsed = time.perf_counter() - start
    assert r.status_code == 200
    assert elapsed < 0.2, f"Categories took {elapsed:.3f}s"


def test_architecture_generation_latency():
    """Architecture generation (no AI) should be fast."""
    start = time.perf_counter()
    r = client.post(
        "/api/architecture/generate",
        json={"answers": {"org_size": "medium"}, "use_ai": False},
    )
    elapsed = time.perf_counter() - start
    assert r.status_code == 200
    assert elapsed < 0.5, f"Architecture generation took {elapsed:.3f}s"


def test_bicep_generation_latency():
    """Bicep generation should complete quickly."""
    r = client.post(
        "/api/architecture/generate",
        json={"answers": {"org_size": "enterprise"}, "use_ai": False},
    )
    arch = r.json()["architecture"]

    start = time.perf_counter()
    r = client.post("/api/bicep/generate", json={"architecture": arch})
    elapsed = time.perf_counter() - start
    assert r.status_code == 200
    assert elapsed < 1.0, f"Bicep generation took {elapsed:.3f}s"


def test_compliance_scoring_latency():
    """Compliance scoring should be fast."""
    r = client.post(
        "/api/architecture/generate",
        json={"answers": {"org_size": "enterprise"}, "use_ai": False},
    )
    arch = r.json()["architecture"]

    start = time.perf_counter()
    r = client.post(
        "/api/scoring/evaluate",
        json={"architecture": arch, "frameworks": ["SOC2", "HIPAA", "PCI-DSS", "NIST 800-53", "ISO 27001", "FedRAMP"]},
    )
    elapsed = time.perf_counter() - start
    assert r.status_code == 200
    assert elapsed < 1.0, f"Compliance scoring took {elapsed:.3f}s"


def test_concurrent_architecture_generation():
    """Multiple architecture generations should complete quickly."""
    start = time.perf_counter()
    for size in ["small", "medium", "enterprise"] * 3:
        r = client.post(
            "/api/architecture/generate",
            json={"answers": {"org_size": size}, "use_ai": False},
        )
        assert r.status_code == 200
    elapsed = time.perf_counter() - start
    assert elapsed < 3.0, f"9 architecture generations took {elapsed:.3f}s"
