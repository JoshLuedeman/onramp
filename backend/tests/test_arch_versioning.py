"""Comprehensive tests for architecture versioning — model, service, and routes."""

import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.models.base import Base

SQLITE_TEST_URL = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def engine():
    eng = create_async_engine(SQLITE_TEST_URL, echo=False)

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture()
async def db_session(engine):
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture()
async def client(engine):
    """AsyncClient backed by an in-memory DB, injected via dependency override."""
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _override_get_current_user():
        return {"oid": "test-user-id", "tid": "test-tenant", "name": "Tester"}

    from app.db.session import get_db
    from app.auth import get_current_user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

SAMPLE_ARCH_V1 = {
    "management_groups": {"root": {"display_name": "Root", "children": {}}},
    "subscriptions": [{"name": "Prod", "purpose": "Production"}],
    "network_topology": {"type": "hub-spoke"},
    "policies": {"enforce_tagging": True},
}

SAMPLE_ARCH_V2 = {
    "management_groups": {
        "root": {
            "display_name": "Root",
            "children": {"platform": {"display_name": "Platform", "children": {}}},
        }
    },
    "subscriptions": [
        {"name": "Prod", "purpose": "Production"},
        {"name": "Dev", "purpose": "Development"},
    ],
    "network_topology": {"type": "hub-spoke", "firewall": True},
    "policies": {"enforce_tagging": True, "enforce_naming": True},
    "compliance_frameworks": ["CIS", "NIST"],
}

SAMPLE_ARCH_V3 = {
    "management_groups": {
        "root": {"display_name": "Tenant Root", "children": {}}
    },
    "subscriptions": [{"name": "Staging", "purpose": "Staging"}],
    "network_topology": {"type": "flat"},
}


async def _seed_architecture(db_session: AsyncSession) -> str:
    """Insert a bare Architecture row and return its id."""
    from app.models.architecture import Architecture

    arch = Architecture(
        architecture_data=SAMPLE_ARCH_V1,
        project_id="proj-test-1",
        status="draft",
        version=1,
    )
    db_session.add(arch)
    await db_session.flush()
    return arch.id


async def _seed_project_and_architecture(db_session: AsyncSession) -> str:
    """Insert tenant, user, project, and architecture. Return arch id."""
    from app.models.tenant import Tenant
    from app.models.user import User
    from app.models.project import Project
    from app.models.architecture import Architecture

    tenant = Tenant(id="test-tenant", name="Test Tenant", azure_tenant_id="azure-t")
    db_session.add(tenant)
    await db_session.flush()

    user = User(
        id="test-user-id",
        email="test@example.com",
        display_name="Tester",
        role="architect",
        tenant_id="test-tenant",
        entra_object_id="entra-obj",
    )
    db_session.add(user)
    await db_session.flush()

    project = Project(
        id="proj-test-1",
        name="Test Project",
        status="draft",
        tenant_id="test-tenant",
        created_by="test-user-id",
    )
    db_session.add(project)
    await db_session.flush()

    arch = Architecture(
        architecture_data=SAMPLE_ARCH_V1,
        project_id="proj-test-1",
        status="draft",
        version=1,
    )
    db_session.add(arch)
    await db_session.flush()
    return arch.id


# ===========================================================================
# SERVICE-LEVEL TESTS
# ===========================================================================

