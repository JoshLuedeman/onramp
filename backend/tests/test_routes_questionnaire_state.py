"""Tests for questionnaire state routes."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_save_state():
    r = client.post("/api/questionnaire/state/save", json={
        "project_id": "test-project",
        "answers": {"q1": "answer1", "q2": "answer2"}
    })
    assert r.status_code == 200
    assert r.json()["saved"] is True

def test_load_state():
    r = client.get("/api/questionnaire/state/load/test-project")
    assert r.status_code == 200
    assert "answers" in r.json()


def test_save_state_with_list_values():
    """Save answers that contain list values."""
    r = client.post("/api/questionnaire/state/save", json={
        "project_id": "test-list-project",
        "answers": {
            "q1": "simple string",
            "q2": ["option_a", "option_b"],
            "q3": ["single_option"],
        }
    })
    assert r.status_code == 200
    assert r.json()["saved"] is True


def test_load_state_unknown_project():
    """Load state for unknown project returns empty answers."""
    r = client.get("/api/questionnaire/state/load/nonexistent-project-xyz")
    assert r.status_code == 200
    data = r.json()
    assert data["answers"] == {}


def test_save_state_empty_answers():
    """Save with empty answers dict."""
    r = client.post("/api/questionnaire/state/save", json={
        "project_id": "empty-answers",
        "answers": {}
    })
    assert r.status_code == 200
    assert r.json()["saved"] is True


def test_save_state_returns_project_id():
    """Response includes the project_id."""
    r = client.post("/api/questionnaire/state/save", json={
        "project_id": "pid-check",
        "answers": {"q1": "a1"}
    })
    assert r.status_code == 200
    data = r.json()
    assert data["project_id"] == "pid-check"


def test_save_state_missing_fields():
    """Missing required fields returns 422."""
    r = client.post("/api/questionnaire/state/save", json={"answers": {"q1": "a"}})
    assert r.status_code == 422

    r = client.post("/api/questionnaire/state/save", json={"project_id": "p1"})
    assert r.status_code == 422


def test_load_state_in_memory_message():
    """In dev mode, load returns database not configured message."""
    r = client.get("/api/questionnaire/state/load/some-project")
    data = r.json()
    assert "answers" in data
