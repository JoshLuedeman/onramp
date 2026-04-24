"""Tests for Pydantic schema validation constraints.

Verifies that Field() constraints, Literal types, and custom validators
correctly reject invalid input with ValidationError.
"""

import pytest
from pydantic import ValidationError

from app.api.routes.deployment import DeployRequest, ValidationRequest
from app.api.routes.scoring import ScoreRequest
from app.schemas.cost import CostBudgetCreate
from app.schemas.policy import PolicyDefinition, PolicyGenerateRequest
from app.schemas.project import ProjectBase, ProjectUpdate
from app.schemas.security import SecurityAnalyzeRequest
from app.schemas.template import (
    TemplateCreate,
    TemplateListResponse,
    TemplateUseRequest,
)
from app.schemas.user import UserBase, UserCreate
from app.schemas.workload import WorkloadCreate

# ── Project schemas ──────────────────────────────────────────────────────


class TestProjectBase:
    """Validation constraints on ProjectBase / ProjectCreate."""

    def test_valid_project(self):
        p = ProjectBase(name="My Project", description="A description")
        assert p.name == "My Project"

    def test_name_min_length_rejects_empty(self):
        with pytest.raises(ValidationError, match="name"):
            ProjectBase(name="")

    def test_name_max_length_rejects_long(self):
        with pytest.raises(ValidationError, match="name"):
            ProjectBase(name="x" * 256)

    def test_name_max_length_accepts_boundary(self):
        p = ProjectBase(name="x" * 255)
        assert len(p.name) == 255

    def test_description_max_length_rejects_long(self):
        with pytest.raises(ValidationError, match="description"):
            ProjectBase(name="Valid", description="x" * 2001)

    def test_description_max_length_accepts_boundary(self):
        p = ProjectBase(name="Valid", description="x" * 2000)
        assert len(p.description) == 2000

    def test_description_none_allowed(self):
        p = ProjectBase(name="Valid")
        assert p.description is None


class TestProjectUpdate:
    """Validation constraints on ProjectUpdate."""

    def test_update_name_rejects_empty(self):
        with pytest.raises(ValidationError, match="name"):
            ProjectUpdate(name="")

    def test_update_name_none_allowed(self):
        p = ProjectUpdate(name=None)
        assert p.name is None

    def test_update_description_max_length(self):
        with pytest.raises(ValidationError, match="description"):
            ProjectUpdate(description="x" * 2001)


# ── User schemas ─────────────────────────────────────────────────────────


class TestUserBase:
    """Validation constraints on UserBase."""

    def test_valid_user(self):
        u = UserBase(email="test@example.com", display_name="Test User")
        assert u.role == "viewer"

    def test_email_rejects_no_at(self):
        with pytest.raises(ValidationError, match="email"):
            UserBase(email="invalid-email", display_name="Test")

    def test_email_rejects_empty(self):
        with pytest.raises(ValidationError, match="email"):
            UserBase(email="", display_name="Test")

    def test_email_rejects_no_domain(self):
        with pytest.raises(ValidationError, match="email"):
            UserBase(email="user@", display_name="Test")

    def test_display_name_rejects_empty(self):
        with pytest.raises(ValidationError, match="display_name"):
            UserBase(email="test@example.com", display_name="")

    def test_display_name_max_length(self):
        with pytest.raises(ValidationError, match="display_name"):
            UserBase(email="test@example.com", display_name="x" * 256)

    def test_role_literal_accepts_valid(self):
        for role in ("admin", "architect", "viewer"):
            u = UserBase(email="a@b.com", display_name="A", role=role)
            assert u.role == role

    def test_role_literal_rejects_invalid(self):
        with pytest.raises(ValidationError, match="role"):
            UserBase(email="a@b.com", display_name="A", role="superadmin")


class TestUserCreate:
    """Validation constraints on UserCreate."""

    def test_entra_object_id_rejects_empty(self):
        with pytest.raises(ValidationError, match="entra_object_id"):
            UserCreate(
                email="a@b.com",
                display_name="A",
                entra_object_id="",
                tenant_id="tid",
            )

    def test_tenant_id_rejects_empty(self):
        with pytest.raises(ValidationError, match="tenant_id"):
            UserCreate(
                email="a@b.com",
                display_name="A",
                entra_object_id="oid",
                tenant_id="",
            )