class TestCreateVersion:
    """Tests for version_service.create_version."""

    @pytest.mark.asyncio
    async def test_creates_first_version(self, db_session):
        arch_id = await _seed_architecture(db_session)
        from app.services.version_service import create_version

        v = await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1))
        assert v.version_number == 1
        assert v.architecture_id == arch_id

    @pytest.mark.asyncio
    async def test_auto_increments_version(self, db_session):
        arch_id = await _seed_architecture(db_session)
        from app.services.version_service import create_version

        v1 = await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1))
        v2 = await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V2))
        assert v1.version_number == 1
        assert v2.version_number == 2

    @pytest.mark.asyncio
    async def test_stores_change_summary(self, db_session):
        arch_id = await _seed_architecture(db_session)
        from app.services.version_service import create_version

        v = await create_version(
            db_session, arch_id, json.dumps(SAMPLE_ARCH_V1),
            change_summary="Initial generation",
        )
        assert v.change_summary == "Initial generation"

    @pytest.mark.asyncio
    async def test_stores_created_by(self, db_session):
        arch_id = await _seed_architecture(db_session)
        from app.services.version_service import create_version

        v = await create_version(
            db_session, arch_id, json.dumps(SAMPLE_ARCH_V1), created_by="user-123",
        )
        assert v.created_by == "user-123"

    @pytest.mark.asyncio
    async def test_stores_full_json(self, db_session):
        arch_id = await _seed_architecture(db_session)
        from app.services.version_service import create_version

        payload = json.dumps(SAMPLE_ARCH_V1)
        v = await create_version(db_session, arch_id, payload)
        assert json.loads(v.architecture_json) == SAMPLE_ARCH_V1

    @pytest.mark.asyncio
    async def test_version_has_id(self, db_session):
        arch_id = await _seed_architecture(db_session)
        from app.services.version_service import create_version

        v = await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1))
        assert v.id is not None
        assert len(v.id) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_multiple_architectures_independent_numbering(self, db_session):
        """Version numbers are scoped per architecture."""
        from app.models.architecture import Architecture
        from app.services.version_service import create_version

        arch1 = Architecture(
            architecture_data=SAMPLE_ARCH_V1, project_id="proj-a", status="draft",
        )
        arch2 = Architecture(
            architecture_data=SAMPLE_ARCH_V2, project_id="proj-b", status="draft",
        )
        db_session.add_all([arch1, arch2])
        await db_session.flush()

        v1a = await create_version(db_session, arch1.id, json.dumps(SAMPLE_ARCH_V1))
        v1b = await create_version(db_session, arch2.id, json.dumps(SAMPLE_ARCH_V2))
        v2a = await create_version(db_session, arch1.id, json.dumps(SAMPLE_ARCH_V2))

        assert v1a.version_number == 1
        assert v1b.version_number == 1
        assert v2a.version_number == 2


class TestListVersions:
    """Tests for version_service.list_versions."""

    @pytest.mark.asyncio
    async def test_empty_list(self, db_session):
        arch_id = await _seed_architecture(db_session)
        from app.services.version_service import list_versions

        versions = await list_versions(db_session, arch_id)
        assert versions == []

    @pytest.mark.asyncio
    async def test_returns_versions_newest_first(self, db_session):
        arch_id = await _seed_architecture(db_session)
        from app.services.version_service import create_version, list_versions

        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1))
        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V2))
        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V3))

        versions = await list_versions(db_session, arch_id)
        assert len(versions) == 3
        assert versions[0].version_number == 3
        assert versions[1].version_number == 2
        assert versions[2].version_number == 1

    @pytest.mark.asyncio
    async def test_scoped_to_architecture(self, db_session):
        from app.models.architecture import Architecture
        from app.services.version_service import create_version, list_versions

        arch1 = Architecture(
            architecture_data=SAMPLE_ARCH_V1, project_id="proj-x", status="draft",
        )
        arch2 = Architecture(
            architecture_data=SAMPLE_ARCH_V2, project_id="proj-y", status="draft",
        )
        db_session.add_all([arch1, arch2])
        await db_session.flush()

        await create_version(db_session, arch1.id, json.dumps(SAMPLE_ARCH_V1))
        await create_version(db_session, arch1.id, json.dumps(SAMPLE_ARCH_V2))
        await create_version(db_session, arch2.id, json.dumps(SAMPLE_ARCH_V3))

        assert len(await list_versions(db_session, arch1.id)) == 2
        assert len(await list_versions(db_session, arch2.id)) == 1


