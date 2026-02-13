"""Tests for database seed module."""

import pytest


def test_seed_module_importable():
    from app.db.seed import seed_database
    assert callable(seed_database)


def test_seed_functions_importable():
    from app.db.seed import (
        _seed_question_categories,
        _seed_questions,
        _seed_compliance_frameworks,
    )
    assert callable(_seed_question_categories)
    assert callable(_seed_questions)
    assert callable(_seed_compliance_frameworks)


def test_questionnaire_questions_have_required_fields():
    from app.services.questionnaire import questionnaire_service

    questions = questionnaire_service.get_all_questions()
    assert len(questions) > 0
    for q in questions:
        assert "id" in q, f"Question missing 'id': {q}"
        assert "text" in q, f"Question missing 'text': {q}"
        assert "type" in q, f"Question missing 'type': {q}"
        assert isinstance(q["id"], str)
        assert isinstance(q["text"], str)


def test_questionnaire_questions_have_unique_ids():
    from app.services.questionnaire import questionnaire_service

    questions = questionnaire_service.get_all_questions()
    ids = [q["id"] for q in questions]
    assert len(ids) == len(set(ids)), "Duplicate question IDs found"


def test_questionnaire_categories_have_required_fields():
    from app.services.questionnaire import questionnaire_service

    categories = questionnaire_service.get_categories()
    assert len(categories) > 0
    for cat in categories:
        assert "id" in cat
        assert "name" in cat
        assert isinstance(cat["id"], str)
        assert isinstance(cat["name"], str)


def test_question_categories_match_known_categories():
    from app.services.questionnaire import questionnaire_service

    categories = questionnaire_service.get_categories()
    cat_ids = {c["id"] for c in categories}
    questions = questionnaire_service.get_all_questions()
    for q in questions:
        cat = q.get("category", "")
        if cat:
            assert cat in cat_ids, f"Question '{q['id']}' has unknown category '{cat}'"


def test_compliance_frameworks_have_required_fields():
    from app.services.compliance_data import COMPLIANCE_FRAMEWORKS

    assert len(COMPLIANCE_FRAMEWORKS) > 0
    for fw in COMPLIANCE_FRAMEWORKS:
        assert "name" in fw
        assert "short_name" in fw
        assert isinstance(fw["name"], str)
        assert isinstance(fw["short_name"], str)


def test_compliance_framework_controls_have_required_fields():
    from app.services.compliance_data import COMPLIANCE_FRAMEWORKS

    for fw in COMPLIANCE_FRAMEWORKS:
        for ctrl in fw.get("controls", []):
            assert "control_id" in ctrl, f"Control in '{fw['name']}' missing control_id"
            assert "title" in ctrl, f"Control in '{fw['name']}' missing title"
            assert "severity" in ctrl, f"Control in '{fw['name']}' missing severity"
            assert ctrl["severity"] in (
                "low", "medium", "high", "critical",
            ), f"Invalid severity '{ctrl['severity']}' in control '{ctrl['control_id']}'"


@pytest.mark.asyncio
async def test_seed_database_no_db():
    """seed_database exits early when no DB configured."""
    from unittest.mock import patch
    with patch("app.db.seed.get_session_factory", return_value=None):
        from app.db.seed import seed_database
        await seed_database()  # Should not raise
