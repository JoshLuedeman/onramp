"""Adversarial cross-tenant security tests.

Sets up two isolated tenants with separate users, projects, and child
resources, then verifies that every data-access endpoint enforces
row-level tenant isolation — returning 404 (or empty results) when a
user from Tenant A attempts to read, modify, or delete resources
belonging to Tenant B.

Covered resources:
    - Projects
    - Architectures
    - Architecture versions
    - Questionnaire state
    - Compliance results
    - Bicep files
    - Cost budgets / anomalies
    - Deployments
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.auth.entra import get_current_user
from app.db.session import get_db
from app.models.base import Base

SQLITE_URL = "sqlite+aiosqlite:///:memory:"


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------


@pytest.fixture()
async def async_engine():
    """Create a fresh in-memory SQLite engine for each test."""
    engine = create_async_engine(SQLITE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def db_session(async_engine):
    """Provide an async session bound to the test engine."""
    factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with factory() as session:
        yield session


# -- Tenants ------------------------------------------------------------


@pytest.fixture()
async def tenant_a(db_session):
    from app.models.tenant import Tenant

    t = Tenant(
        id="tenant-a-id", name="Tenant A", is_active=True
    )
    db_session.add(t)
    await db_session.flush()
    return t


@pytest.fixture()
async def tenant_b(db_session):
    from app.models.tenant import Tenant

    t = Tenant(
        id="tenant-b-id", name="Tenant B", is_active=True
    )
    db_session.add(t)
    await db_session.flush()
    return t


# -- Users --------------------------------------------------------------


@pytest.fixture()
async def user_a(db_session, tenant_a):
    from app.models.user import User

    u = User(
        id="user-a-id",
        entra_object_id="user-a-oid",
        email="user-a@tenant-a.local",
        display_name="User A",
        tenant_id=tenant_a.id,
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture()
async def user_b(db_session, tenant_b):
    from app.models.user import User

    u = User(
        id="user-b-id",
        entra_object_id="user-b-oid",
        email="user-b@tenant-b.local",
        display_name="User B",
        tenant_id=tenant_b.id,
    )
    db_session.add(u)
    await db_session.flush()
    return u


# -- User claim dicts ---------------------------------------------------


@pytest.fixture()
def user_a_claims(tenant_a, user_a) -> dict:
    """JWT-like claims for Tenant A user."""
    return {
        "sub": user_a.entra_object_id,
        "oid": user_a.entra_object_id,
        "name": user_a.display_name,
        "email": user_a.email,
        "roles": ["architect"],
        "tid": tenant_a.id,
        "tenant_id": tenant_a.id,
    }


@pytest.fixture()
def user_b_claims(tenant_b, user_b) -> dict:
    """JWT-like claims for Tenant B user."""
    return {
        "sub": user_b.entra_object_id,
        "oid": user_b.entra_object_id,
        "name": user_b.display_name,
        "email": user_b.email,
        "roles": ["architect"],
        "tid": tenant_b.id,
        "tenant_id": tenant_b.id,
    }


# -- Projects -----------------------------------------------------------


@pytest.fixture()
async def project_a(db_session, tenant_a, user_a):
    from app.models.project import Project

    p = Project(
        id="project-a-id",
        name="Project A",
        tenant_id=tenant_a.id,
        created_by=user_a.id,
    )
    db_session.add(p)
    await db_session.flush()
    return p


@pytest.fixture()
async def project_b(db_session, tenant_b, user_b):
    from app.models.project import Project

    p = Project(
        id="project-b-id",
        name="Project B",
        tenant_id=tenant_b.id,
        created_by=user_b.id,
    )
    db_session.add(p)
    await db_session.flush()
    return p


# -- Architectures ------------------------------------------------------


@pytest.fixture()
async def architecture_b(db_session, project_b):
    from app.models.architecture import Architecture

    a = Architecture(
        id="arch-b-id",
        project_id=project_b.id,
        architecture_data={
            "management_groups": [],
            "subscriptions": [],
        },
        version=1,
        status="draft",
    )
    db_session.add(a)
    await db_session.flush()
    return a


# -- Architecture versions ----------------------------------------------


@pytest.fixture()
async def arch_version_b(db_session, architecture_b):
    from app.models.architecture_version import ArchitectureVersion

    v = ArchitectureVersion(
        id="archver-b-id",
        architecture_id=architecture_b.id,
        version_number=1,
        architecture_json='{"management_groups": []}',
        change_summary="Initial version",
        created_by="user-b-id",
    )
    db_session.add(v)
    await db_session.flush()
    return v


# -- Compliance results -------------------------------------------------


@pytest.fixture()
async def compliance_result_b(db_session, project_b):
    from app.models.compliance_result import ComplianceResult

    cr = ComplianceResult(
        id="cr-b-id",
        project_id=project_b.id,
        scoring_data={"overall_score": 85},
        frameworks_evaluated=["CIS"],
        overall_score=85,
    )
    db_session.add(cr)
    await db_session.flush()
    return cr


# -- Bicep files --------------------------------------------------------


@pytest.fixture()
async def bicep_file_b(db_session, project_b):
    from app.models.bicep_file import BicepFile

    bf = BicepFile(
        id="bicep-b-id",
        project_id=project_b.id,
        file_name="main.bicep",
        file_path="modules/main.bicep",
        content="targetScope = 'subscription'",
        size_bytes=30,
    )
    db_session.add(bf)
    await db_session.flush()
    return bf


# -- Cost budget --------------------------------------------------------


@pytest.fixture()
async def cost_budget_b(db_session, project_b):
    from app.models.cost import CostBudget

    budget = CostBudget(
        id="budget-b-id",
        project_id=project_b.id,
        budget_name="Test Budget",
        budget_amount=1000.0,
        current_spend=500.0,
        currency="USD",
        threshold_percentage=80.0,
        alert_enabled=True,
    )
    db_session.add(budget)
    await db_session.flush()
    return budget


# -------------------------------------------------------------------
# Test-app builder
# -------------------------------------------------------------------


def _build_test_app(
    user_override: dict,
    db_session_override: AsyncSession,
    routers: list,
) -> FastAPI:
    """Build a minimal FastAPI app wired to the test DB and user."""
    test_app = FastAPI()
    for r in routers:
        test_app.include_router(r)

    async def _override_user():
        return user_override

    async def _override_db():
        yield db_session_override

    test_app.dependency_overrides[get_current_user] = (
        _override_user
    )
    test_app.dependency_overrides[get_db] = _override_db
    return test_app


# ===================================================================
# PROJECTS — verify existing tenant isolation
# ===================================================================


class TestProjectIsolation:
    """User A must not access Tenant B's projects."""

    @pytest.mark.asyncio
    async def test_list_excludes_other_tenant(
        self, db_session, user_a_claims, project_a, project_b,
    ):
        from app.api.routes.projects import router

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.get("/api/projects")
            assert resp.status_code == 200
            ids = [p["id"] for p in resp.json()["projects"]]
            assert "project-a-id" in ids
            assert "project-b-id" not in ids

    @pytest.mark.asyncio
    async def test_read_cross_tenant_returns_404(
        self, db_session, user_a_claims, project_b,
    ):
        from app.api.routes.projects import router

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.get(
                f"/api/projects/{project_b.id}"
            )
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_cross_tenant_returns_404(
        self, db_session, user_a_claims, project_b,
    ):
        from app.api.routes.projects import router

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.put(
                f"/api/projects/{project_b.id}",
                json={"name": "Hacked"},
            )
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_cross_tenant_returns_403(
        self, db_session, user_a_claims, project_b,
    ):
        """DELETE requires admin role; architect gets 403 before tenant check."""
        from app.api.routes.projects import router

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.delete(
                f"/api/projects/{project_b.id}"
            )
            assert resp.status_code == 403