class TestGetVersion:
    """Tests for version_service.get_version."""

    @pytest.mark.asyncio
    async def test_get_existing_version(self, db_session):
        arch_id = await _seed_architecture(db_session)
        from app.services.version_service import create_version, get_version

        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1))
        v = await get_version(db_session, arch_id, 1)
        assert v is not None
        assert v.version_number == 1

    @pytest.mark.asyncio
    async def test_get_nonexistent_version_returns_none(self, db_session):
        arch_id = await _seed_architecture(db_session)
        from app.services.version_service import get_version

        v = await get_version(db_session, arch_id, 999)
        assert v is None

    @pytest.mark.asyncio
    async def test_get_specific_version_among_many(self, db_session):
        arch_id = await _seed_architecture(db_session)
        from app.services.version_service import create_version, get_version

        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1))
        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V2))
        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V3))

        v2 = await get_version(db_session, arch_id, 2)
        assert v2 is not None
        assert json.loads(v2.architecture_json) == SAMPLE_ARCH_V2

    @pytest.mark.asyncio
    async def test_get_version_wrong_architecture_returns_none(self, db_session):
        arch_id = await _seed_architecture(db_session)
        from app.services.version_service import create_version, get_version

        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1))
        v = await get_version(db_session, "nonexistent-arch-id", 1)
        assert v is None


