"""Tests for the questionnaire engine."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.questionnaire import questionnaire_service

client = TestClient(app)


def test_get_all_questions():
    questions = questionnaire_service.get_all_questions()
    assert len(questions) > 20
    # Verify sorted by order
    orders = [q["order"] for q in questions]
    assert orders == sorted(orders)


def test_get_categories():
    categories = questionnaire_service.get_categories()
    category_names = [c["id"] for c in categories]
    assert "organization" in category_names
    assert "identity" in category_names
    assert "networking" in category_names
    assert "security" in category_names
    assert "governance" in category_names
    assert "compliance" in category_names


def test_get_next_question_empty_state():
    next_q = questionnaire_service.get_next_question({})
    assert next_q is not None
    assert next_q["order"] == 1


def test_get_next_question_skips_answered():
    answered = {"org_name": "Test Corp"}
    next_q = questionnaire_service.get_next_question(answered)
    assert next_q is not None
    assert next_q["id"] != "org_name"


def test_get_progress():
    progress = questionnaire_service.get_progress({"org_name": "Test", "org_size": "medium"})
    assert progress["answered"] == 2
    assert progress["total"] > 20
    assert progress["percent_complete"] > 0


def test_validate_text_answer():
    assert questionnaire_service.validate_answer("org_name", "Contoso") is True
    assert questionnaire_service.validate_answer("org_name", "") is False


def test_validate_single_choice():
    assert questionnaire_service.validate_answer("org_size", "medium") is True
    assert questionnaire_service.validate_answer("org_size", "invalid") is False


def test_validate_multi_choice():
    assert questionnaire_service.validate_answer("compliance_frameworks", ["soc2", "hipaa"]) is True
    assert questionnaire_service.validate_answer("compliance_frameworks", ["invalid"]) is False


def test_api_categories():
    response = client.get("/api/questionnaire/categories")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data


def test_api_all_questions():
    response = client.get("/api/questionnaire/questions")
    assert response.status_code == 200
    data = response.json()
    assert "questions" in data
    assert len(data["questions"]) > 20


def test_api_next_question():
    response = client.post("/api/questionnaire/next", json={"answers": {}})
    assert response.status_code == 200
    data = response.json()
    assert data["complete"] is False
    assert data["question"] is not None


def test_api_progress():
    response = client.post(
        "/api/questionnaire/progress",
        json={"answers": {"org_name": "Test", "org_size": "small"}},
    )
    assert response.status_code == 200
    assert response.json()["answered"] == 2
