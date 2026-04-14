"""Extended tests for SQLAlchemy models."""
from app.models import (
    Architecture,
    Base,
    ComplianceControl,
    ComplianceFramework,
    Deployment,
    Project,
    Question,
    QuestionCategory,
    QuestionnaireResponse,
    Tenant,
    User,
)


def test_model_columns_tenant():
    cols = {c.name for c in Tenant.__table__.columns}
    assert "id" in cols
    assert "name" in cols
    assert "is_active" in cols

def test_model_columns_user():
    cols = {c.name for c in User.__table__.columns}
    assert "email" in cols
    assert "display_name" in cols
    assert "entra_object_id" in cols
    assert "role" in cols

def test_model_columns_project():
    cols = {c.name for c in Project.__table__.columns}
    assert "name" in cols
    assert "status" in cols
    assert "created_by" in cols

def test_model_columns_architecture():
    cols = {c.name for c in Architecture.__table__.columns}
    assert "project_id" in cols
    assert "architecture_data" in cols
    assert "ai_reasoning" in cols

def test_model_columns_deployment():
    cols = {c.name for c in Deployment.__table__.columns}
    assert "project_id" in cols
    assert "status" in cols

def test_model_columns_questionnaire_response():
    cols = {c.name for c in QuestionnaireResponse.__table__.columns}
    assert "question_id" in cols
    assert "answer_value" in cols
    assert "project_id" in cols

def test_model_columns_compliance():
    cols = {c.name for c in ComplianceFramework.__table__.columns}
    assert "name" in cols
    ctrl_cols = {c.name for c in ComplianceControl.__table__.columns}
    assert "framework_id" in ctrl_cols
    assert "control_id" in ctrl_cols

def test_base_metadata_has_all_tables():
    table_names = Base.metadata.tables.keys()
    expected = ["tenants", "users", "projects", "architectures", "deployments"]
    for t in expected:
        assert t in table_names

def test_question_model():
    cols = {c.name for c in Question.__table__.columns}
    assert "category_id" in cols
    assert "text" in cols

def test_question_category_model():
    cols = {c.name for c in QuestionCategory.__table__.columns}
    assert "name" in cols
    assert "caf_design_area" in cols


def test_generate_uuid():
    """generate_uuid returns a valid UUID string."""
    from app.models.base import generate_uuid
    result = generate_uuid()
    assert isinstance(result, str)
    assert len(result) == 36
    assert result.count("-") == 4