class TestDiffVersions:
    """Tests for version_service.diff_versions (pure function)."""

    def test_identical_versions_no_changes(self):
        from app.services.version_service import diff_versions

        diff = diff_versions(json.dumps(SAMPLE_ARCH_V1), json.dumps(SAMPLE_ARCH_V1))
        assert diff.added_components == []
        assert diff.removed_components == []
        assert diff.modified_components == []
        assert diff.summary == "No changes detected"

    def test_added_components(self):
        from app.services.version_service import diff_versions

        a = json.dumps({"management_groups": {}})
        b = json.dumps({"management_groups": {}, "subscriptions": [{"name": "Prod"}]})
        diff = diff_versions(a, b)
        assert len(diff.added_components) == 1
        assert diff.added_components[0].name == "subscriptions"

    def test_removed_components(self):
        from app.services.version_service import diff_versions

        a = json.dumps({"management_groups": {}, "subscriptions": [{"name": "Prod"}]})
        b = json.dumps({"management_groups": {}})
        diff = diff_versions(a, b)
        assert len(diff.removed_components) == 1
        assert diff.removed_components[0].name == "subscriptions"

    def test_modified_components_dict(self):
        from app.services.version_service import diff_versions

        a = json.dumps({"network_topology": {"type": "hub-spoke"}})
        b = json.dumps({"network_topology": {"type": "flat"}})
        diff = diff_versions(a, b)
        assert len(diff.modified_components) == 1
        assert diff.modified_components[0].name == "network_topology"

    def test_modified_components_list_added_items(self):
        from app.services.version_service import diff_versions

        a = json.dumps({"subscriptions": [{"name": "Prod"}]})
        b = json.dumps({"subscriptions": [{"name": "Prod"}, {"name": "Dev"}]})
        diff = diff_versions(a, b)
        assert len(diff.modified_components) == 1
        assert "added" in diff.modified_components[0].detail

    def test_modified_components_list_removed_items(self):
        from app.services.version_service import diff_versions

        a = json.dumps({"subscriptions": [{"name": "Prod"}, {"name": "Dev"}]})
        b = json.dumps({"subscriptions": [{"name": "Prod"}]})
        diff = diff_versions(a, b)
        assert len(diff.modified_components) == 1
        assert "removed" in diff.modified_components[0].detail

    def test_modified_components_list_same_count(self):
        from app.services.version_service import diff_versions

        a = json.dumps({"subscriptions": [{"name": "Prod"}]})
        b = json.dumps({"subscriptions": [{"name": "Staging"}]})
        diff = diff_versions(a, b)
        assert len(diff.modified_components) == 1
        assert "modified" in diff.modified_components[0].detail

    def test_complex_diff_v1_to_v2(self):
        from app.services.version_service import diff_versions

        diff = diff_versions(json.dumps(SAMPLE_ARCH_V1), json.dumps(SAMPLE_ARCH_V2))
        added_names = {c.name for c in diff.added_components}
        modified_names = {c.name for c in diff.modified_components}
        assert "compliance_frameworks" in added_names
        assert "management_groups" in modified_names
        assert "subscriptions" in modified_names

    def test_summary_format(self):
        from app.services.version_service import diff_versions

        diff = diff_versions(json.dumps(SAMPLE_ARCH_V1), json.dumps(SAMPLE_ARCH_V2))
        assert "added" in diff.summary
        assert "modified" in diff.summary

    def test_empty_to_full(self):
        from app.services.version_service import diff_versions

        diff = diff_versions(json.dumps({}), json.dumps(SAMPLE_ARCH_V1))
        assert len(diff.added_components) >= 3  # mg, subs, network, policies

    def test_full_to_empty(self):
        from app.services.version_service import diff_versions

        diff = diff_versions(json.dumps(SAMPLE_ARCH_V1), json.dumps({}))
        assert len(diff.removed_components) >= 3

    def test_diff_dict_added_keys(self):
        from app.services.version_service import diff_versions

        a = json.dumps({"policies": {"tagging": True}})
        b = json.dumps({"policies": {"tagging": True, "naming": True}})
        diff = diff_versions(a, b)
        assert len(diff.modified_components) == 1
        assert "added" in diff.modified_components[0].detail

    def test_diff_dict_removed_keys(self):
        from app.services.version_service import diff_versions

        a = json.dumps({"policies": {"tagging": True, "naming": True}})
        b = json.dumps({"policies": {"tagging": True}})
        diff = diff_versions(a, b)
        assert len(diff.modified_components) == 1
        assert "removed" in diff.modified_components[0].detail

    def test_diff_scalar_value_changed(self):
        from app.services.version_service import diff_versions

        a = json.dumps({"network_topology": "hub-spoke"})
        b = json.dumps({"network_topology": "flat"})
        diff = diff_versions(a, b)
        assert len(diff.modified_components) == 1
        assert "changed" in diff.modified_components[0].detail

    def test_diff_captures_custom_keys(self):
        """Keys beyond the standard component list are also captured."""
        from app.services.version_service import diff_versions

        a = json.dumps({"custom_config": {"key": "val"}})
        b = json.dumps({"custom_config": {"key": "new_val"}})
        diff = diff_versions(a, b)
        assert len(diff.modified_components) == 1
        assert diff.modified_components[0].name == "custom_config"

    def test_diff_ignores_metadata_keys(self):
        """Metadata like 'version', 'status', 'id' should be ignored."""
        from app.services.version_service import diff_versions

        a = json.dumps({"version": 1, "status": "draft", "management_groups": {}})
        b = json.dumps({"version": 2, "status": "active", "management_groups": {}})
        diff = diff_versions(a, b)
        assert diff.added_components == []
        assert diff.removed_components == []
        assert diff.modified_components == []


