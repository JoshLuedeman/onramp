"""Test that all models can be imported and have correct table names."""


def test_all_models_importable():
    from app.models import (
        Base,
        Tenant,
        User,
        Project,
        QuestionCategory,
        Question,
        QuestionnaireResponse,
        Architecture,
        Deployment,
        ComplianceFramework,
        ComplianceControl,
    )

    assert Tenant.__tablename__ == "tenants"
    assert User.__tablename__ == "users"
    assert Project.__tablename__ == "projects"
    assert QuestionCategory.__tablename__ == "question_categories"
    assert Question.__tablename__ == "questions"
    assert QuestionnaireResponse.__tablename__ == "questionnaire_responses"
    assert Architecture.__tablename__ == "architectures"
    assert Deployment.__tablename__ == "deployments"
    assert ComplianceFramework.__tablename__ == "compliance_frameworks"
    assert ComplianceControl.__tablename__ == "compliance_controls"

    # Verify all tables are registered in metadata
    table_names = Base.metadata.tables.keys()
    assert len(list(table_names)) == 10


def test_all_schemas_importable():
    from app.schemas import (
        TenantCreate,
        TenantResponse,
        UserCreate,
        UserResponse,
        ProjectCreate,
        ProjectResponse,
    )

    tenant = TenantCreate(name="Test Tenant")
    assert tenant.name == "Test Tenant"

    project = ProjectCreate(name="Test Project", description="Test")
    assert project.name == "Test Project"
