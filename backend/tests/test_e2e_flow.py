"""End-to-end flow tests covering the full user journey."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_full_journey_small_org():
    """Test: questionnaire -> architecture -> compliance -> bicep -> deploy."""
    # Step 1: Start questionnaire
    r = client.post("/api/questionnaire/next", json={"answers": {}})
    assert r.status_code == 200
    assert r.json()["question"] is not None

    # Step 2: Generate small architecture
    answers = {
        "org_name": "SmallCo",
        "org_size": "small",
        "primary_region": "westus2",
    }
    r = client.post(
        "/api/architecture/generate",
        json={"answers": answers, "use_ai": False, "use_archetype": True},
    )
    assert r.status_code == 200
    arch = r.json()["architecture"]
    assert arch["organization_size"] == "small"

    # Step 3: Score compliance
    r = client.post(
        "/api/scoring/evaluate",
        json={"architecture": arch, "frameworks": ["SOC2"]},
    )
    assert r.status_code == 200
    assert r.json()["overall_score"] >= 0

    # Step 4: Generate Bicep
    r = client.post("/api/bicep/generate", json={"architecture": arch})
    assert r.status_code == 200
    assert len(r.json()["files"]) >= 5

    # Step 5: Validate subscription
    r = client.post(
        "/api/deployment/validate",
        json={"subscription_id": "sub-123", "region": "westus2"},
    )
    assert r.status_code == 200

    # Step 6: Create and run deployment
    r = client.post(
        "/api/deployment/create",
        json={
            "project_id": "e2e-test",
            "architecture": arch,
            "subscription_ids": ["sub-123"],
        },
    )
    assert r.status_code == 201
    deploy_id = r.json()["id"]
    assert r.json()["status"] == "pending"

    r = client.post(f"/api/deployment/{deploy_id}/start")
    assert r.status_code == 200
    assert r.json()["status"] == "succeeded"

    # Step 7: Check audit log
    r = client.get(f"/api/deployment/{deploy_id}/audit")
    assert r.status_code == 200
    assert len(r.json()["entries"]) >= 3


def test_full_journey_enterprise_org():
    """Test enterprise flow with compliance."""
    answers = {
        "org_name": "EnterpriseCorp",
        "org_size": "enterprise",
        "primary_region": "eastus2",
        "network_topology": "hub_spoke",
        "compliance_frameworks": ["hipaa", "soc2"],
    }
    r = client.post(
        "/api/architecture/generate",
        json={"answers": answers, "use_ai": False, "use_archetype": True},
    )
    assert r.status_code == 200
    arch = r.json()["architecture"]
    assert arch["organization_size"] == "enterprise"
    assert len(arch.get("subscriptions", [])) >= 6

    # Score against multiple frameworks
    r = client.post(
        "/api/scoring/evaluate",
        json={"architecture": arch, "frameworks": ["SOC2", "HIPAA", "PCI-DSS"]},
    )
    assert r.status_code == 200
    assert len(r.json()["frameworks"]) == 3

    # Generate Bicep
    r = client.post("/api/bicep/generate", json={"architecture": arch})
    assert r.status_code == 200
    files = r.json()["files"]
    assert any("main.bicep" in f["name"] for f in files)


def test_deployment_rollback():
    """Test deployment with rollback."""
    answers = {"org_size": "small"}
    r = client.post(
        "/api/architecture/generate",
        json={"answers": answers, "use_ai": False, "use_archetype": True},
    )
    arch = r.json()["architecture"]

    # Create and start deployment
    r = client.post(
        "/api/deployment/create",
        json={
            "project_id": "rollback-test",
            "architecture": arch,
            "subscription_ids": ["sub-456"],
        },
    )
    deploy_id = r.json()["id"]
    client.post(f"/api/deployment/{deploy_id}/start")

    # Rollback
    r = client.post(f"/api/deployment/{deploy_id}/rollback")
    assert r.status_code == 200
    assert r.json()["status"] == "rolled_back"


def test_all_archetypes_generate_valid_bicep():
    """Every archetype should produce valid Bicep output."""
    for size in ["small", "medium", "enterprise"]:
        r = client.post(
            "/api/architecture/generate",
            json={"answers": {"org_size": size}, "use_ai": False, "use_archetype": True},
        )
        assert r.status_code == 200
        arch = r.json()["architecture"]

        r = client.post("/api/bicep/generate", json={"architecture": arch})
        assert r.status_code == 200
        files = r.json()["files"]
        assert len(files) >= 5, f"{size} archetype should generate at least 5 files"