class TestRestoreVersion:
    """Tests for version_service.restore_version."""

    @pytest.mark.asyncio
    async def test_restore_creates_new_version(self, db_session):
        arch_id = await _seed_architecture(db_session)
        from app.services.version_service import create_version, list_versions, restore_version

        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1))
        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V2))

        restored = await restore_version(db_session, arch_id, 1)
        assert restored is not None
        assert restored.version_number == 3
        assert json.loads(restored.architecture_json) == SAMPLE_ARCH_V1

    @pytest.mark.asyncio
    async def test_restore_default_summary(self, db_session):
        arch_id = await _seed_architecture(db_session)
        from app.services.version_service import create_version, restore_version

        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1))
        restored = await restore_version(db_session, arch_id, 1)
        assert "Restored from version 1" in restored.change_summary

    @pytest.mark.asyncio
    async def test_restore_custom_summary(self, db_session):
        arch_id = await _seed_architecture(db_session)
        from app.services.version_service import create_version, restore_version

        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1))
        restored = await restore_version(
            db_session, arch_id, 1, change_summary="Rolling back policy change",
        )
        assert restored.change_summary == "Rolling back policy change"

    @pytest.mark.asyncio
    async def test_restore_nonexistent_returns_none(self, db_session):
        arch_id = await _seed_architecture(db_session)
        from app.services.version_service import restore_version

        result = await restore_version(db_session, arch_id, 99)
        assert result is None

    @pytest.mark.asyncio
    async def test_restore_records_user(self, db_session):
        arch_id = await _seed_architecture(db_session)
        from app.services.version_service import create_version, restore_version

        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1))
        restored = await restore_version(
            db_session, arch_id, 1, created_by="restore-user",
        )
        assert restored.created_by == "restore-user"

    @pytest.mark.asyncio
    async def test_restore_preserves_original_data(self, db_session):
        """Restoring v1 after v2 produces v3 with identical data to v1."""
        arch_id = await _seed_architecture(db_session)
        from app.services.version_service import create_version, get_version, restore_version

        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1))
        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V2))
        await restore_version(db_session, arch_id, 1)

        v1 = await get_version(db_session, arch_id, 1)
        v3 = await get_version(db_session, arch_id, 3)
        assert v1.architecture_json == v3.architecture_json


# ===========================================================================
# ROUTE-LEVEL TESTS (via AsyncClient)
# ===========================================================================

