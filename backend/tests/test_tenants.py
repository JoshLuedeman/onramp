"""Comprehensive tests for tenant isolation, CRUD, resolution, and schemas.

Covers:
    - Pydantic schema validation (TenantCreate, TenantUpdate, TenantResponse, TenantListResponse)
    - TenantService CRUD operations against an in-memory SQLite database
    - Tenant resolution dependency (JWT tid, X-Tenant-ID header, dev-mode default)
    - API route tests (create, list, get, update, soft-delete)
    - RBAC permission checks (non-admin rejected)
    - Tenant scoping / isolation (cross-tenant data invisible)
    - Dev-mode auto-creation of default tenant
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.dependencies import get_current_tenant
from app.api.routes.tenants import router as tenants_router
from app.auth.entra import get_current_user
from app.db.session import get_db
from app.models.base import Base
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import (
    TenantCreate,
    TenantListResponse,
    TenantResponse,
    TenantUpdate,
)
from app.services.tenant_service import TenantService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SQLITE_URL = "sqlite+aiosqlite:///:memory:"


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
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        yield session


@pytest.fixture()
def admin_user() -> dict:
    """Simulated admin JWT claims."""
    return {
        "sub": "admin-oid",
        "name": "Admin User",
        "email": "admin@onramp.local",
        "roles": ["admin"],
        "tenant_id": "",
    }


@pytest.fixture()
def viewer_user() -> dict:
    """Simulated viewer JWT claims (non-admin)."""
    return {
        "sub": "viewer-oid",
        "name": "Viewer User",
        "email": "viewer@onramp.local",
        "roles": ["viewer"],
        "tenant_id": "",
    }


def _build_test_app(
    user_override: dict,
    db_session_override: AsyncSession,
) -> FastAPI:
    """Build a minimal FastAPI app wired to the test DB and user."""
    test_app = FastAPI()
    test_app.include_router(tenants_router)

    async def _override_user():
        return user_override

    async def _override_db():
        yield db_session_override

    test_app.dependency_overrides[get_current_user] = _override_user
    test_app.dependency_overrides[get_db] = _override_db
    return test_app


# ---------------------------------------------------------------------------
# Schema Validation Tests
# ---------------------------------------------------------------------------


class TestTenantCreateSchema:
    """Tests for TenantCreate schema validation."""

    def test_valid_create(self):
        schema = TenantCreate(name="Acme Corp")
        assert schema.name == "Acme Corp"
        assert schema.azure_tenant_id is None

    def test_valid_create_with_azure_tid(self):
        tid = str(uuid.uuid4())
        schema = TenantCreate(name="Acme Corp", azure_tenant_id=tid)
        assert schema.azure_tenant_id == tid

    def test_create_empty_name_rejected(self):
        with pytest.raises(Exception):
            TenantCreate(name="")

    def test_create_missing_name_rejected(self):
        with pytest.raises(Exception):
            TenantCreate()

    def test_create_long_name_rejected(self):
        with pytest.raises(Exception):
            TenantCreate(name="x" * 256)

    def test_create_max_length_name_accepted(self):
        schema = TenantCreate(name="x" * 255)
        assert len(schema.name) == 255

    def test_create_azure_tid_too_long_rejected(self):
        with pytest.raises(Exception):
            TenantCreate(name="ok", azure_tenant_id="x" * 37)


class TestTenantUpdateSchema:
    """Tests for TenantUpdate schema validation."""

    def test_update_name_only(self):
        schema = TenantUpdate(name="New Name")
        assert schema.name == "New Name"
        assert schema.is_active is None

    def test_update_is_active_only(self):
        schema = TenantUpdate(is_active=False)
        assert schema.is_active is False
        assert schema.name is None

    def test_update_all_fields(self):
        schema = TenantUpdate(name="Updated", is_active=True)
        assert schema.name == "Updated"
        assert schema.is_active is True

    def test_update_no_fields(self):
        schema = TenantUpdate()
        assert schema.name is None
        assert schema.is_active is None

    def test_update_empty_name_rejected(self):
        with pytest.raises(Exception):
            TenantUpdate(name="")

    def test_update_long_name_rejected(self):
        with pytest.raises(Exception):
            TenantUpdate(name="x" * 256)


class TestTenantResponseSchema:
    """Tests for TenantResponse schema."""

    def test_from_attributes(self):
        now = datetime.now(timezone.utc)
        resp = TenantResponse(
            id="t1",
            name="Test",
            azure_tenant_id=None,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert resp.id == "t1"
        assert resp.is_active is True

    def test_from_orm_object(self):
        """TenantResponse.model_validate works with an ORM-like object."""
        class FakeTenant:
            id = "t2"
            name = "Fake"
            azure_tenant_id = "az-123"
            is_active = False
            created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
            updated_at = datetime(2024, 1, 2, tzinfo=timezone.utc)

        resp = TenantResponse.model_validate(FakeTenant(), from_attributes=True)
        assert resp.name == "Fake"
        assert resp.azure_tenant_id == "az-123"


class TestTenantListResponseSchema:
    """Tests for TenantListResponse schema."""

    def test_empty_list(self):
        resp = TenantListResponse(tenants=[], total=0)
        assert resp.tenants == []
        assert resp.total == 0

    def test_with_tenants(self):
        now = datetime.now(timezone.utc)
        t = TenantResponse(
            id="t1", name="A", azure_tenant_id=None,
            is_active=True, created_at=now, updated_at=now,
        )
        resp = TenantListResponse(tenants=[t], total=1)
        assert len(resp.tenants) == 1
        assert resp.total == 1


# ---------------------------------------------------------------------------
# TenantService Tests
# ---------------------------------------------------------------------------


class TestTenantServiceCreate:
    """Tests for TenantService.create_tenant."""

    async def test_create_tenant(self, db_session):
        svc = TenantService(db_session)
        tenant = await svc.create_tenant(TenantCreate(name="NewCo"))
        assert tenant.id is not None
        assert tenant.name == "NewCo"
        assert tenant.is_active is True

    async def test_create_tenant_with_azure_tid(self, db_session):
        tid = str(uuid.uuid4())
        svc = TenantService(db_session)
        tenant = await svc.create_tenant(
            TenantCreate(name="AzureCo", azure_tenant_id=tid)
        )
        assert tenant.azure_tenant_id == tid

    async def test_create_multiple_tenants(self, db_session):
        svc = TenantService(db_session)
        t1 = await svc.create_tenant(TenantCreate(name="A"))
        t2 = await svc.create_tenant(TenantCreate(name="B"))
        assert t1.id != t2.id


class TestTenantServiceGet:
    """Tests for TenantService.get_tenant."""

    async def test_get_existing_tenant(self, db_session):
        svc = TenantService(db_session)
        created = await svc.create_tenant(TenantCreate(name="Exists"))
        fetched = await svc.get_tenant(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    async def test_get_nonexistent_tenant(self, db_session):
        svc = TenantService(db_session)
        result = await svc.get_tenant("nonexistent-id")
        assert result is None


class TestTenantServiceList:
    """Tests for TenantService.list_tenants."""

    async def test_list_empty(self, db_session):
        svc = TenantService(db_session)
        tenants, total = await svc.list_tenants()
        assert tenants == []
        assert total == 0

    async def test_list_with_data(self, db_session):
        svc = TenantService(db_session)
        await svc.create_tenant(TenantCreate(name="A"))
        await svc.create_tenant(TenantCreate(name="B"))
        tenants, total = await svc.list_tenants()
        assert total == 2
        assert len(tenants) == 2

    async def test_list_pagination(self, db_session):
        svc = TenantService(db_session)
        for i in range(5):
            await svc.create_tenant(TenantCreate(name=f"T{i}"))
        tenants, total = await svc.list_tenants(skip=2, limit=2)
        assert total == 5
        assert len(tenants) == 2


class TestTenantServiceUpdate:
    """Tests for TenantService.update_tenant."""

    async def test_update_name(self, db_session):
        svc = TenantService(db_session)
        tenant = await svc.create_tenant(TenantCreate(name="Old"))
        updated = await svc.update_tenant(tenant.id, TenantUpdate(name="New"))
        assert updated is not None
        assert updated.name == "New"

    async def test_update_is_active(self, db_session):
        svc = TenantService(db_session)
        tenant = await svc.create_tenant(TenantCreate(name="Active"))
        updated = await svc.update_tenant(tenant.id, TenantUpdate(is_active=False))
        assert updated is not None
        assert updated.is_active is False

    async def test_update_nonexistent_returns_none(self, db_session):
        svc = TenantService(db_session)
        result = await svc.update_tenant("missing", TenantUpdate(name="X"))
        assert result is None

    async def test_update_no_fields_is_noop(self, db_session):
        svc = TenantService(db_session)
        tenant = await svc.create_tenant(TenantCreate(name="Same"))
        updated = await svc.update_tenant(tenant.id, TenantUpdate())
        assert updated is not None
        assert updated.name == "Same"


class TestTenantServiceDeactivate:
    """Tests for TenantService.deactivate_tenant."""

    async def test_deactivate(self, db_session):
        svc = TenantService(db_session)
        tenant = await svc.create_tenant(TenantCreate(name="ToDeactivate"))
        result = await svc.deactivate_tenant(tenant.id)
        assert result is not None
        assert result.is_active is False

    async def test_deactivate_nonexistent(self, db_session):
        svc = TenantService(db_session)
        result = await svc.deactivate_tenant("missing")
        assert result is None


class TestTenantServiceDefaultTenant:
    """Tests for TenantService.get_or_create_default."""

    async def test_creates_default_when_missing(self, db_session):
        svc = TenantService(db_session)
        tenant = await svc.get_or_create_default()
        assert tenant.name == "Default"
        assert tenant.is_active is True

    async def test_returns_existing_default(self, db_session):
        svc = TenantService(db_session)
        first = await svc.get_or_create_default()
        second = await svc.get_or_create_default()
        assert first.id == second.id


# ---------------------------------------------------------------------------
# Tenant Resolution Dependency Tests
# ---------------------------------------------------------------------------


class TestGetCurrentTenantJWT:
    """Tests for get_current_tenant — JWT tid claim path."""

    async def test_resolves_via_jwt_tid(self, db_session):
        """When user has a valid tenant_id claim, resolves that tenant."""
        azure_tid = str(uuid.uuid4())
        tenant = Tenant(name="JWT Tenant", azure_tenant_id=azure_tid, is_active=True)
        db_session.add(tenant)
        await db_session.flush()

        user_claims = {"tenant_id": azure_tid, "roles": ["admin"]}

        class FakeRequest:
            headers = {}

        resolved = await get_current_tenant(FakeRequest(), user_claims, db_session)
        assert resolved.id == tenant.id

    async def test_jwt_tid_not_found_falls_through(self, db_session):
        """Unknown tid falls through to header / dev-mode."""
        user_claims = {"tenant_id": "unknown-tid", "roles": ["admin"]}

        class FakeRequest:
            headers = {}

        with patch("app.api.dependencies.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            resolved = await get_current_tenant(FakeRequest(), user_claims, db_session)
            assert resolved.name == "Default"


class TestGetCurrentTenantHeader:
    """Tests for get_current_tenant — X-Tenant-ID header path."""

    async def test_resolves_via_header(self, db_session):
        """When X-Tenant-ID header is set, resolves that tenant."""
        tenant = Tenant(name="Header Tenant", is_active=True)
        db_session.add(tenant)
        await db_session.flush()

        user_claims = {"roles": ["admin"]}

        class FakeRequest:
            headers = {"X-Tenant-ID": tenant.id}

        resolved = await get_current_tenant(FakeRequest(), user_claims, db_session)
        assert resolved.id == tenant.id

    async def test_invalid_header_id_falls_through(self, db_session):
        """Bad header ID falls through to dev-mode default."""
        user_claims = {"roles": ["admin"]}

        class FakeRequest:
            headers = {"X-Tenant-ID": "nonexistent"}

        with patch("app.api.dependencies.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            resolved = await get_current_tenant(FakeRequest(), user_claims, db_session)
            assert resolved.name == "Default"


class TestGetCurrentTenantDevMode:
    """Tests for get_current_tenant — dev-mode default path."""

    async def test_creates_default_in_dev_mode(self, db_session):
        """In dev mode with no JWT/header, auto-creates Default tenant."""
        user_claims = {"roles": ["admin"]}

        class FakeRequest:
            headers = {}

        with patch("app.api.dependencies.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            resolved = await get_current_tenant(FakeRequest(), user_claims, db_session)
            assert resolved.name == "Default"
            assert resolved.is_active is True

    async def test_reuses_existing_default(self, db_session):
        """If Default tenant already exists, reuses it."""
        existing = Tenant(name="Default", is_active=True)
        db_session.add(existing)
        await db_session.flush()

        user_claims = {"roles": ["admin"]}

        class FakeRequest:
            headers = {}

        with patch("app.api.dependencies.settings") as mock_settings:
            mock_settings.is_dev_mode = True
            resolved = await get_current_tenant(FakeRequest(), user_claims, db_session)
            assert resolved.id == existing.id

    async def test_inactive_tenant_rejected(self, db_session):
        """Even if resolved, an inactive tenant raises 403."""
        from fastapi import HTTPException

        azure_tid = str(uuid.uuid4())
        tenant = Tenant(name="Dead", azure_tenant_id=azure_tid, is_active=False)
        db_session.add(tenant)
        await db_session.flush()

        user_claims = {"tenant_id": azure_tid, "roles": ["admin"]}

        class FakeRequest:
            headers = {}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_tenant(FakeRequest(), user_claims, db_session)
        assert exc_info.value.status_code == 403
        assert "deactivated" in exc_info.value.detail

    async def test_no_db_raises_403(self):
        """When db is None, raises 403."""
        from fastapi import HTTPException

        user_claims = {"roles": ["admin"]}

        class FakeRequest:
            headers = {}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_tenant(FakeRequest(), user_claims, None)
        assert exc_info.value.status_code == 403

    async def test_no_resolution_in_prod_raises_403(self, db_session):
        """In production mode with no matching tenant, raises 403."""
        from fastapi import HTTPException

        user_claims = {"roles": ["admin"]}

        class FakeRequest:
            headers = {}

        with patch("app.api.dependencies.settings") as mock_settings:
            mock_settings.is_dev_mode = False
            with pytest.raises(HTTPException) as exc_info:
                await get_current_tenant(FakeRequest(), user_claims, db_session)
            assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Route Tests — CRUD
# ---------------------------------------------------------------------------


class TestCreateTenantRoute:
    """Tests for POST /api/tenants/."""

    def test_create_tenant_success(self, admin_user, db_session):
        app = _build_test_app(admin_user, db_session)
        client = TestClient(app)
        resp = client.post("/api/tenants/", json={"name": "Acme"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Acme"
        assert data["is_active"] is True
        assert "id" in data

    def test_create_tenant_with_azure_tid(self, admin_user, db_session):
        app = _build_test_app(admin_user, db_session)
        client = TestClient(app)
        tid = str(uuid.uuid4())
        resp = client.post(
            "/api/tenants/", json={"name": "Azure Co", "azure_tenant_id": tid}
        )
        assert resp.status_code == 201
        assert resp.json()["azure_tenant_id"] == tid

    def test_create_tenant_invalid_body(self, admin_user, db_session):
        app = _build_test_app(admin_user, db_session)
        client = TestClient(app)
        resp = client.post("/api/tenants/", json={})
        assert resp.status_code == 422

    def test_create_tenant_empty_name(self, admin_user, db_session):
        app = _build_test_app(admin_user, db_session)
        client = TestClient(app)
        resp = client.post("/api/tenants/", json={"name": ""})
        assert resp.status_code == 422


class TestListTenantsRoute:
    """Tests for GET /api/tenants/."""

    def test_list_empty(self, admin_user, db_session):
        app = _build_test_app(admin_user, db_session)
        client = TestClient(app)
        resp = client.get("/api/tenants/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tenants"] == []
        assert data["total"] == 0

    def test_list_after_create(self, admin_user, db_session):
        app = _build_test_app(admin_user, db_session)
        client = TestClient(app)
        client.post("/api/tenants/", json={"name": "T1"})
        client.post("/api/tenants/", json={"name": "T2"})
        resp = client.get("/api/tenants/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["tenants"]) == 2

    def test_list_pagination(self, admin_user, db_session):
        app = _build_test_app(admin_user, db_session)
        client = TestClient(app)
        for i in range(5):
            client.post("/api/tenants/", json={"name": f"T{i}"})
        resp = client.get("/api/tenants/?skip=2&limit=2")
        data = resp.json()
        assert data["total"] == 5
        assert len(data["tenants"]) == 2


class TestGetTenantRoute:
    """Tests for GET /api/tenants/{tenant_id}."""

    def test_get_existing(self, admin_user, db_session):
        app = _build_test_app(admin_user, db_session)
        client = TestClient(app)
        create_resp = client.post("/api/tenants/", json={"name": "GetMe"})
        tid = create_resp.json()["id"]
        resp = client.get(f"/api/tenants/{tid}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "GetMe"

    def test_get_nonexistent(self, admin_user, db_session):
        app = _build_test_app(admin_user, db_session)
        client = TestClient(app)
        resp = client.get("/api/tenants/no-such-id")
        assert resp.status_code == 404


class TestUpdateTenantRoute:
    """Tests for PATCH /api/tenants/{tenant_id}."""

    def test_update_name(self, admin_user, db_session):
        app = _build_test_app(admin_user, db_session)
        client = TestClient(app)
        create_resp = client.post("/api/tenants/", json={"name": "Old"})
        tid = create_resp.json()["id"]
        resp = client.patch(f"/api/tenants/{tid}", json={"name": "New"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New"

    def test_update_is_active(self, admin_user, db_session):
        app = _build_test_app(admin_user, db_session)
        client = TestClient(app)
        create_resp = client.post("/api/tenants/", json={"name": "Flip"})
        tid = create_resp.json()["id"]
        resp = client.patch(f"/api/tenants/{tid}", json={"is_active": False})
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_update_nonexistent(self, admin_user, db_session):
        app = _build_test_app(admin_user, db_session)
        client = TestClient(app)
        resp = client.patch("/api/tenants/missing", json={"name": "X"})
        assert resp.status_code == 404

    def test_update_empty_body_ok(self, admin_user, db_session):
        """PATCH with no fields is a valid no-op."""
        app = _build_test_app(admin_user, db_session)
        client = TestClient(app)
        create_resp = client.post("/api/tenants/", json={"name": "Same"})
        tid = create_resp.json()["id"]
        resp = client.patch(f"/api/tenants/{tid}", json={})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Same"


class TestDeleteTenantRoute:
    """Tests for DELETE /api/tenants/{tenant_id}."""

    def test_delete_deactivates(self, admin_user, db_session):
        app = _build_test_app(admin_user, db_session)
        client = TestClient(app)
        create_resp = client.post("/api/tenants/", json={"name": "Doomed"})
        tid = create_resp.json()["id"]
        resp = client.delete(f"/api/tenants/{tid}")
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_delete_nonexistent(self, admin_user, db_session):
        app = _build_test_app(admin_user, db_session)
        client = TestClient(app)
        resp = client.delete("/api/tenants/missing")
        assert resp.status_code == 404

    def test_delete_is_idempotent(self, admin_user, db_session):
        """Deleting an already-deactivated tenant still returns it."""
        app = _build_test_app(admin_user, db_session)
        client = TestClient(app)
        create_resp = client.post("/api/tenants/", json={"name": "Twice"})
        tid = create_resp.json()["id"]
        client.delete(f"/api/tenants/{tid}")
        resp = client.delete(f"/api/tenants/{tid}")
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False


# ---------------------------------------------------------------------------
# Permission / RBAC Tests
# ---------------------------------------------------------------------------


class TestTenantPermissions:
    """Non-admin users should be rejected from all tenant routes."""

    def test_viewer_cannot_create(self, viewer_user, db_session):
        app = _build_test_app(viewer_user, db_session)
        client = TestClient(app)
        resp = client.post("/api/tenants/", json={"name": "Nope"})
        assert resp.status_code == 403

    def test_viewer_cannot_list(self, viewer_user, db_session):
        app = _build_test_app(viewer_user, db_session)
        client = TestClient(app)
        resp = client.get("/api/tenants/")
        assert resp.status_code == 403

    def test_viewer_cannot_get(self, viewer_user, db_session):
        app = _build_test_app(viewer_user, db_session)
        client = TestClient(app)
        resp = client.get("/api/tenants/some-id")
        assert resp.status_code == 403

    def test_viewer_cannot_update(self, viewer_user, db_session):
        app = _build_test_app(viewer_user, db_session)
        client = TestClient(app)
        resp = client.patch("/api/tenants/some-id", json={"name": "Nope"})
        assert resp.status_code == 403

    def test_viewer_cannot_delete(self, viewer_user, db_session):
        app = _build_test_app(viewer_user, db_session)
        client = TestClient(app)
        resp = client.delete("/api/tenants/some-id")
        assert resp.status_code == 403

    def test_architect_cannot_create(self, db_session):
        architect_user = {
            "sub": "arch-oid",
            "name": "Architect",
            "email": "arch@onramp.local",
            "roles": ["architect"],
        }
        app = _build_test_app(architect_user, db_session)
        client = TestClient(app)
        resp = client.post("/api/tenants/", json={"name": "Nope"})
        assert resp.status_code == 403

    def test_no_roles_cannot_create(self, db_session):
        no_role_user = {
            "sub": "nobody",
            "name": "Nobody",
            "email": "nobody@onramp.local",
            "roles": [],
        }
        app = _build_test_app(no_role_user, db_session)
        client = TestClient(app)
        resp = client.post("/api/tenants/", json={"name": "Nope"})
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Tenant Scoping / Isolation Tests
# ---------------------------------------------------------------------------


class TestTenantIsolation:
    """Verify that tenant data stays isolated."""

    async def test_tenants_have_unique_ids(self, db_session):
        svc = TenantService(db_session)
        t1 = await svc.create_tenant(TenantCreate(name="Org A"))
        t2 = await svc.create_tenant(TenantCreate(name="Org B"))
        assert t1.id != t2.id

    async def test_user_scoped_to_tenant(self, db_session):
        """Users in different tenants are isolated."""
        svc = TenantService(db_session)
        t1 = await svc.create_tenant(TenantCreate(name="Tenant 1"))
        t2 = await svc.create_tenant(TenantCreate(name="Tenant 2"))

        u1 = User(
            entra_object_id="oid-1", email="u1@t1.com",
            display_name="User 1", tenant_id=t1.id,
        )
        u2 = User(
            entra_object_id="oid-2", email="u2@t2.com",
            display_name="User 2", tenant_id=t2.id,
        )
        db_session.add_all([u1, u2])
        await db_session.flush()

        # Query users scoped to tenant 1
        result = await db_session.execute(
            select(User).where(User.tenant_id == t1.id)
        )
        t1_users = result.scalars().all()
        assert len(t1_users) == 1
        assert t1_users[0].email == "u1@t1.com"

    async def test_deactivated_tenant_hides_from_resolution(self, db_session):
        """An inactive tenant is rejected by get_current_tenant."""
        from fastapi import HTTPException

        svc = TenantService(db_session)
        tenant = await svc.create_tenant(TenantCreate(name="Hidden"))
        await svc.deactivate_tenant(tenant.id)

        user_claims = {"roles": ["admin"]}

        class FakeRequest:
            headers = {"X-Tenant-ID": tenant.id}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_tenant(FakeRequest(), user_claims, db_session)
        assert exc_info.value.status_code == 403

    async def test_cross_tenant_query_returns_empty(self, db_session):
        """Querying users with the wrong tenant_id returns nothing."""
        svc = TenantService(db_session)
        t1 = await svc.create_tenant(TenantCreate(name="Visible"))
        t2 = await svc.create_tenant(TenantCreate(name="Other"))

        u = User(
            entra_object_id="oid-x", email="x@visible.com",
            display_name="X", tenant_id=t1.id,
        )
        db_session.add(u)
        await db_session.flush()

        result = await db_session.execute(
            select(User).where(User.tenant_id == t2.id)
        )
        assert result.scalars().all() == []


# ---------------------------------------------------------------------------
# No-Database Guard Tests
# ---------------------------------------------------------------------------


class TestNoDatabaseGuards:
    """Routes handle db=None gracefully."""

    def test_create_no_db(self, admin_user):
        test_app = FastAPI()
        test_app.include_router(tenants_router)

        async def _override_user():
            return admin_user

        async def _override_db():
            yield None

        test_app.dependency_overrides[get_current_user] = _override_user
        test_app.dependency_overrides[get_db] = _override_db
        client = TestClient(test_app)
        resp = client.post("/api/tenants/", json={"name": "X"})
        assert resp.status_code == 503

    def test_list_no_db(self, admin_user):
        test_app = FastAPI()
        test_app.include_router(tenants_router)

        async def _override_user():
            return admin_user

        async def _override_db():
            yield None

        test_app.dependency_overrides[get_current_user] = _override_user
        test_app.dependency_overrides[get_db] = _override_db
        client = TestClient(test_app)
        resp = client.get("/api/tenants/")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_get_no_db(self, admin_user):
        test_app = FastAPI()
        test_app.include_router(tenants_router)

        async def _override_user():
            return admin_user

        async def _override_db():
            yield None

        test_app.dependency_overrides[get_current_user] = _override_user
        test_app.dependency_overrides[get_db] = _override_db
        client = TestClient(test_app)
        resp = client.get("/api/tenants/x")
        assert resp.status_code == 503

    def test_update_no_db(self, admin_user):
        test_app = FastAPI()
        test_app.include_router(tenants_router)

        async def _override_user():
            return admin_user

        async def _override_db():
            yield None

        test_app.dependency_overrides[get_current_user] = _override_user
        test_app.dependency_overrides[get_db] = _override_db
        client = TestClient(test_app)
        resp = client.patch("/api/tenants/x", json={"name": "Y"})
        assert resp.status_code == 503

    def test_delete_no_db(self, admin_user):
        test_app = FastAPI()
        test_app.include_router(tenants_router)

        async def _override_user():
            return admin_user

        async def _override_db():
            yield None

        test_app.dependency_overrides[get_current_user] = _override_user
        test_app.dependency_overrides[get_db] = _override_db
        client = TestClient(test_app)
        resp = client.delete("/api/tenants/x")
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Integration Smoke Tests (via main app)
# ---------------------------------------------------------------------------


class TestMainAppIntegration:
    """Verify the tenants router is registered on the main app."""

    def test_tenants_routes_registered(self):
        """The main app should include /api/tenants endpoints."""
        from app.main import app as main_app

        routes = [r.path for r in main_app.routes]
        assert "/api/tenants/" in routes or "/api/tenants" in routes

    def test_create_via_main_app_dev_mode(self):
        """In dev mode, admin can create a tenant through the main app."""
        from app.main import app as main_app

        client = TestClient(main_app)
        resp = client.post("/api/tenants/", json={"name": "IntegrationTest"})
        # dev mode returns admin user => 201 if DB is available, 503 if not
        assert resp.status_code in (201, 503)
