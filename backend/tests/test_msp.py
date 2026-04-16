"""Comprehensive tests for the MSP dashboard feature.

Covers:
    - Pydantic schema validation (TenantOverview, MSPOverviewResponse,
      TenantHealthResponse, ComplianceSummaryResponse, DeploymentSummary,
      TenantComplianceScore)
    - MSPService mock-data paths (DB = None)
    - MSPService DB-backed paths with in-memory SQLite
    - API route tests (overview, tenant health, compliance summary)
    - RBAC permission checks (msp_admin allowed, viewer rejected)
    - Edge cases (no tenants, inactive tenants, unknown tenant_id)
"""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.routes.msp import router as msp_router
from app.auth.entra import get_current_user
from app.db.session import get_db
from app.models.base import Base
from app.models.deployment import Deployment
from app.models.project import Project
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.msp import (
    ComplianceSummaryResponse,
    DeploymentSummary,
    MSPOverviewResponse,
    TenantComplianceScore,
    TenantHealthResponse,
    TenantOverview,
)
from app.services.msp_service import (
    MSPService,
    _mock_compliance_summary,
    _mock_overview,
    _mock_tenant_health,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SQLITE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture()
async def async_engine():
    engine = create_async_engine(SQLITE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def db_session(async_engine):
    factory = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        yield session


@pytest.fixture()
def msp_admin_user() -> dict:
    return {
        "sub": "msp-admin-oid",
        "name": "MSP Admin",
        "email": "msp-admin@onramp.local",
        "roles": ["msp_admin"],
        "tenant_id": "",
    }


@pytest.fixture()
def admin_user() -> dict:
    return {
        "sub": "admin-oid",
        "name": "Admin User",
        "email": "admin@onramp.local",
        "roles": ["admin"],
        "tenant_id": "",
    }


@pytest.fixture()
def viewer_user() -> dict:
    return {
        "sub": "viewer-oid",
        "name": "Viewer User",
        "email": "viewer@onramp.local",
        "roles": ["viewer"],
        "tenant_id": "",
    }


@pytest.fixture()
def architect_user() -> dict:
    return {
        "sub": "architect-oid",
        "name": "Architect User",
        "email": "architect@onramp.local",
        "roles": ["architect"],
        "tenant_id": "",
    }


def _build_test_app(
    user_override: dict,
    db_session_override: AsyncSession | None,
) -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(msp_router)

    async def _override_user():
        return user_override

    async def _override_db():
        yield db_session_override

    test_app.dependency_overrides[get_current_user] = _override_user
    test_app.dependency_overrides[get_db] = _override_db
    return test_app


async def _seed_tenant(
    session: AsyncSession,
    *,
    name: str = "Test Tenant",
    is_active: bool = True,
) -> Tenant:
    tid = str(uuid.uuid4())
    tenant = Tenant(id=tid, name=name, is_active=is_active)
    session.add(tenant)
    await session.flush()
    return tenant


async def _seed_user(
    session: AsyncSession, tenant: Tenant
) -> User:
    uid = str(uuid.uuid4())
    user = User(
        id=uid,
        entra_object_id=str(uuid.uuid4()),
        email=f"{uid[:8]}@test.local",
        display_name="Test User",
        tenant_id=tenant.id,
    )
    session.add(user)
    await session.flush()
    return user


async def _seed_project(
    session: AsyncSession,
    tenant: Tenant,
    user: User,
    *,
    name: str = "Test Project",
) -> Project:
    pid = str(uuid.uuid4())
    project = Project(
        id=pid,
        name=name,
        tenant_id=tenant.id,
        created_by=user.id,
    )
    session.add(project)
    await session.flush()
    return project


async def _seed_deployment(
    session: AsyncSession,
    project: Project,
    user: User,
    *,
    dep_status: str = "succeeded",
) -> Deployment:
    did = str(uuid.uuid4())
    dep = Deployment(
        id=did,
        project_id=project.id,
        initiated_by=user.id,
        target_subscription_id=str(uuid.uuid4()),
        status=dep_status,
    )
    session.add(dep)
    await session.flush()
    return dep


# ===================================================================
# Schema Validation Tests
# ===================================================================


class TestTenantOverviewSchema:
    def test_valid_overview(self):
        ov = TenantOverview(
            tenant_id="t-1",
            name="Acme",
            status="active",
            compliance_score=85.0,
            project_count=5,
            deployment_count=10,
            active_deployments=2,
        )
        assert ov.tenant_id == "t-1"
        assert ov.compliance_score == 85.0

    def test_overview_with_last_activity(self):
        now = datetime.now(timezone.utc)
        ov = TenantOverview(
            tenant_id="t-2",
            name="Beta",
            status="active",
            last_activity=now,
            compliance_score=70.0,
            project_count=3,
            deployment_count=7,
            active_deployments=1,
        )
        assert ov.last_activity == now

    def test_overview_without_last_activity(self):
        ov = TenantOverview(
            tenant_id="t-3",
            name="Gamma",
            status="inactive",
            compliance_score=60.0,
            project_count=0,
            deployment_count=0,
            active_deployments=0,
        )
        assert ov.last_activity is None

    def test_overview_score_lower_bound(self):
        ov = TenantOverview(
            tenant_id="t-4",
            name="Delta",
            status="active",
            compliance_score=0.0,
            project_count=0,
            deployment_count=0,
            active_deployments=0,
        )
        assert ov.compliance_score == 0.0

    def test_overview_score_upper_bound(self):
        ov = TenantOverview(
            tenant_id="t-5",
            name="Epsilon",
            status="active",
            compliance_score=100.0,
            project_count=0,
            deployment_count=0,
            active_deployments=0,
        )
        assert ov.compliance_score == 100.0

    def test_overview_negative_score_rejected(self):
        with pytest.raises(Exception):
            TenantOverview(
                tenant_id="t-6",
                name="Fail",
                status="active",
                compliance_score=-1.0,
                project_count=0,
                deployment_count=0,
                active_deployments=0,
            )

    def test_overview_score_over_100_rejected(self):
        with pytest.raises(Exception):
            TenantOverview(
                tenant_id="t-7",
                name="Fail",
                status="active",
                compliance_score=101.0,
                project_count=0,
                deployment_count=0,
                active_deployments=0,
            )

    def test_overview_negative_project_count_rejected(self):
        with pytest.raises(Exception):
            TenantOverview(
                tenant_id="t-8",
                name="Fail",
                status="active",
                compliance_score=50.0,
                project_count=-1,
                deployment_count=0,
                active_deployments=0,
            )


class TestMSPOverviewResponseSchema:
    def test_valid_response(self):
        resp = MSPOverviewResponse(
            tenants=[],
            total_tenants=0,
            total_projects=0,
            avg_compliance_score=0.0,
        )
        assert resp.total_tenants == 0
        assert resp.tenants == []

    def test_response_with_tenants(self):
        tenant = TenantOverview(
            tenant_id="t-1",
            name="Acme",
            status="active",
            compliance_score=90.0,
            project_count=3,
            deployment_count=5,
            active_deployments=1,
        )
        resp = MSPOverviewResponse(
            tenants=[tenant],
            total_tenants=1,
            total_projects=3,
            avg_compliance_score=90.0,
        )
        assert len(resp.tenants) == 1
        assert resp.avg_compliance_score == 90.0


class TestTenantHealthResponseSchema:
    def test_valid_health(self):
        health = TenantHealthResponse(
            tenant_id="t-1",
            name="Acme",
            compliance_score=85.0,
            compliance_status="passing",
            active_alerts=0,
            resource_count=10,
        )
        assert health.compliance_status == "passing"
        assert health.recent_deployments == []

    def test_health_with_deployments(self):
        dep = DeploymentSummary(
            id="d-1",
            project_name="Project A",
            status="succeeded",
        )
        health = TenantHealthResponse(
            tenant_id="t-1",
            name="Acme",
            compliance_score=85.0,
            compliance_status="passing",
            recent_deployments=[dep],
            active_alerts=0,
            resource_count=10,
        )
        assert len(health.recent_deployments) == 1

    def test_health_negative_alerts_rejected(self):
        with pytest.raises(Exception):
            TenantHealthResponse(
                tenant_id="t-1",
                name="Acme",
                compliance_score=85.0,
                compliance_status="passing",
                active_alerts=-1,
                resource_count=10,
            )


class TestDeploymentSummarySchema:
    def test_valid_deployment(self):
        dep = DeploymentSummary(
            id="d-1",
            project_name="Hub Network",
            status="succeeded",
        )
        assert dep.started_at is None
        assert dep.completed_at is None

    def test_deployment_with_times(self):
        now = datetime.now(timezone.utc)
        dep = DeploymentSummary(
            id="d-2",
            project_name="Spoke",
            status="in_progress",
            started_at=now,
            completed_at=now,
        )
        assert dep.started_at == now


class TestTenantComplianceScoreSchema:
    def test_valid_score(self):
        score = TenantComplianceScore(
            tenant_id="t-1",
            name="Acme",
            score=92.5,
            status="passing",
        )
        assert score.score == 92.5

    def test_score_out_of_range_rejected(self):
        with pytest.raises(Exception):
            TenantComplianceScore(
                tenant_id="t-1",
                name="Acme",
                score=150.0,
                status="passing",
            )

    def test_negative_score_rejected(self):
        with pytest.raises(Exception):
            TenantComplianceScore(
                tenant_id="t-1",
                name="Acme",
                score=-10.0,
                status="passing",
            )


class TestComplianceSummaryResponseSchema:
    def test_valid_summary(self):
        summary = ComplianceSummaryResponse(
            total_tenants=3,
            passing=1,
            warning=1,
            failing=1,
        )
        assert summary.scores_by_tenant == []

    def test_summary_with_scores(self):
        score = TenantComplianceScore(
            tenant_id="t-1",
            name="Acme",
            score=85.0,
            status="passing",
        )
        summary = ComplianceSummaryResponse(
            total_tenants=1,
            passing=1,
            warning=0,
            failing=0,
            scores_by_tenant=[score],
        )
        assert len(summary.scores_by_tenant) == 1

    def test_negative_counts_rejected(self):
        with pytest.raises(Exception):
            ComplianceSummaryResponse(
                total_tenants=-1,
                passing=0,
                warning=0,
                failing=0,
            )


# ===================================================================
# Mock-data function tests
# ===================================================================


class TestMockOverview:
    def test_returns_overview_response(self):
        result = _mock_overview()
        assert isinstance(result, MSPOverviewResponse)

    def test_has_tenants(self):
        result = _mock_overview()
        assert result.total_tenants == 4
        assert len(result.tenants) == 4

    def test_total_projects_match(self):
        result = _mock_overview()
        expected = sum(t.project_count for t in result.tenants)
        assert result.total_projects == expected

    def test_avg_compliance_score(self):
        result = _mock_overview()
        expected = round(
            sum(t.compliance_score for t in result.tenants)
            / len(result.tenants),
            1,
        )
        assert result.avg_compliance_score == expected

    def test_tenant_names(self):
        result = _mock_overview()
        names = [t.name for t in result.tenants]
        assert "Contoso Ltd" in names
        assert "Fabrikam Inc" in names

    def test_tenant_statuses(self):
        result = _mock_overview()
        statuses = {t.status for t in result.tenants}
        assert "active" in statuses


class TestMockTenantHealth:
    def test_known_tenant(self):
        result = _mock_tenant_health("t-001")
        assert result is not None
        assert result.tenant_id == "t-001"
        assert result.name == "Contoso Ltd"

    def test_unknown_tenant_returns_none(self):
        result = _mock_tenant_health("nonexistent")
        assert result is None

    def test_passing_status(self):
        result = _mock_tenant_health("t-001")
        assert result is not None
        assert result.compliance_status == "passing"

    def test_failing_status(self):
        result = _mock_tenant_health("t-003")
        assert result is not None
        assert result.compliance_status == "failing"

    def test_has_deployments(self):
        result = _mock_tenant_health("t-001")
        assert result is not None
        assert len(result.recent_deployments) > 0

    def test_resource_count_derived_from_projects(self):
        result = _mock_tenant_health("t-001")
        assert result is not None
        assert result.resource_count == 8 * 5  # project_count * 5

    def test_inactive_tenant_health(self):
        result = _mock_tenant_health("t-004")
        assert result is not None
        assert result.compliance_status == "failing"


class TestMockComplianceSummary:
    def test_returns_summary(self):
        result = _mock_compliance_summary()
        assert isinstance(result, ComplianceSummaryResponse)

    def test_total_tenants(self):
        result = _mock_compliance_summary()
        assert result.total_tenants == 4

    def test_counts_sum_to_total(self):
        result = _mock_compliance_summary()
        assert (
            result.passing + result.warning + result.failing
            == result.total_tenants
        )

    def test_scores_by_tenant_populated(self):
        result = _mock_compliance_summary()
        assert len(result.scores_by_tenant) == 4

    def test_contoso_is_passing(self):
        result = _mock_compliance_summary()
        contoso = next(
            s
            for s in result.scores_by_tenant
            if s.name == "Contoso Ltd"
        )
        assert contoso.status == "passing"

    def test_woodgrove_is_failing(self):
        result = _mock_compliance_summary()
        wg = next(
            s
            for s in result.scores_by_tenant
            if s.name == "Woodgrove Bank"
        )
        assert wg.status == "failing"


# ===================================================================
# MSPService tests (DB = None → mock data)
# ===================================================================


class TestMSPServiceMockMode:
    @pytest.mark.asyncio
    async def test_overview_without_db(self):
        svc = MSPService(None)
        result = await svc.get_overview()
        assert isinstance(result, MSPOverviewResponse)
        assert result.total_tenants == 4

    @pytest.mark.asyncio
    async def test_tenant_health_without_db(self):
        svc = MSPService(None)
        result = await svc.get_tenant_health("t-001")
        assert result is not None
        assert result.name == "Contoso Ltd"

    @pytest.mark.asyncio
    async def test_tenant_health_not_found_without_db(self):
        svc = MSPService(None)
        result = await svc.get_tenant_health("unknown")
        assert result is None

    @pytest.mark.asyncio
    async def test_compliance_summary_without_db(self):
        svc = MSPService(None)
        result = await svc.get_compliance_summary()
        assert isinstance(result, ComplianceSummaryResponse)
        assert result.total_tenants == 4


# ===================================================================
# MSPService tests (with in-memory SQLite)
# ===================================================================


class TestMSPServiceWithDB:
    @pytest.mark.asyncio
    async def test_overview_empty_db(self, db_session):
        svc = MSPService(db_session)
        result = await svc.get_overview()
        assert result.total_tenants == 0
        assert result.total_projects == 0
        assert result.avg_compliance_score == 0.0
        assert result.tenants == []

    @pytest.mark.asyncio
    async def test_overview_with_tenants(self, db_session):
        await _seed_tenant(db_session, name="Acme")
        await _seed_tenant(db_session, name="Beta")
        await db_session.commit()

        svc = MSPService(db_session)
        result = await svc.get_overview()
        assert result.total_tenants == 2
        names = {t.name for t in result.tenants}
        assert "Acme" in names
        assert "Beta" in names

    @pytest.mark.asyncio
    async def test_overview_with_projects(self, db_session):
        tenant = await _seed_tenant(db_session, name="Acme")
        user = await _seed_user(db_session, tenant)
        await _seed_project(db_session, tenant, user, name="P1")
        await _seed_project(db_session, tenant, user, name="P2")
        await db_session.commit()

        svc = MSPService(db_session)
        result = await svc.get_overview()
        assert result.total_projects == 2
        acme = next(t for t in result.tenants if t.name == "Acme")
        assert acme.project_count == 2

    @pytest.mark.asyncio
    async def test_overview_with_deployments(self, db_session):
        tenant = await _seed_tenant(db_session, name="Acme")
        user = await _seed_user(db_session, tenant)
        project = await _seed_project(db_session, tenant, user)
        await _seed_deployment(
            db_session, project, user, dep_status="succeeded"
        )
        await _seed_deployment(
            db_session, project, user, dep_status="deploying"
        )
        await db_session.commit()

        svc = MSPService(db_session)
        result = await svc.get_overview()
        acme = next(t for t in result.tenants if t.name == "Acme")
        assert acme.deployment_count == 2
        assert acme.active_deployments == 1

    @pytest.mark.asyncio
    async def test_overview_inactive_tenant(self, db_session):
        await _seed_tenant(
            db_session, name="Inactive", is_active=False
        )
        await db_session.commit()

        svc = MSPService(db_session)
        result = await svc.get_overview()
        assert result.total_tenants == 1
        assert result.tenants[0].status == "inactive"

    @pytest.mark.asyncio
    async def test_tenant_health_found(self, db_session):
        tenant = await _seed_tenant(db_session, name="Acme")
        user = await _seed_user(db_session, tenant)
        await _seed_project(db_session, tenant, user)
        await db_session.commit()

        svc = MSPService(db_session)
        result = await svc.get_tenant_health(tenant.id)
        assert result is not None
        assert result.name == "Acme"
        assert result.resource_count == 5  # 1 project * 5

    @pytest.mark.asyncio
    async def test_tenant_health_not_found(self, db_session):
        svc = MSPService(db_session)
        result = await svc.get_tenant_health("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_tenant_health_with_deployments(self, db_session):
        tenant = await _seed_tenant(db_session, name="Acme")
        user = await _seed_user(db_session, tenant)
        project = await _seed_project(db_session, tenant, user)
        await _seed_deployment(db_session, project, user)
        await db_session.commit()

        svc = MSPService(db_session)
        result = await svc.get_tenant_health(tenant.id)
        assert result is not None
        assert len(result.recent_deployments) == 1

    @pytest.mark.asyncio
    async def test_compliance_summary_empty_db(self, db_session):
        svc = MSPService(db_session)
        result = await svc.get_compliance_summary()
        assert result.total_tenants == 0
        assert result.passing == 0
        assert result.warning == 0
        assert result.failing == 0

    @pytest.mark.asyncio
    async def test_compliance_summary_with_tenants(self, db_session):
        await _seed_tenant(db_session, name="T1")
        await _seed_tenant(db_session, name="T2")
        await _seed_tenant(db_session, name="T3")
        await db_session.commit()

        svc = MSPService(db_session)
        result = await svc.get_compliance_summary()
        assert result.total_tenants == 3
        assert len(result.scores_by_tenant) == 3
        assert (
            result.passing + result.warning + result.failing == 3
        )

    @pytest.mark.asyncio
    async def test_compliance_summary_all_statuses_valid(
        self, db_session
    ):
        for i in range(5):
            await _seed_tenant(db_session, name=f"Tenant-{i}")
        await db_session.commit()

        svc = MSPService(db_session)
        result = await svc.get_compliance_summary()
        for score in result.scores_by_tenant:
            assert score.status in ("passing", "warning", "failing")
            assert 0.0 <= score.score <= 100.0


# ===================================================================
# API Route Tests — RBAC
# ===================================================================


class TestMSPRoutesRBAC:
    def test_overview_allowed_for_msp_admin(
        self, msp_admin_user, db_session
    ):
        app = _build_test_app(msp_admin_user, db_session)
        client = TestClient(app)
        resp = client.get("/api/msp/overview")
        assert resp.status_code == 200

    def test_overview_allowed_for_admin(
        self, admin_user, db_session
    ):
        app = _build_test_app(admin_user, db_session)
        client = TestClient(app)
        resp = client.get("/api/msp/overview")
        assert resp.status_code == 200

    def test_overview_forbidden_for_viewer(
        self, viewer_user, db_session
    ):
        app = _build_test_app(viewer_user, db_session)
        client = TestClient(app)
        resp = client.get("/api/msp/overview")
        assert resp.status_code == 403

    def test_overview_forbidden_for_architect(
        self, architect_user, db_session
    ):
        app = _build_test_app(architect_user, db_session)
        client = TestClient(app)
        resp = client.get("/api/msp/overview")
        assert resp.status_code == 403

    def test_health_forbidden_for_viewer(
        self, viewer_user, db_session
    ):
        app = _build_test_app(viewer_user, db_session)
        client = TestClient(app)
        resp = client.get("/api/msp/tenants/t-001/health")
        assert resp.status_code == 403

    def test_compliance_forbidden_for_viewer(
        self, viewer_user, db_session
    ):
        app = _build_test_app(viewer_user, db_session)
        client = TestClient(app)
        resp = client.get("/api/msp/compliance-summary")
        assert resp.status_code == 403

    def test_health_allowed_for_msp_admin(
        self, msp_admin_user, db_session
    ):
        app = _build_test_app(msp_admin_user, db_session)
        client = TestClient(app)
        resp = client.get("/api/msp/tenants/t-001/health")
        # Will be 200 (mock data) or 404 (DB mode, not found)
        assert resp.status_code in (200, 404)

    def test_compliance_allowed_for_msp_admin(
        self, msp_admin_user, db_session
    ):
        app = _build_test_app(msp_admin_user, db_session)
        client = TestClient(app)
        resp = client.get("/api/msp/compliance-summary")
        assert resp.status_code == 200


# ===================================================================
# API Route Tests — Responses
# ===================================================================


class TestMSPRoutesOverview:
    def test_overview_returns_valid_json(
        self, msp_admin_user, db_session
    ):
        app = _build_test_app(msp_admin_user, db_session)
        client = TestClient(app)
        resp = client.get("/api/msp/overview")
        data = resp.json()
        assert "tenants" in data
        assert "total_tenants" in data
        assert "total_projects" in data
        assert "avg_compliance_score" in data

    def test_overview_response_model_valid(
        self, msp_admin_user, db_session
    ):
        app = _build_test_app(msp_admin_user, db_session)
        client = TestClient(app)
        resp = client.get("/api/msp/overview")
        # Should parse without error
        MSPOverviewResponse(**resp.json())


class TestMSPRoutesOverviewNoDb:
    def test_overview_mock_data_when_no_db(self, msp_admin_user):
        app = _build_test_app(msp_admin_user, None)
        client = TestClient(app)
        resp = client.get("/api/msp/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tenants"] == 4

    def test_health_mock_data_when_no_db(self, msp_admin_user):
        app = _build_test_app(msp_admin_user, None)
        client = TestClient(app)
        resp = client.get("/api/msp/tenants/t-001/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Contoso Ltd"

    def test_health_not_found_when_no_db(self, msp_admin_user):
        app = _build_test_app(msp_admin_user, None)
        client = TestClient(app)
        resp = client.get(
            "/api/msp/tenants/nonexistent/health"
        )
        assert resp.status_code == 404

    def test_compliance_mock_data_when_no_db(
        self, msp_admin_user
    ):
        app = _build_test_app(msp_admin_user, None)
        client = TestClient(app)
        resp = client.get("/api/msp/compliance-summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tenants"] == 4


class TestMSPRoutesTenantHealth:
    def test_health_not_found_in_db(
        self, msp_admin_user, db_session
    ):
        app = _build_test_app(msp_admin_user, db_session)
        client = TestClient(app)
        resp = client.get(
            "/api/msp/tenants/nonexistent/health"
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_health_response_model_valid(
        self, msp_admin_user
    ):
        app = _build_test_app(msp_admin_user, None)
        client = TestClient(app)
        resp = client.get("/api/msp/tenants/t-002/health")
        assert resp.status_code == 200
        TenantHealthResponse(**resp.json())


class TestMSPRoutesComplianceSummary:
    def test_compliance_returns_valid_json(
        self, msp_admin_user, db_session
    ):
        app = _build_test_app(msp_admin_user, db_session)
        client = TestClient(app)
        resp = client.get("/api/msp/compliance-summary")
        data = resp.json()
        assert "total_tenants" in data
        assert "passing" in data
        assert "warning" in data
        assert "failing" in data
        assert "scores_by_tenant" in data

    def test_compliance_response_model_valid(
        self, msp_admin_user, db_session
    ):
        app = _build_test_app(msp_admin_user, db_session)
        client = TestClient(app)
        resp = client.get("/api/msp/compliance-summary")
        ComplianceSummaryResponse(**resp.json())


# ===================================================================
# Edge Cases
# ===================================================================


class TestMSPEdgeCases:
    @pytest.mark.asyncio
    async def test_overview_no_tenants(self, db_session):
        svc = MSPService(db_session)
        result = await svc.get_overview()
        assert result.total_tenants == 0
        assert result.avg_compliance_score == 0.0

    @pytest.mark.asyncio
    async def test_overview_single_tenant(self, db_session):
        await _seed_tenant(db_session, name="Solo")
        await db_session.commit()
        svc = MSPService(db_session)
        result = await svc.get_overview()
        assert result.total_tenants == 1

    @pytest.mark.asyncio
    async def test_tenant_health_no_projects(self, db_session):
        tenant = await _seed_tenant(db_session, name="Empty")
        await db_session.commit()
        svc = MSPService(db_session)
        result = await svc.get_tenant_health(tenant.id)
        assert result is not None
        assert result.resource_count == 0
        assert result.recent_deployments == []

    @pytest.mark.asyncio
    async def test_overview_many_tenants(self, db_session):
        for i in range(20):
            await _seed_tenant(db_session, name=f"T-{i}")
        await db_session.commit()
        svc = MSPService(db_session)
        result = await svc.get_overview()
        assert result.total_tenants == 20

    @pytest.mark.asyncio
    async def test_compliance_all_inactive_tenants(
        self, db_session
    ):
        for i in range(3):
            await _seed_tenant(
                db_session,
                name=f"Inactive-{i}",
                is_active=False,
            )
        await db_session.commit()
        svc = MSPService(db_session)
        result = await svc.get_compliance_summary()
        assert result.total_tenants == 3

    @pytest.mark.asyncio
    async def test_overview_compliance_scores_in_range(
        self, db_session
    ):
        for i in range(10):
            await _seed_tenant(db_session, name=f"Range-{i}")
        await db_session.commit()
        svc = MSPService(db_session)
        result = await svc.get_overview()
        for t in result.tenants:
            assert 0.0 <= t.compliance_score <= 100.0
        assert 0.0 <= result.avg_compliance_score <= 100.0

    @pytest.mark.asyncio
    async def test_tenant_health_deployment_limit(
        self, db_session
    ):
        """Ensure at most 10 recent deployments are returned."""
        tenant = await _seed_tenant(db_session, name="Busy")
        user = await _seed_user(db_session, tenant)
        project = await _seed_project(
            db_session, tenant, user
        )
        for _ in range(15):
            await _seed_deployment(db_session, project, user)
        await db_session.commit()

        svc = MSPService(db_session)
        result = await svc.get_tenant_health(tenant.id)
        assert result is not None
        assert len(result.recent_deployments) <= 10

    def test_user_with_no_roles_gets_default_viewer(self):
        """RoleChecker assigns 'viewer' when roles list empty."""
        no_role_user = {
            "sub": "no-role",
            "name": "No Role",
            "email": "norole@test.local",
            "roles": [],
            "tenant_id": "",
        }
        app = _build_test_app(no_role_user, None)
        client = TestClient(app)
        resp = client.get("/api/msp/overview")
        assert resp.status_code == 403