class TestVersionRoutes:
    """Integration tests for /api/architectures/{arch_id}/versions endpoints."""

    @pytest.mark.asyncio
    async def test_list_versions_empty(self, client, db_session):
        arch_id = await _seed_project_and_architecture(db_session)
        await db_session.commit()
        resp = await client.get(f"/api/architectures/{arch_id}/versions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["versions"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_versions_after_creation(self, client, db_session):
        arch_id = await _seed_project_and_architecture(db_session)
        from app.services.version_service import create_version

        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1), change_summary="v1")
        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V2), change_summary="v2")
        await db_session.commit()

        resp = await client.get(f"/api/architectures/{arch_id}/versions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["versions"][0]["version_number"] == 2
        assert data["versions"][1]["version_number"] == 1

    @pytest.mark.asyncio
    async def test_get_specific_version(self, client, db_session):
        arch_id = await _seed_project_and_architecture(db_session)
        from app.services.version_service import create_version

        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1), change_summary="v1")
        await db_session.commit()

        resp = await client.get(f"/api/architectures/{arch_id}/versions/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["version_number"] == 1
        assert data["change_summary"] == "v1"
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_version_not_found(self, client, db_session):
        arch_id = await _seed_project_and_architecture(db_session)
        await db_session.commit()
        resp = await client.get(f"/api/architectures/{arch_id}/versions/999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_version_returns_full_json(self, client, db_session):
        arch_id = await _seed_project_and_architecture(db_session)
        from app.services.version_service import create_version

        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1))
        await db_session.commit()

        resp = await client.get(f"/api/architectures/{arch_id}/versions/1")
        data = resp.json()
        parsed = json.loads(data["architecture_json"])
        assert parsed == SAMPLE_ARCH_V1

    @pytest.mark.asyncio
    async def test_restore_version_creates_new(self, client, db_session):
        arch_id = await _seed_project_and_architecture(db_session)
        from app.services.version_service import create_version

        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1), change_summary="v1")
        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V2), change_summary="v2")
        await db_session.commit()

        resp = await client.post(
            f"/api/architectures/{arch_id}/versions/1/restore",
            json={"change_summary": "Rollback to v1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["version_number"] == 3
        assert json.loads(data["architecture_json"]) == SAMPLE_ARCH_V1
        assert data["change_summary"] == "Rollback to v1"

    @pytest.mark.asyncio
    async def test_restore_without_body(self, client, db_session):
        arch_id = await _seed_project_and_architecture(db_session)
        from app.services.version_service import create_version

        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1))
        await db_session.commit()

        resp = await client.post(f"/api/architectures/{arch_id}/versions/1/restore")
        assert resp.status_code == 200
        data = resp.json()
        assert "Restored from version 1" in data["change_summary"]

    @pytest.mark.asyncio
    async def test_restore_not_found(self, client, db_session):
        arch_id = await _seed_project_and_architecture(db_session)
        await db_session.commit()
        resp = await client.post(f"/api/architectures/{arch_id}/versions/999/restore")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_diff_versions(self, client, db_session):
        arch_id = await _seed_project_and_architecture(db_session)
        from app.services.version_service import create_version

        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1))
        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V2))
        await db_session.commit()

        resp = await client.get(
            f"/api/architectures/{arch_id}/versions/diff",
            params={"from": 1, "to": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["from_version"] == 1
        assert data["to_version"] == 2
        assert "added_components" in data
        assert "removed_components" in data
        assert "modified_components" in data
        assert "summary" in data

    @pytest.mark.asyncio
    async def test_diff_shows_correct_changes(self, client, db_session):
        arch_id = await _seed_project_and_architecture(db_session)
        from app.services.version_service import create_version

        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1))
        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V2))
        await db_session.commit()

        resp = await client.get(
            f"/api/architectures/{arch_id}/versions/diff",
            params={"from": 1, "to": 2},
        )
        data = resp.json()
        added_names = {c["name"] for c in data["added_components"]}
        modified_names = {c["name"] for c in data["modified_components"]}
        assert "compliance_frameworks" in added_names
        assert "subscriptions" in modified_names

    @pytest.mark.asyncio
    async def test_diff_version_not_found_from(self, client, db_session):
        arch_id = await _seed_project_and_architecture(db_session)
        from app.services.version_service import create_version

        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1))
        await db_session.commit()

        resp = await client.get(
            f"/api/architectures/{arch_id}/versions/diff",
            params={"from": 99, "to": 1},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_diff_version_not_found_to(self, client, db_session):
        arch_id = await _seed_project_and_architecture(db_session)
        from app.services.version_service import create_version

        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1))
        await db_session.commit()

        resp = await client.get(
            f"/api/architectures/{arch_id}/versions/diff",
            params={"from": 1, "to": 99},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_restore_records_created_by(self, client, db_session):
        arch_id = await _seed_project_and_architecture(db_session)
        from app.services.version_service import create_version

        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1))
        await db_session.commit()

        resp = await client.post(f"/api/architectures/{arch_id}/versions/1/restore")
        data = resp.json()
        assert data["created_by"] == "test-user-id"

    @pytest.mark.asyncio
    async def test_list_after_restore_includes_new_version(self, client, db_session):
        arch_id = await _seed_project_and_architecture(db_session)
        from app.services.version_service import create_version

        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1))
        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V2))
        await db_session.commit()

        await client.post(f"/api/architectures/{arch_id}/versions/1/restore")

        resp = await client.get(f"/api/architectures/{arch_id}/versions")
        data = resp.json()
        assert data["total"] == 3
        assert data["versions"][0]["version_number"] == 3

    @pytest.mark.asyncio
    async def test_diff_self_version(self, client, db_session):
        """Diffing a version against itself should show no changes."""
        arch_id = await _seed_project_and_architecture(db_session)
        from app.services.version_service import create_version

        await create_version(db_session, arch_id, json.dumps(SAMPLE_ARCH_V1))
        await db_session.commit()

        resp = await client.get(
            f"/api/architectures/{arch_id}/versions/diff",
            params={"from": 1, "to": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"] == "No changes detected"

    @pytest.mark.asyncio
    async def test_version_response_has_all_fields(self, client, db_session):
        arch_id = await _seed_project_and_architecture(db_session)
        from app.services.version_service import create_version

        await create_version(
            db_session, arch_id, json.dumps(SAMPLE_ARCH_V1),
            change_summary="test", created_by="test-user-id",
        )
        await db_session.commit()

        resp = await client.get(f"/api/architectures/{arch_id}/versions/1")
        data = resp.json()
        expected_keys = {"id", "version_number", "architecture_json", "change_summary", "created_by", "created_at"}
        assert expected_keys.issubset(set(data.keys()))


# ===========================================================================
# MODEL-LEVEL TESTS
# ===========================================================================

class TestArchitectureVersionModel:
    """Tests for the ArchitectureVersion SQLAlchemy model."""

    @pytest.mark.asyncio
    async def test_model_table_name(self):
        from app.models.architecture_version import ArchitectureVersion
        assert ArchitectureVersion.__tablename__ == "architecture_versions"

    @pytest.mark.asyncio
    async def test_model_creates_in_db(self, db_session):
        arch_id = await _seed_architecture(db_session)
        from app.models.architecture_version import ArchitectureVersion

        v = ArchitectureVersion(
            architecture_id=arch_id,
            version_number=1,
            architecture_json=json.dumps(SAMPLE_ARCH_V1),
        )
        db_session.add(v)
        await db_session.flush()
        assert v.id is not None

    @pytest.mark.asyncio
    async def test_model_timestamps(self, db_session):
        arch_id = await _seed_architecture(db_session)
        from app.models.architecture_version import ArchitectureVersion

        v = ArchitectureVersion(
            architecture_id=arch_id,
            version_number=1,
            architecture_json="{}",
        )
        db_session.add(v)
        await db_session.flush()
        assert v.created_at is not None
        assert v.updated_at is not None

    @pytest.mark.asyncio
    async def test_model_nullable_fields(self, db_session):
        arch_id = await _seed_architecture(db_session)
        from app.models.architecture_version import ArchitectureVersion

        v = ArchitectureVersion(
            architecture_id=arch_id,
            version_number=1,
            architecture_json="{}",
        )
        db_session.add(v)
        await db_session.flush()
        assert v.change_summary is None
        assert v.created_by is None


# ===========================================================================
# SCHEMA-LEVEL TESTS
# ===========================================================================

class TestVersionSchemas:
    """Tests for Pydantic version schemas."""

    def test_version_response_from_attributes(self):
        from app.schemas.version import ArchitectureVersionResponse
        from datetime import datetime

        data = {
            "id": "abc-123",
            "version_number": 1,
            "architecture_json": "{}",
            "change_summary": "Initial",
            "created_by": "user-1",
            "created_at": datetime.now(),
        }
        resp = ArchitectureVersionResponse(**data)
        assert resp.version_number == 1
        assert resp.id == "abc-123"

    def test_version_list_response(self):
        from app.schemas.version import ArchitectureVersionResponse, VersionListResponse
        from datetime import datetime

        v = ArchitectureVersionResponse(
            id="a", version_number=1, architecture_json="{}",
            created_at=datetime.now(),
        )
        lst = VersionListResponse(versions=[v], total=1)
        assert lst.total == 1
        assert len(lst.versions) == 1

    def test_version_diff_response(self):
        from app.schemas.version import ComponentChange, VersionDiffResponse

        diff = VersionDiffResponse(
            from_version=1, to_version=2,
            added_components=[ComponentChange(name="policies", detail="Added policies")],
            removed_components=[],
            modified_components=[],
            summary="1 component(s) added",
        )
        assert diff.from_version == 1
        assert len(diff.added_components) == 1

    def test_restore_request_optional_summary(self):
        from app.schemas.version import RestoreVersionRequest

        req = RestoreVersionRequest()
        assert req.change_summary is None

    def test_restore_request_with_summary(self):
        from app.schemas.version import RestoreVersionRequest

        req = RestoreVersionRequest(change_summary="Rolling back")
        assert req.change_summary == "Rolling back"

    def test_component_change(self):
        from app.schemas.version import ComponentChange

        c = ComponentChange(name="network_topology", detail="Type changed")
        assert c.name == "network_topology"
        assert c.detail == "Type changed"