# ── Template schemas ─────────────────────────────────────────────────────


class TestTemplateCreate:
    """Validation constraints on TemplateCreate."""

    def test_valid_template(self):
        t = TemplateCreate(
            name="My Template",
            industry="Finance",
            architecture_json='{"key": "value"}',
        )
        assert t.name == "My Template"

    def test_name_rejects_empty(self):
        with pytest.raises(ValidationError, match="name"):
            TemplateCreate(name="", industry="Finance", architecture_json="{}")

    def test_industry_rejects_empty(self):
        with pytest.raises(ValidationError, match="industry"):
            TemplateCreate(name="T", industry="", architecture_json="{}")

    def test_architecture_json_rejects_empty(self):
        with pytest.raises(ValidationError, match="architecture_json"):
            TemplateCreate(name="T", industry="Finance", architecture_json="")

    def test_description_max_length(self):
        with pytest.raises(ValidationError, match="description"):
            TemplateCreate(
                name="T",
                industry="Finance",
                architecture_json="{}",
                description="x" * 2001,
            )


class TestTemplateListResponse:
    """Validation constraints on pagination fields."""

    def test_page_rejects_zero(self):
        with pytest.raises(ValidationError, match="page"):
            TemplateListResponse(templates=[], total=0, page=0, page_size=10)

    def test_page_size_rejects_zero(self):
        with pytest.raises(ValidationError, match="page_size"):
            TemplateListResponse(templates=[], total=0, page=1, page_size=0)


class TestTemplateUseRequest:
    """Validation constraints on TemplateUseRequest."""

    def test_project_id_rejects_empty(self):
        with pytest.raises(ValidationError, match="project_id"):
            TemplateUseRequest(project_id="")


# ── Workload schemas ─────────────────────────────────────────────────────


class TestWorkloadCreate:
    """Validation constraints on WorkloadCreate."""

    def test_valid_workload(self):
        w = WorkloadCreate(project_id="p1", name="Web Server")
        assert w.type == "other"

    def test_project_id_rejects_empty(self):
        with pytest.raises(ValidationError, match="project_id"):
            WorkloadCreate(project_id="", name="Web Server")

    def test_name_rejects_empty(self):
        with pytest.raises(ValidationError, match="name"):
            WorkloadCreate(project_id="p1", name="")

    def test_cpu_cores_rejects_zero(self):
        with pytest.raises(ValidationError, match="cpu_cores"):
            WorkloadCreate(project_id="p1", name="W", cpu_cores=0)

    def test_memory_gb_rejects_zero(self):
        with pytest.raises(ValidationError, match="memory_gb"):
            WorkloadCreate(project_id="p1", name="W", memory_gb=0)

    def test_storage_gb_rejects_negative(self):
        with pytest.raises(ValidationError, match="storage_gb"):
            WorkloadCreate(project_id="p1", name="W", storage_gb=-1)

    def test_notes_max_length(self):
        with pytest.raises(ValidationError, match="notes"):
            WorkloadCreate(project_id="p1", name="W", notes="x" * 5001)


# ── Security schemas ─────────────────────────────────────────────────────


class TestSecurityAnalyzeRequest:
    """Validation constraints on SecurityAnalyzeRequest."""

    def test_valid_request(self):
        r = SecurityAnalyzeRequest(architecture={"key": "value"})
        assert r.use_ai is False

    def test_architecture_rejects_empty_dict(self):
        with pytest.raises(ValidationError, match="architecture"):
            SecurityAnalyzeRequest(architecture={})


# ── Policy schemas ───────────────────────────────────────────────────────


class TestPolicyGenerateRequest:
    """Validation constraints on PolicyGenerateRequest."""

    def test_valid_request(self):
        r = PolicyGenerateRequest(description="Deny public IPs")
        assert r.context is None

    def test_description_rejects_empty(self):
        with pytest.raises(ValidationError, match="description"):
            PolicyGenerateRequest(description="")

    def test_description_max_length(self):
        with pytest.raises(ValidationError, match="description"):
            PolicyGenerateRequest(description="x" * 5001)


