"""Tests for workload API routes."""

import io
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PROJECT_ID = "proj-test-routes"


# ---------------------------------------------------------------------------
# POST /api/workloads  (manual create)
# ---------------------------------------------------------------------------

def test_create_workload_basic():
    payload = {"project_id": PROJECT_ID, "name": "MyVM", "type": "vm"}
    r = client.post("/api/workloads", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "MyVM"
    assert data["type"] == "vm"
    assert "id" in data


def test_create_workload_full_payload():
    payload = {
        "project_id": PROJECT_ID,
        "name": "FullVM",
        "type": "vm",
        "source_platform": "vmware",
        "cpu_cores": 8,
        "memory_gb": 32.0,
        "storage_gb": 500.0,
        "os_type": "Windows",
        "os_version": "Server 2022",
        "criticality": "mission-critical",
        "compliance_requirements": ["SOC2"],
        "dependencies": [],
        "migration_strategy": "rehost",
        "notes": "Important server",
    }
    r = client.post("/api/workloads", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["criticality"] == "mission-critical"
    assert data["migration_strategy"] == "rehost"
    assert data["compliance_requirements"] == ["SOC2"]


def test_create_workload_missing_name():
    r = client.post("/api/workloads", json={"project_id": PROJECT_ID})
    assert r.status_code == 422


def test_create_workload_missing_project_id():
    r = client.post("/api/workloads", json={"name": "NoProject"})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/workloads?project_id=...
# ---------------------------------------------------------------------------

def test_list_workloads_returns_list():
    r = client.get(f"/api/workloads?project_id={PROJECT_ID}")
    assert r.status_code == 200
    data = r.json()
    assert "workloads" in data
    assert isinstance(data["workloads"], list)


def test_list_workloads_missing_project_id():
    r = client.get("/api/workloads")
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/workloads/import — CSV
# ---------------------------------------------------------------------------

def test_import_csv_basic():
    csv_content = b"name,type,cpu_cores\nweb01,vm,4\nweb02,container,2\n"
    r = client.post(
        f"/api/workloads/import?project_id={PROJECT_ID}",
        files={"file": ("workloads.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["imported_count"] == 2
    assert data["failed_count"] == 0
    assert len(data["workloads"]) == 2


def test_import_csv_with_aliases():
    csv_content = b"vm_name,cpus,ram_gb\nserver1,8,32\n"
    r = client.post(
        f"/api/workloads/import?project_id={PROJECT_ID}",
        files={"file": ("vms.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["imported_count"] == 1
    assert data["workloads"][0]["name"] == "server1"


def test_import_csv_row_with_missing_name_recorded_as_error():
    # Row 2 has no name — should be counted as failed
    csv_content = b"name,type\nweb01,vm\n,container\n"
    r = client.post(
        f"/api/workloads/import?project_id={PROJECT_ID}",
        files={"file": ("bad.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["imported_count"] == 1
    assert data["failed_count"] == 1
    assert len(data["errors"]) == 1


# ---------------------------------------------------------------------------
# POST /api/workloads/import — JSON
# ---------------------------------------------------------------------------

def test_import_json_basic():
    payload = [{"name": "svc1", "type": "web-app"}, {"name": "svc2", "type": "database"}]
    r = client.post(
        f"/api/workloads/import?project_id={PROJECT_ID}",
        files={
            "file": ("workloads.json", io.BytesIO(json.dumps(payload).encode()), "application/json")
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["imported_count"] == 2
    assert data["failed_count"] == 0


def test_import_json_wrapped():
    payload = {"workloads": [{"name": "wrapped1"}]}
    r = client.post(
        f"/api/workloads/import?project_id={PROJECT_ID}",
        files={
            "file": ("w.json", io.BytesIO(json.dumps(payload).encode()), "application/json")
        },
    )
    assert r.status_code == 200
    assert r.json()["imported_count"] == 1


def test_import_empty_file_returns_zero():
    r = client.post(
        f"/api/workloads/import?project_id={PROJECT_ID}",
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
    )
    assert r.status_code == 400


def test_import_missing_project_id_returns_422():
    csv_content = b"name\nweb01\n"
    r = client.post(
        "/api/workloads/import",
        files={"file": ("w.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert r.status_code == 422


def test_import_invalid_json_returns_422():
    r = client.post(
        f"/api/workloads/import?project_id={PROJECT_ID}",
        files={"file": ("bad.json", io.BytesIO(b"not-json"), "application/json")},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /api/workloads/{id}
# ---------------------------------------------------------------------------

def test_patch_workload_no_db_returns_404():
    """In dev mode without DB, PATCH returns 404."""
    r = client.patch("/api/workloads/nonexistent", json={"name": "Updated"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/workloads/{id}
# ---------------------------------------------------------------------------

def test_delete_workload_no_db_returns_success():
    """In dev mode without DB, DELETE returns success message."""
    r = client.delete("/api/workloads/some-id")
    assert r.status_code == 200
    data = r.json()
    assert data["deleted"] is True


# ---------------------------------------------------------------------------
# WorkloadImportResult structure
# ---------------------------------------------------------------------------

def test_import_result_has_required_fields():
    csv_content = b"name\ntest-workload\n"
    r = client.post(
        f"/api/workloads/import?project_id={PROJECT_ID}",
        files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert r.status_code == 200
    data = r.json()
    assert "imported_count" in data
    assert "failed_count" in data
    assert "errors" in data
    assert "workloads" in data