# ===================================================================
# ARCHITECTURE — generate + get must enforce tenant
# ===================================================================


class TestArchitectureIsolation:
    """Tenant A must not read/write Tenant B's architectures."""

    @pytest.mark.asyncio
    async def test_get_cross_tenant_returns_null(
        self,
        db_session,
        user_a_claims,
        architecture_b,
    ):
        from app.api.routes.architecture import router

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.get(
                f"/api/architecture/project/"
                f"{architecture_b.project_id}"
            )
            assert resp.status_code == 200
            assert resp.json()["architecture"] is None

    @pytest.mark.asyncio
    async def test_generate_cross_tenant_returns_404(
        self, db_session, user_a_claims, project_b,
    ):
        from app.api.routes.architecture import router

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.post(
                "/api/architecture/generate",
                json={
                    "answers": {"q1": "a1"},
                    "use_archetype": True,
                    "use_ai": False,
                    "project_id": project_b.id,
                },
            )
            assert resp.status_code == 404


# ===================================================================
# ARCHITECTURE VERSIONS — all routes must enforce tenant
# ===================================================================


class TestArchVersionIsolation:
    """Tenant A must not access Tenant B's architecture versions."""

    @pytest.mark.asyncio
    async def test_list_versions_cross_tenant_404(
        self,
        db_session,
        user_a_claims,
        arch_version_b,
    ):
        from app.api.routes.arch_versions import router

        arch_id = arch_version_b.architecture_id
        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.get(
                f"/api/architectures/{arch_id}/versions"
            )
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_version_cross_tenant_404(
        self,
        db_session,
        user_a_claims,
        arch_version_b,
    ):
        from app.api.routes.arch_versions import router

        arch_id = arch_version_b.architecture_id
        ver = arch_version_b.version_number
        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.get(
                f"/api/architectures/{arch_id}"
                f"/versions/{ver}"
            )
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_diff_versions_cross_tenant_404(
        self,
        db_session,
        user_a_claims,
        arch_version_b,
    ):
        from app.api.routes.arch_versions import router

        arch_id = arch_version_b.architecture_id
        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.get(
                f"/api/architectures/{arch_id}"
                "/versions/diff",
                params={"from": 1, "to": 1},
            )
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_restore_version_cross_tenant_404(
        self,
        db_session,
        user_a_claims,
        arch_version_b,
    ):
        from app.api.routes.arch_versions import router

        arch_id = arch_version_b.architecture_id
        ver = arch_version_b.version_number
        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.post(
                f"/api/architectures/{arch_id}"
                f"/versions/{ver}/restore"
            )
            assert resp.status_code == 404


