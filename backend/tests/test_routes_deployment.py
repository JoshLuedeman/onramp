"""Tests for deployment API routes."""
import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.credentials import credential_manager

client = TestClient(app)


def test_validate_deployment():
    r = client.post("/api/deployment/validate", json={
        "subscription_id": "00000000-0000-0000-0000-000000000001",
        "region": "eastus2",
    })
    assert r.status_code == 200
    data = r.json()
    assert "subscription_id" in data
    assert "ready_to_deploy" in data
    assert "details" in data


def test_validate_deployment_default_region():
    r = client.post("/api/deployment/validate", json={
        "subscription_id": "test-sub-id",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["subscription_id"] == "test-sub-id"


def test_create_deployment():
    r = client.post("/api/deployment/create", json={
        "project_id": "proj-001",
        "architecture": {"management_groups": [{"name": "root"}]},
        "subscription_ids": ["sub-001"],
    })
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["project_id"] == "proj-001"
    assert "status" in data


def test_get_deployment_not_found():
    r = client.get("/api/deployment/nonexistent-id")
    assert r.status_code == 404


def test_start_deployment_not_found():
    r = client.post("/api/deployment/nonexistent-id/start")
    assert r.status_code == 404


def test_rollback_deployment_not_found():
    r = client.post("/api/deployment/nonexistent-id/rollback")
    assert r.status_code == 404


def test_audit_deployment_not_found():
    r = client.get("/api/deployment/nonexistent-id/audit")
    assert r.status_code == 404


def test_list_deployments():
    r = client.get("/api/deployment/")
    assert r.status_code == 200
    data = r.json()
    assert "deployments" in data
    assert isinstance(data["deployments"], list)


def test_list_deployments_with_project_filter():
    r = client.get("/api/deployment/?project_id=proj-001")
    assert r.status_code == 200
    assert "deployments" in r.json()


def test_create_and_get_deployment():
    """Create a deployment then retrieve it."""
    create_r = client.post("/api/deployment/create", json={
        "project_id": "proj-002",
        "architecture": {"management_groups": []},
        "subscription_ids": ["sub-002"],
    })
    assert create_r.status_code == 201
    deployment_id = create_r.json()["id"]

    get_r = client.get(f"/api/deployment/{deployment_id}")
    assert get_r.status_code == 200
    assert get_r.json()["id"] == deployment_id


def test_create_and_start_deployment():
    """Create then start a deployment."""
    create_r = client.post("/api/deployment/create", json={
        "project_id": "proj-003",
        "architecture": {"management_groups": [], "subscriptions": []},
        "subscription_ids": ["sub-003"],
    })
    assert create_r.status_code == 201
    deployment_id = create_r.json()["id"]

    start_r = client.post(f"/api/deployment/{deployment_id}/start")
    assert start_r.status_code == 200
    assert "status" in start_r.json()


def test_create_and_get_audit():
    """Create a deployment then get its audit log."""
    create_r = client.post("/api/deployment/create", json={
        "project_id": "proj-004",
        "architecture": {"management_groups": []},
        "subscription_ids": ["sub-004"],
    })
    assert create_r.status_code == 201
    deployment_id = create_r.json()["id"]

    audit_r = client.get(f"/api/deployment/{deployment_id}/audit")
    assert audit_r.status_code == 200
    data = audit_r.json()
    assert "entries" in data
    assert data["deployment_id"] == deployment_id


def test_create_start_and_rollback():
    """Create, start, then rollback a deployment."""
    create_r = client.post("/api/deployment/create", json={
        "project_id": "proj-005",
        "architecture": {"management_groups": []},
        "subscription_ids": ["sub-005"],
    })
    deployment_id = create_r.json()["id"]

    client.post(f"/api/deployment/{deployment_id}/start")
    rollback_r = client.post(f"/api/deployment/{deployment_id}/rollback")
    assert rollback_r.status_code == 200
    assert "status" in rollback_r.json()


def test_validate_deployment_missing_field():
    """Validate without subscription_id returns 422."""
    r = client.post("/api/deployment/validate", json={"region": "eastus2"})
    assert r.status_code == 422


def test_validate_deployment_uses_region_not_location(monkeypatch):
    """Verify the API uses 'region' parameter (not 'location') matching frontend contract."""
    captured_regions = []
    original_check = credential_manager.check_subscription_quotas

    async def capture_region(sub_id, region):
        captured_regions.append(region)
        return await original_check(sub_id, region)

    monkeypatch.setattr(credential_manager, "check_subscription_quotas", capture_region)

    # Explicit region should be passed through
    r = client.post("/api/deployment/validate", json={
        "subscription_id": "test-sub",
        "region": "westus2",
    })
    assert r.status_code == 200
    assert captured_regions[-1] == "westus2"

    # 'location' is not a valid field — Pydantic ignores it, uses default 'eastus2'
    r2 = client.post("/api/deployment/validate", json={
        "subscription_id": "test-sub",
        "location": "westus2",
    })
    assert r2.status_code == 200
    assert captured_regions[-1] == "eastus2"  # default, not 'westus2'


def test_create_deployment_missing_fields():
    """Create without required fields returns 422."""
    r = client.post("/api/deployment/create", json={"project_id": "p1"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_validate_deployment_async():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/deployment/validate", json={
            "subscription_id": "async-sub",
            "region": "westus2",
        })
        assert r.status_code == 200
        assert r.json()["subscription_id"] == "async-sub"


@pytest.mark.asyncio
async def test_list_deployments_async():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/deployment/")
        assert r.status_code == 200
        assert "deployments" in r.json()
