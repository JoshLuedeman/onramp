"""Tests for migration wave API routes."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PROJECT_ID = "proj-test-migration"


class TestGenerateWavesNoDB:
    """Test wave generation endpoints when no DB is configured."""

    def test_generate_waves_no_db(self):
        payload = {
            "project_id": PROJECT_ID,
            "strategy": "complexity_first",
            "plan_name": "Test Plan",
        }
        r = client.post("/api/migration/waves/generate", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == PROJECT_ID
        assert data["name"] == "Test Plan"
        assert data["strategy"] == "complexity_first"
        assert data["is_active"] is True
        assert isinstance(data["waves"], list)
        assert isinstance(data["warnings"], list)

    def test_generate_waves_priority_strategy_no_db(self):
        payload = {
            "project_id": PROJECT_ID,
            "strategy": "priority_first",
            "plan_name": "Priority Plan",
            "max_wave_size": 5,
        }
        r = client.post("/api/migration/waves/generate", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["strategy"] == "priority_first"


class TestListWavesNoDB:
    def test_list_waves_no_db(self):
        r = client.get(
            "/api/migration/waves",
            params={"project_id": PROJECT_ID},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == PROJECT_ID
        assert data["waves"] == []

    def test_list_waves_missing_project_id(self):
        r = client.get("/api/migration/waves")
        assert r.status_code == 422


class TestExportNoDB:
    def test_export_csv_no_db(self):
        payload = {"project_id": PROJECT_ID, "format": "csv"}
        r = client.post("/api/migration/waves/export", json=payload)
        assert r.status_code == 200
        assert "Wave" in r.text
        assert "Workload" in r.text

    def test_export_markdown_no_db(self):
        payload = {"project_id": PROJECT_ID, "format": "markdown"}
        r = client.post("/api/migration/waves/export", json=payload)
        assert r.status_code == 200
        assert "Migration Wave Plan" in r.text


class TestValidateNoDB:
    def test_validate_no_db(self):
        payload = {"project_id": PROJECT_ID}
        r = client.post("/api/migration/waves/validate", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == PROJECT_ID
        assert data["waves"] == []
        assert data["warnings"] == []


class TestMoveWorkloadNoDB:
    def test_move_workload_no_db(self):
        payload = {
            "workload_id": "w1",
            "target_wave_id": "wave-1",
            "position": 0,
        }
        r = client.post("/api/migration/waves/move", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert "waves" in data