# ===================================================================
# QUESTIONNAIRE STATE — save/load must enforce tenant
# ===================================================================


class TestQuestionnaireStateIsolation:
    """Tenant A must not read/write Tenant B's questionnaire state."""

    @pytest.mark.asyncio
    async def test_save_cross_tenant_returns_404(
        self, db_session, user_a_claims, project_b,
    ):
        from app.api.routes.questionnaire_state import router

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.post(
                "/api/questionnaire/state/save",
                json={
                    "project_id": project_b.id,
                    "answers": {"q1": "evil"},
                },
            )
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_load_cross_tenant_returns_404(
        self, db_session, user_a_claims, project_b,
    ):
        from app.api.routes.questionnaire_state import router

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.get(
                f"/api/questionnaire/state/load/"
                f"{project_b.id}"
            )
            assert resp.status_code == 404


# ===================================================================
# COMPLIANCE / SCORING — verify existing tenant isolation
# ===================================================================


class TestComplianceIsolation:
    """Tenant A must not see Tenant B's compliance results."""

    @pytest.mark.asyncio
    async def test_get_results_cross_tenant_empty(
        self,
        db_session,
        user_a_claims,
        compliance_result_b,
        project_b,
    ):
        from app.api.routes.scoring import router

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.get(
                f"/api/scoring/project/{project_b.id}"
            )
            assert resp.status_code == 200
            assert resp.json()["results"] == []


# ===================================================================
# BICEP — verify existing tenant isolation
# ===================================================================


class TestBicepIsolation:
    """Tenant A must not see Tenant B's Bicep files."""

    @pytest.mark.asyncio
    async def test_get_files_cross_tenant_empty(
        self,
        db_session,
        user_a_claims,
        bicep_file_b,
        project_b,
    ):
        from app.api.routes.bicep import router

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.get(
                f"/api/bicep/project/{project_b.id}"
            )
            assert resp.status_code == 200
            assert resp.json()["files"] == []


# ===================================================================
# COST — budget and anomaly routes must enforce tenant
# ===================================================================


