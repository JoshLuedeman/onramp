"""Tests for tenant isolation improvements.

Verifies:
- Compound unique constraint on (tenant_id, entra_object_id) in User model
- get_user_projects filters by tenant_id
- Same entra_object_id allowed across different tenants
"""

import os

os.environ.setdefault("ONRAMP_DEBUG", "true")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.auth.entra import get_current_user
from app.db.session import get_db
from app.main import app
from app.models import Project, Tenant, User
from app.models.base import Base

AUTH_HEADERS = {"Authorization": "Bearer test"}

SQLITE_URL = "sqlite+aiosqlite:///:memory:"


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------


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


# -------------------------------------------------------------------
# Model-level tests
# -------------------------------------------------------------------


class TestUserModelConstraint:
    """Verify the compound unique constraint exists on the User model."""

    def test_compound_unique_constraint_declared(self):
        """The User model must declare uq_user_tenant_entra."""
        constraints = User.__table_args__
        assert any(
            getattr(c, "name", None) == "uq_user_tenant_entra" for c in constraints
        ), "Expected compound unique constraint 'uq_user_tenant_entra' on User model"

    def test_entra_object_id_not_individually_unique(self):
        """entra_object_id column should NOT have unique=True by itself."""
        col = User.__table__.columns["entra_object_id"]
        assert col.unique is not True, (
            "entra_object_id should not be individually unique; "
            "use the compound constraint instead"
        )

    @pytest.mark.asyncio
    async def test_compound_constraint_in_schema(self, async_engine):
        """The actual DB schema should have the compound unique constraint."""
        async with async_engine.connect() as conn:
            uniques = await conn.run_sync(
                lambda sync_conn: sa_inspect(sync_conn).get_unique_constraints("users")
            )
        names = [u["name"] for u in uniques]
        assert "uq_user_tenant_entra" in names


# -------------------------------------------------------------------
# Same entra_object_id across tenants
# -------------------------------------------------------------------


class TestCrossTenantUsers:
    """Same entra_object_id must be allowed in different tenants."""

    @pytest.mark.asyncio
    async def test_same_entra_id_different_tenants(self, db_session: AsyncSession):
        tenant_a = Tenant(id="tenant-a", name="Tenant A")
        tenant_b = Tenant(id="tenant-b", name="Tenant B")
        db_session.add_all([tenant_a, tenant_b])
        await db_session.flush()

        shared_entra_id = "shared-entra-oid"

        user_a = User(
            id="user-a",
            entra_object_id=shared_entra_id,
            email="user@a.com",
            display_name="User A",
            tenant_id="tenant-a",
        )
        user_b = User(
            id="user-b",
            entra_object_id=shared_entra_id,
            email="user@b.com",
            display_name="User B",
            tenant_id="tenant-b",
        )
        db_session.add_all([user_a, user_b])
        await db_session.commit()

        # Both rows should persist without constraint violation
        await db_session.refresh(user_a)
        await db_session.refresh(user_b)
        assert user_a.entra_object_id == user_b.entra_object_id
        assert user_a.tenant_id != user_b.tenant_id


# -------------------------------------------------------------------
# Route-level: get_user_projects must filter by tenant_id
# -------------------------------------------------------------------


class TestGetUserProjectsTenantScoped:
    """Verify /api/users/me/projects is tenant-scoped."""

    @pytest.mark.asyncio
    async def test_projects_filtered_by_tenant(self, async_engine):
        """Only projects matching user's tenant_id should be returned."""
        factory = async_sessionmaker(
            async_engine, class_=AsyncSession, expire_on_commit=False
        )

        # Seed data
        async with factory() as session:
            tenant_a = Tenant(id="tenant-a", name="Tenant A")
            tenant_b = Tenant(id="tenant-b", name="Tenant B")
            session.add_all([tenant_a, tenant_b])
            await session.flush()

            user_a = User(
                id="user-a",
                entra_object_id="oid-a",
                email="a@test.com",
                display_name="User A",
                tenant_id="tenant-a",
            )
            session.add(user_a)
            await session.flush()

            # Project in tenant A owned by user_a
            proj_a = Project(
                id="proj-a",
                name="Project A",
                tenant_id="tenant-a",
                created_by="user-a",
            )
            # Project in tenant B but same created_by (simulates cross-tenant leak)
            proj_b = Project(
                id="proj-b",
                name="Project B",
                tenant_id="tenant-b",
                created_by="user-a",
            )
            session.add_all([proj_a, proj_b])
            await session.commit()

        # Override dependencies
        mock_user = {
            "sub": "user-a",
            "oid": "user-a",
            "tid": "tenant-a",
            "name": "User A",
            "email": "a@test.com",
            "roles": ["admin"],
        }

        async def override_db():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = override_db

        try:
            client = TestClient(app)
            response = client.get("/api/users/me/projects", headers=AUTH_HEADERS)
            assert response.status_code == 200
            data = response.json()
            project_ids = [p["id"] for p in data["projects"]]
            assert "proj-a" in project_ids, "User's own-tenant project should appear"
            assert "proj-b" not in project_ids, (
                "Project from another tenant must NOT appear"
            )
        finally:
            app.dependency_overrides.clear()