class TestPolicyDefinition:
    """Validation constraints on PolicyDefinition."""

    def test_name_rejects_empty(self):
        with pytest.raises(ValidationError, match="name"):
            PolicyDefinition(name="")

    def test_name_max_length(self):
        with pytest.raises(ValidationError, match="name"):
            PolicyDefinition(name="x" * 256)


# ── Cost schemas ─────────────────────────────────────────────────────────


class TestCostBudgetCreate:
    """Validation constraints on CostBudgetCreate."""

    def test_valid_budget(self):
        b = CostBudgetCreate(
            project_id="p1", budget_name="Monthly", budget_amount=1000.0
        )
        assert b.currency == "USD"

    def test_project_id_rejects_empty(self):
        with pytest.raises(ValidationError, match="project_id"):
            CostBudgetCreate(project_id="", budget_name="B", budget_amount=100)

    def test_budget_name_rejects_empty(self):
        with pytest.raises(ValidationError, match="budget_name"):
            CostBudgetCreate(project_id="p1", budget_name="", budget_amount=100)

    def test_budget_amount_rejects_zero(self):
        with pytest.raises(ValidationError, match="budget_amount"):
            CostBudgetCreate(project_id="p1", budget_name="B", budget_amount=0)

    def test_budget_amount_rejects_negative(self):
        with pytest.raises(ValidationError, match="budget_amount"):
            CostBudgetCreate(project_id="p1", budget_name="B", budget_amount=-50)

    def test_threshold_percentage_rejects_over_100(self):
        with pytest.raises(ValidationError, match="threshold_percentage"):
            CostBudgetCreate(
                project_id="p1",
                budget_name="B",
                budget_amount=100,
                threshold_percentage=101,
            )

    def test_currency_rejects_too_long(self):
        with pytest.raises(ValidationError, match="currency"):
            CostBudgetCreate(
                project_id="p1",
                budget_name="B",
                budget_amount=100,
                currency="USDX",
            )


# ── Deployment schemas (inline in routes) ────────────────────────────────


class TestDeployRequest:
    """Validation constraints on DeployRequest."""

    def test_valid_request(self):
        r = DeployRequest(
            project_id="p1",
            architecture={"key": "value"},
            subscription_ids=["sub-1"],
        )
        assert r.project_id == "p1"

    def test_project_id_rejects_empty(self):
        with pytest.raises(ValidationError, match="project_id"):
            DeployRequest(
                project_id="",
                architecture={"k": "v"},
                subscription_ids=["s1"],
            )

    def test_architecture_rejects_empty_dict(self):
        with pytest.raises(ValidationError, match="architecture"):
            DeployRequest(
                project_id="p1",
                architecture={},
                subscription_ids=["s1"],
            )

    def test_subscription_ids_rejects_empty_list(self):
        with pytest.raises(ValidationError, match="subscription_ids"):
            DeployRequest(
                project_id="p1",
                architecture={"k": "v"},
                subscription_ids=[],
            )


class TestValidationRequest:
    """Validation constraints on ValidationRequest."""

    def test_subscription_id_rejects_empty(self):
        with pytest.raises(ValidationError, match="subscription_id"):
            ValidationRequest(subscription_id="")


# ── Scoring schemas (inline in routes) ───────────────────────────────────


class TestScoreRequest:
    """Validation constraints on ScoreRequest."""

    def test_valid_request(self):
        r = ScoreRequest(
            architecture={"key": "value"},
            frameworks=["SOC2"],
        )
        assert r.use_ai is True

    def test_architecture_rejects_empty_dict(self):
        with pytest.raises(ValidationError, match="architecture"):
            ScoreRequest(architecture={}, frameworks=["SOC2"])

    def test_frameworks_rejects_empty_list(self):
        with pytest.raises(ValidationError, match="frameworks"):
            ScoreRequest(architecture={"k": "v"}, frameworks=[])