class TestCostIsolation:
    """Tenant A must not access Tenant B's cost data."""

    @pytest.mark.asyncio
    async def test_get_budget_cross_tenant_404(
        self,
        db_session,
        user_a_claims,
        cost_budget_b,
        project_b,
    ):
        from app.api.routes.cost import router

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.get(
                f"/api/governance/cost/budget/"
                f"{project_b.id}"
            )
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_budget_cross_tenant_404(
        self, db_session, user_a_claims, project_b,
    ):
        from app.api.routes.cost import router

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.post(
                "/api/governance/cost/budget",
                json={
                    "project_id": project_b.id,
                    "budget_name": "Evil Budget",
                    "budget_amount": 9999.0,
                    "currency": "USD",
                    "threshold_percentage": 80.0,
                    "alert_enabled": True,
                },
            )
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_anomalies_cross_tenant_404(
        self, db_session, user_a_claims, project_b,
    ):
        from app.api.routes.cost import router

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.get(
                f"/api/governance/cost/anomalies/"
                f"{project_b.id}"
            )
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cost_summary_cross_tenant_404(
        self, db_session, user_a_claims, project_b,
    ):
        from app.api.routes.cost import router

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.get(
                f"/api/governance/cost/summary/"
                f"{project_b.id}"
            )
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cost_trend_cross_tenant_404(
        self, db_session, user_a_claims, project_b,
    ):
        from app.api.routes.cost import router

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.get(
                f"/api/governance/cost/trend/"
                f"{project_b.id}"
            )
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_trigger_scan_cross_tenant_404(
        self, db_session, user_a_claims, project_b,
    ):
        from app.api.routes.cost import router

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.post(
                f"/api/governance/cost/scan/"
                f"{project_b.id}"
            )
            assert resp.status_code == 404


# ===================================================================
# DEPLOYMENT — create and access must enforce tenant
# ===================================================================


class TestDeploymentIsolation:
    """Tenant A must not create or access Tenant B deployments."""

    @pytest.mark.asyncio
    async def test_create_cross_tenant_returns_404(
        self, db_session, user_a_claims, project_b,
    ):
        from app.api.routes.deployment import router

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.post(
                "/api/deployment/create",
                json={
                    "project_id": project_b.id,
                    "architecture": {"test": True},
                    "subscription_ids": ["sub-1"],
                },
            )
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_deployment_cross_tenant_404(
        self, db_session, user_a_claims, project_b,
    ):
        """Access a deployment whose project belongs to Tenant B."""
        from app.api.routes.deployment import router
        from app.services.deployment_orchestrator import (
            deployment_orchestrator,
        )

        # Create directly on the in-memory orchestrator
        record = deployment_orchestrator.create_deployment(
            project_b.id, {"test": True}, ["sub-1"]
        )

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.get(
                f"/api/deployment/{record.id}"
            )
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_deployments_cross_tenant_404(
        self, db_session, user_a_claims, project_b,
    ):
        from app.api.routes.deployment import router

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.get(
                "/api/deployment/",
                params={"project_id": project_b.id},
            )
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_rollback_cross_tenant_returns_404(
        self, db_session, user_a_claims, project_b,
    ):
        """Rollback a deployment whose project is Tenant B."""
        from app.api.routes.deployment import router
        from app.services.deployment_orchestrator import (
            deployment_orchestrator,
        )

        record = deployment_orchestrator.create_deployment(
            project_b.id, {"test": True}, ["sub-1"]
        )

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.post(
                f"/api/deployment/{record.id}/rollback"
            )
            assert resp.status_code == 404


# ===================================================================
# POSITIVE — Tenant A CAN access own resources
# ===================================================================


class TestSameTenantAccess:
    """Verify that tenant scoping does not block legitimate access."""

    @pytest.mark.asyncio
    async def test_tenant_a_reads_own_project(
        self, db_session, user_a_claims, project_a,
    ):
        from app.api.routes.projects import router

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.get(
                f"/api/projects/{project_a.id}"
            )
            assert resp.status_code == 200
            assert resp.json()["id"] == project_a.id

    @pytest.mark.asyncio
    async def test_tenant_a_loads_own_questionnaire(
        self, db_session, user_a_claims, project_a,
    ):
        from app.api.routes.questionnaire_state import router

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.get(
                f"/api/questionnaire/state/load/"
                f"{project_a.id}"
            )
            assert resp.status_code == 200
            assert resp.json()["project_id"] == project_a.id

    @pytest.mark.asyncio
    async def test_tenant_a_creates_deployment_own_project(
        self, db_session, user_a_claims, project_a,
    ):
        from app.api.routes.deployment import router

        app = _build_test_app(
            user_a_claims, db_session, [router]
        )
        with TestClient(app) as client:
            resp = client.post(
                "/api/deployment/create",
                json={
                    "project_id": project_a.id,
                    "architecture": {"test": True},
                    "subscription_ids": ["sub-1"],
                },
            )
            assert resp.status_code == 200
