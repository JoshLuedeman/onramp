"""Tests for enterprise infrastructure — project RBAC, tenant lifecycle,
audit logging, marketplace safety.

Targets: 75+ tests across all four feature areas plus schema validation.
"""

import csv
import io
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.main import app

client = TestClient(app)


# =====================================================================
# 1. Project RBAC — role hierarchy, permission checks, effective roles
# =====================================================================

class TestProjectRBACRoleHierarchy:
    """Verify the ROLE_HIERARCHY mapping and rank logic."""

    def test_hierarchy_mapping_importable(self):
        from app.services.project_rbac_service import ROLE_HIERARCHY
        assert isinstance(ROLE_HIERARCHY, dict)

    def test_admin_is_highest(self):
        from app.services.project_rbac_service import ROLE_HIERARCHY
        assert ROLE_HIERARCHY["admin"] > ROLE_HIERARCHY["owner"]

    def test_owner_outranks_reviewer(self):
        from app.services.project_rbac_service import ROLE_HIERARCHY
        assert ROLE_HIERARCHY["owner"] > ROLE_HIERARCHY["reviewer"]

    def test_reviewer_outranks_contributor(self):
        from app.services.project_rbac_service import ROLE_HIERARCHY
        assert ROLE_HIERARCHY["reviewer"] > ROLE_HIERARCHY["contributor"]

    def test_contributor_outranks_viewer(self):
        from app.services.project_rbac_service import ROLE_HIERARCHY
        assert ROLE_HIERARCHY["contributor"] > ROLE_HIERARCHY["viewer"]

    def test_viewer_is_lowest(self):
        from app.services.project_rbac_service import ROLE_HIERARCHY
        assert ROLE_HIERARCHY["viewer"] == 0

    def test_editor_alias_ranks_above_reviewer(self):
        from app.services.project_rbac_service import ROLE_HIERARCHY
        assert ROLE_HIERARCHY["editor"] > ROLE_HIERARCHY["reviewer"]

    def test_unknown_role_returns_negative(self):
        from app.services.project_rbac_service import ProjectRBACService
        svc = ProjectRBACService()
        assert svc._role_rank("nonexistent") == -1


class TestProjectRBACServiceUnit:
    """Unit tests for ProjectRBACService with mocked DB."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from app.services.project_rbac_service import ProjectRBACService
        self.svc = ProjectRBACService()

    @pytest.mark.asyncio
    async def test_effective_role_global_admin(self):
        """Global admin always returns 'admin'."""
        mock_db = AsyncMock()
        # User row with role='admin'
        user_row = MagicMock()
        user_row.role = "admin"
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user_row
        mock_db.execute = AsyncMock(return_value=user_result)

        role = await self.svc.get_effective_role(
            mock_db, "proj-1", "user-1",
        )
        assert role == "admin"

    @pytest.mark.asyncio
    async def test_effective_role_project_member(self):
        """Project member gets their membership role."""
        mock_db = AsyncMock()
        # User row with role='viewer' (not admin)
        user_row = MagicMock()
        user_row.role = "viewer"
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user_row

        # Project membership with role='owner'
        member_row = MagicMock()
        member_row.role = "owner"
        member_result = MagicMock()
        member_result.scalar_one_or_none.return_value = member_row

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return user_result
            return member_result

        mock_db.execute = AsyncMock(side_effect=side_effect)

        role = await self.svc.get_effective_role(
            mock_db, "proj-1", "user-1",
        )
        assert role == "owner"

    @pytest.mark.asyncio
    async def test_effective_role_no_access(self):
        """No global role and no membership returns None."""
        mock_db = AsyncMock()
        empty = MagicMock()
        empty.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=empty)

        role = await self.svc.get_effective_role(
            mock_db, "proj-1", "user-1",
        )
        assert role is None

    @pytest.mark.asyncio
    async def test_check_permission_allowed(self):
        """Permission granted when effective role >= required role."""
        with patch.object(
            self.svc, "get_effective_role",
            new_callable=AsyncMock, return_value="owner",
        ):
            result = await self.svc.check_project_permission(
                AsyncMock(), "proj-1", "user-1", "editor",
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_check_permission_denied(self):
        """Permission denied when effective role < required role."""
        with patch.object(
            self.svc, "get_effective_role",
            new_callable=AsyncMock, return_value="viewer",
        ):
            result = await self.svc.check_project_permission(
                AsyncMock(), "proj-1", "user-1", "owner",
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_check_permission_no_role(self):
        """Permission denied when no effective role."""
        with patch.object(
            self.svc, "get_effective_role",
            new_callable=AsyncMock, return_value=None,
        ):
            result = await self.svc.check_project_permission(
                AsyncMock(), "proj-1", "user-1", "viewer",
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_effective_role_higher_global_wins(self):
        """When global role outranks project role, global wins."""
        mock_db = AsyncMock()
        user_row = MagicMock()
        user_row.role = "owner"
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user_row

        member_row = MagicMock()
        member_row.role = "viewer"
        member_result = MagicMock()
        member_result.scalar_one_or_none.return_value = member_row

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return user_result if call_count == 1 else member_result

        mock_db.execute = AsyncMock(side_effect=side_effect)

        role = await self.svc.get_effective_role(
            mock_db, "proj-1", "user-1",
        )
        assert role == "owner"


class TestProjectRBACRoutes:
    """Test the project RBAC HTTP endpoints."""

    def test_get_permissions_dev_mode(self):
        """Dev mode returns admin role."""
        r = client.get("/api/projects/proj-1/permissions")
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == "proj-1"
        assert data["effective_role"] == "admin"

    def test_list_roles_dev_mode(self):
        """Dev mode returns empty member list."""
        r = client.get("/api/projects/proj-1/roles")
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == "proj-1"
        assert data["members"] == []

    def test_require_project_role_factory(self):
        """require_project_role returns a callable."""
        from app.services.project_rbac_service import project_rbac
        dep = project_rbac.require_project_role("owner")
        assert callable(dep)


# =====================================================================
# 2. Tenant Lifecycle — provision, settings, offboard
# =====================================================================

class TestTenantLifecycleSchemas:
    """Validate Pydantic schemas for tenant lifecycle."""

    def test_resource_limits_defaults(self):
        from app.schemas.tenant_lifecycle import ResourceLimits
        limits = ResourceLimits()
        assert limits.max_projects == 50
        assert limits.max_users == 100
        assert limits.ai_budget == 1000.0

    def test_resource_limits_custom(self):
        from app.schemas.tenant_lifecycle import ResourceLimits
        limits = ResourceLimits(
            max_projects=10, max_users=20, ai_budget=500.0,
        )
        assert limits.max_projects == 10
        assert limits.max_users == 20

    def test_resource_limits_min_values(self):
        from app.schemas.tenant_lifecycle import ResourceLimits
        limits = ResourceLimits(max_projects=1, max_users=1, ai_budget=0)
        assert limits.max_projects == 1

    def test_resource_limits_rejects_negative_budget(self):
        from app.schemas.tenant_lifecycle import ResourceLimits
        with pytest.raises(Exception):
            ResourceLimits(ai_budget=-1)

    def test_provision_request_valid(self):
        from app.schemas.tenant_lifecycle import TenantProvisionRequest
        req = TenantProvisionRequest(
            name="Acme Corp",
            admin_email="admin@acme.com",
        )
        assert req.name == "Acme Corp"
        assert req.admin_email == "admin@acme.com"
        assert req.resource_limits.max_projects == 50

    def test_provision_request_custom_limits(self):
        from app.schemas.tenant_lifecycle import (
            ResourceLimits,
            TenantProvisionRequest,
        )
        req = TenantProvisionRequest(
            name="BigCo",
            admin_email="admin@bigco.com",
            resource_limits=ResourceLimits(max_projects=500),
        )
        assert req.resource_limits.max_projects == 500

    def test_provision_request_empty_name_rejected(self):
        from app.schemas.tenant_lifecycle import TenantProvisionRequest
        with pytest.raises(Exception):
            TenantProvisionRequest(name="", admin_email="a@b.com")

    def test_offboard_request_defaults(self):
        from app.schemas.tenant_lifecycle import TenantOffboardRequest
        req = TenantOffboardRequest()
        assert req.archive is True
        assert req.retention_days == 90

    def test_offboard_request_custom(self):
        from app.schemas.tenant_lifecycle import TenantOffboardRequest
        req = TenantOffboardRequest(archive=False, retention_days=30)
        assert req.archive is False
        assert req.retention_days == 30

    def test_offboard_rejects_excessive_retention(self):
        from app.schemas.tenant_lifecycle import TenantOffboardRequest
        with pytest.raises(Exception):
            TenantOffboardRequest(retention_days=9999)

    def test_settings_update_partial(self):
        from app.schemas.tenant_lifecycle import TenantSettingsUpdate
        update = TenantSettingsUpdate(
            feature_flags={"ai_enabled": True},
        )
        assert update.resource_limits is None
        assert update.feature_flags == {"ai_enabled": True}

    def test_settings_response_model(self):
        from app.schemas.tenant_lifecycle import (
            ResourceLimits,
            TenantSettingsResponse,
        )
        resp = TenantSettingsResponse(
            tenant_id="t-1",
            name="Test",
            is_active=True,
            resource_limits=ResourceLimits(),
            created_at=datetime.now(timezone.utc),
        )
        assert resp.tenant_id == "t-1"
        assert resp.feature_flags == {}


class TestTenantServiceLifecycle:
    """Unit tests for enhanced TenantService lifecycle methods."""

    @pytest.mark.asyncio
    async def test_provision_tenant(self):
        from app.schemas.tenant_lifecycle import TenantProvisionRequest
        from app.services.tenant_service import TenantService

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        svc = TenantService(mock_db)
        req = TenantProvisionRequest(
            name="TestCo", admin_email="admin@test.co",
        )

        # Patch Tenant class to return a mock with expected fields
        mock_tenant = MagicMock()
        mock_tenant.id = "mock-uuid"
        mock_tenant.name = "TestCo"
        mock_tenant.is_active = True
        mock_tenant.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

        with patch(
            "app.services.tenant_service.Tenant",
            return_value=mock_tenant,
        ):
            result = await svc.provision_tenant(req)

        assert result.name == "TestCo"
        assert result.is_active is True
        assert result.resource_limits.max_projects == 50
        assert result.tenant_id == "mock-uuid"
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tenant_settings_not_found(self):
        from app.services.tenant_service import TenantService

        mock_db = AsyncMock()
        empty = MagicMock()
        empty.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=empty)

        svc = TenantService(mock_db)
        result = await svc.get_tenant_settings("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_offboard_tenant_not_found(self):
        from app.services.tenant_service import TenantService

        mock_db = AsyncMock()
        empty = MagicMock()
        empty.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=empty)

        svc = TenantService(mock_db)
        result = await svc.offboard_tenant("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_offboard_tenant_deactivates(self):
        from app.services.tenant_service import TenantService

        tenant = MagicMock()
        tenant.id = "t-1"
        tenant.name = "TestCo"
        tenant.is_active = True

        mock_db = AsyncMock()
        found = MagicMock()
        found.scalar_one_or_none.return_value = tenant
        mock_db.execute = AsyncMock(return_value=found)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        svc = TenantService(mock_db)
        result = await svc.offboard_tenant("t-1", archive=True, retention_days=60)

        assert result is not None
        assert result.archive is True
        assert result.retention_days == 60
        assert tenant.is_active is False

    @pytest.mark.asyncio
    async def test_update_settings_not_found(self):
        from app.schemas.tenant_lifecycle import TenantSettingsUpdate
        from app.services.tenant_service import TenantService

        mock_db = AsyncMock()
        empty = MagicMock()
        empty.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=empty)

        svc = TenantService(mock_db)
        update = TenantSettingsUpdate(feature_flags={"x": True})
        result = await svc.update_tenant_settings("nope", update)
        assert result is None


class TestTenantLifecycleRoutes:
    """Test tenant lifecycle HTTP endpoints."""

    def test_provision_no_db(self):
        """Without DB, returns 503."""
        r = client.post("/api/tenants/provision", json={
            "name": "Test",
            "admin_email": "admin@test.com",
        })
        assert r.status_code == 503

    def test_get_settings_no_db(self):
        r = client.get("/api/tenants/test-id/settings")
        assert r.status_code == 503

    def test_update_settings_no_db(self):
        r = client.put(
            "/api/tenants/test-id/settings",
            json={"feature_flags": {"a": True}},
        )
        assert r.status_code == 503

    def test_offboard_no_db(self):
        r = client.post(
            "/api/tenants/test-id/offboard",
            json={"archive": True, "retention_days": 30},
        )
        assert r.status_code == 503


# =====================================================================
# 3. Enterprise Audit Logging — model, service, routes, middleware
# =====================================================================

class TestEnterpriseAuditModel:
    """Verify the EnterpriseAuditEvent ORM model."""

    def test_model_importable(self):
        from app.models.enterprise_audit import EnterpriseAuditEvent
        assert EnterpriseAuditEvent.__tablename__ == "enterprise_audit_events"

    def test_model_in_init(self):
        from app.models import EnterpriseAuditEvent
        assert EnterpriseAuditEvent is not None

    def test_model_columns_exist(self):
        from app.models.enterprise_audit import EnterpriseAuditEvent
        cols = {c.name for c in EnterpriseAuditEvent.__table__.columns}
        expected = {
            "id", "event_type", "actor_id", "tenant_id",
            "resource_type", "resource_id", "action",
            "details", "ip_address", "user_agent", "timestamp",
        }
        assert expected.issubset(cols)

    def test_model_has_indexes(self):
        from app.models.enterprise_audit import EnterpriseAuditEvent
        idx_names = {
            idx.name for idx in EnterpriseAuditEvent.__table__.indexes
        }
        assert "ix_ent_audit_tenant_ts" in idx_names
        assert "ix_ent_audit_actor_ts" in idx_names
        assert "ix_ent_audit_resource" in idx_names

    def test_model_has_foreign_keys(self):
        from app.models.enterprise_audit import EnterpriseAuditEvent
        fk_targets = set()
        for col in EnterpriseAuditEvent.__table__.columns:
            for fk in col.foreign_keys:
                fk_targets.add(fk.target_fullname)
        assert "users.id" in fk_targets
        assert "tenants.id" in fk_targets


class TestAuditServiceUnit:
    """Unit tests for AuditService."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from app.services.audit_service import AuditService
        self.svc = AuditService()

    def test_action_from_method_post(self):
        assert self.svc.action_from_method("POST") == "create"

    def test_action_from_method_get(self):
        assert self.svc.action_from_method("GET") == "read"

    def test_action_from_method_put(self):
        assert self.svc.action_from_method("PUT") == "update"

    def test_action_from_method_patch(self):
        assert self.svc.action_from_method("PATCH") == "update"

    def test_action_from_method_delete(self):
        assert self.svc.action_from_method("DELETE") == "delete"

    def test_action_from_method_unknown(self):
        assert self.svc.action_from_method("OPTIONS") == "read"

    def test_action_from_method_case_insensitive(self):
        assert self.svc.action_from_method("post") == "create"

    @pytest.mark.asyncio
    async def test_log_event_creates_record(self):
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        event = await self.svc.log_event(
            mock_db,
            event_type="test.action",
            actor_id="user-1",
            tenant_id="t-1",
            resource_type="project",
            resource_id="p-1",
            action="create",
            details={"key": "value"},
        )
        mock_db.add.assert_called_once()
        assert event.event_type == "test.action"
        assert event.action == "create"

    @pytest.mark.asyncio
    async def test_log_event_extracts_ip_from_forwarded(self):
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        mock_request = MagicMock()
        mock_request.headers = {"x-forwarded-for": "1.2.3.4, 5.6.7.8"}
        mock_request.client = None

        event = await self.svc.log_event(
            mock_db,
            event_type="test",
            action="read",
            request=mock_request,
        )
        assert event.ip_address == "1.2.3.4"

    @pytest.mark.asyncio
    async def test_log_event_extracts_ip_from_client(self):
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client.host = "10.0.0.1"

        event = await self.svc.log_event(
            mock_db,
            event_type="test",
            action="read",
            request=mock_request,
        )
        assert event.ip_address == "10.0.0.1"

    @pytest.mark.asyncio
    async def test_log_event_extracts_user_agent(self):
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()

        mock_request = MagicMock()
        mock_request.headers = {"user-agent": "TestAgent/1.0"}
        mock_request.client = None

        event = await self.svc.log_event(
            mock_db,
            event_type="test",
            action="read",
            request=mock_request,
        )
        assert event.user_agent == "TestAgent/1.0"

    @pytest.mark.asyncio
    async def test_query_events_empty(self):
        mock_db = AsyncMock()
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = []

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return count_result if call_count == 1 else events_result

        mock_db.execute = AsyncMock(side_effect=side_effect)

        result = await self.svc.query_events(mock_db, tenant_id="t-1")
        assert result["total"] == 0
        assert result["events"] == []
        assert result["page"] == 1

    @pytest.mark.asyncio
    async def test_export_events_json(self):
        with patch.object(
            self.svc, "query_events",
            new_callable=AsyncMock,
            return_value={
                "events": [
                    {"id": "e1", "event_type": "test", "action": "create"},
                ],
                "total": 1,
                "page": 1,
                "page_size": 10000,
            },
        ):
            result = await self.svc.export_events(
                AsyncMock(), fmt="json",
            )
            parsed = json.loads(result)
            assert len(parsed) == 1
            assert parsed[0]["id"] == "e1"

    @pytest.mark.asyncio
    async def test_export_events_csv(self):
        with patch.object(
            self.svc, "query_events",
            new_callable=AsyncMock,
            return_value={
                "events": [
                    {"id": "e1", "event_type": "test", "action": "create"},
                    {"id": "e2", "event_type": "test2", "action": "delete"},
                ],
                "total": 2,
                "page": 1,
                "page_size": 10000,
            },
        ):
            result = await self.svc.export_events(
                AsyncMock(), fmt="csv",
            )
            reader = csv.DictReader(io.StringIO(result))
            rows = list(reader)
            assert len(rows) == 2
            assert rows[0]["id"] == "e1"

    @pytest.mark.asyncio
    async def test_export_events_empty_csv(self):
        with patch.object(
            self.svc, "query_events",
            new_callable=AsyncMock,
            return_value={
                "events": [],
                "total": 0,
                "page": 1,
                "page_size": 10000,
            },
        ):
            result = await self.svc.export_events(
                AsyncMock(), fmt="csv",
            )
            assert result == ""

    def test_event_to_dict_structure(self):
        event = MagicMock()
        event.id = "e-1"
        event.event_type = "test"
        event.actor_id = "u-1"
        event.tenant_id = "t-1"
        event.resource_type = "project"
        event.resource_id = "p-1"
        event.action = "create"
        event.details = {"key": "val"}
        event.ip_address = "1.2.3.4"
        event.user_agent = "Agent/1"
        event.timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc)

        d = self.svc._event_to_dict(event)
        assert d["id"] == "e-1"
        assert d["event_type"] == "test"
        assert d["timestamp"] == "2024-01-01T00:00:00+00:00"

    def test_events_to_csv_empty(self):
        result = self.svc._events_to_csv([])
        assert result == ""

    def test_events_to_csv_with_data(self):
        rows = [
            {"id": "1", "action": "create"},
            {"id": "2", "action": "delete"},
        ]
        result = self.svc._events_to_csv(rows)
        assert "id,action" in result
        assert "1,create" in result


class TestAuditRoutes:
    """Test audit HTTP endpoints."""

    def test_query_events_no_db(self):
        r = client.get("/api/audit/events")
        assert r.status_code == 200
        data = r.json()
        assert data["events"] == []
        assert data["total"] == 0

    def test_query_events_with_filters(self):
        r = client.get(
            "/api/audit/events",
            params={
                "tenant_id": "t-1",
                "action": "create",
                "page": 1,
                "page_size": 10,
            },
        )
        assert r.status_code == 200

    def test_export_events_no_db(self):
        r = client.get("/api/audit/events/export")
        assert r.status_code == 503


class TestAuditMiddleware:
    """Test the ASGI audit middleware."""

    def test_middleware_importable(self):
        from app.middleware.audit_middleware import AuditMiddleware
        assert AuditMiddleware is not None

    def test_resource_from_path_basic(self):
        from app.middleware.audit_middleware import _resource_from_path
        rt, rid = _resource_from_path("/api/projects/p-123")
        assert rt == "projects"
        assert rid == "p-123"

    def test_resource_from_path_no_id(self):
        from app.middleware.audit_middleware import _resource_from_path
        rt, rid = _resource_from_path("/api/tenants")
        assert rt == "tenants"
        assert rid is None

    def test_resource_from_path_empty(self):
        from app.middleware.audit_middleware import _resource_from_path
        rt, rid = _resource_from_path("/")
        assert rt is None
        assert rid is None

    def test_resource_from_path_nested(self):
        from app.middleware.audit_middleware import _resource_from_path
        rt, rid = _resource_from_path("/api/projects/p-1/roles")
        assert rt == "projects"
        assert rid == "p-1"


# =====================================================================
# 4. Marketplace Safety — scan, publisher, review workflow
# =====================================================================

class TestTemplateSafetyScan:
    """Test template content scanning."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from app.services.template_safety_service import (
            TemplateSafetyService,
        )
        self.svc = TemplateSafetyService()

    def test_scan_empty_is_safe(self):
        result = self.svc.scan_template(None)
        assert result["safe"] is True
        assert result["findings"] == []

    def test_scan_clean_json(self):
        result = self.svc.scan_template('{"name": "safe template"}')
        assert result["safe"] is True

    def test_scan_detects_script_tag(self):
        result = self.svc.scan_template('<script>alert(1)</script>')
        assert result["safe"] is False
        assert any(
            "script" in f["message"].lower()
            for f in result["findings"]
        )

    def test_scan_detects_javascript_uri(self):
        result = self.svc.scan_template('javascript:alert(1)')
        assert result["safe"] is False

    def test_scan_detects_inline_handler(self):
        result = self.svc.scan_template('onclick=doStuff()')
        assert result["safe"] is False

    def test_scan_detects_eval(self):
        result = self.svc.scan_template('eval("code")')
        assert result["safe"] is False

    def test_scan_detects_function_constructor(self):
        result = self.svc.scan_template('Function("return this")')
        assert result["safe"] is False

    def test_scan_detects_wildcard_permissions(self):
        payload = json.dumps({
            "permissions": ["*"],
        })
        result = self.svc.scan_template(payload)
        assert result["safe"] is False

    def test_scan_detects_excessive_role(self):
        payload = json.dumps({"role": "Owner"})
        result = self.svc.scan_template(payload)
        assert result["safe"] is False

    def test_scan_multiple_findings(self):
        payload = '<script>eval("bad")</script>'
        result = self.svc.scan_template(payload)
        assert result["safe"] is False
        assert len(result["findings"]) >= 2

    def test_scan_dict_input(self):
        """scan_template handles dict input by serializing."""
        result = self.svc.scan_template({"name": "safe"})
        assert result["safe"] is True

    def test_scan_hex_escape_detection(self):
        result = self.svc.scan_template('\\x41\\x42')
        assert result["safe"] is False


class TestTemplateSafetyPublisher:
    """Test publisher verification."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from app.services.template_safety_service import (
            TemplateSafetyService,
        )
        self.svc = TemplateSafetyService()

    @pytest.mark.asyncio
    async def test_validate_publisher_not_found(self):
        mock_db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result_mock)

        result = await self.svc.validate_publisher(mock_db, "bad-tenant")
        assert result["verified"] is False
        assert "not found" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_validate_publisher_inactive(self):
        mock_db = AsyncMock()
        tenant = MagicMock()
        tenant.is_active = False
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = tenant
        mock_db.execute = AsyncMock(return_value=result_mock)

        result = await self.svc.validate_publisher(mock_db, "t-1")
        assert result["verified"] is False
        assert "deactivated" in result["reason"].lower()

    @pytest.mark.asyncio
    async def test_validate_publisher_active(self):
        mock_db = AsyncMock()
        tenant = MagicMock()
        tenant.is_active = True
        tenant.name = "GoodCo"
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = tenant
        mock_db.execute = AsyncMock(return_value=result_mock)

        result = await self.svc.validate_publisher(mock_db, "t-1")
        assert result["verified"] is True
        assert result["tenant_name"] == "GoodCo"


class TestTemplateSafetyReviewWorkflow:
    """Test the review workflow (submit / approve / reject)."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from app.services.template_safety_service import (
            TemplateSafetyService,
        )
        self.svc = TemplateSafetyService()

    @pytest.mark.asyncio
    async def test_submit_not_found(self):
        mock_db = AsyncMock()
        empty = MagicMock()
        empty.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=empty)

        result = await self.svc.submit_for_review(mock_db, "bad-id")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_submit_for_review(self):
        mock_db = AsyncMock()
        tpl = MagicMock()
        tpl.id = "t-1"
        tpl.name = "Test Template"
        tpl.visibility = "private"
        found = MagicMock()
        found.scalar_one_or_none.return_value = tpl
        mock_db.execute = AsyncMock(return_value=found)
        mock_db.flush = AsyncMock()

        result = await self.svc.submit_for_review(mock_db, "t-1")
        assert result["status"] == "pending_review"
        assert tpl.visibility == "pending_review"

    @pytest.mark.asyncio
    async def test_approve_not_found(self):
        mock_db = AsyncMock()
        empty = MagicMock()
        empty.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=empty)

        result = await self.svc.approve_template(
            mock_db, "bad-id", "reviewer-1",
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_approve_template(self):
        mock_db = AsyncMock()
        tpl = MagicMock()
        tpl.id = "t-1"
        tpl.name = "Good Template"
        tpl.visibility = "pending_review"
        found = MagicMock()
        found.scalar_one_or_none.return_value = tpl
        mock_db.execute = AsyncMock(return_value=found)
        mock_db.flush = AsyncMock()

        result = await self.svc.approve_template(
            mock_db, "t-1", "reviewer-1",
        )
        assert result["status"] == "approved"
        assert tpl.visibility == "public"

    @pytest.mark.asyncio
    async def test_reject_not_found(self):
        mock_db = AsyncMock()
        empty = MagicMock()
        empty.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=empty)

        result = await self.svc.reject_template(
            mock_db, "bad-id", "reviewer-1", "Bad content",
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_reject_template(self):
        mock_db = AsyncMock()
        tpl = MagicMock()
        tpl.id = "t-1"
        tpl.name = "Bad Template"
        tpl.visibility = "pending_review"
        found = MagicMock()
        found.scalar_one_or_none.return_value = tpl
        mock_db.execute = AsyncMock(return_value=found)
        mock_db.flush = AsyncMock()

        result = await self.svc.reject_template(
            mock_db, "t-1", "reviewer-1", "Contains malware",
        )
        assert result["status"] == "rejected"
        assert result["reason"] == "Contains malware"
        assert tpl.visibility == "rejected"

    @pytest.mark.asyncio
    async def test_list_pending_review(self):
        mock_db = AsyncMock()
        tpl = MagicMock()
        tpl.id = "t-1"
        tpl.name = "Pending Template"
        tpl.industry = "Healthcare"
        tpl.visibility = "pending_review"
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [tpl]
        mock_db.execute = AsyncMock(return_value=result_mock)

        result = await self.svc.list_pending_review(mock_db)
        assert len(result["templates"]) == 1
        assert result["templates"][0]["name"] == "Pending Template"


class TestTemplateSafetyRoutes:
    """Test template safety HTTP endpoints."""

    def test_scan_with_inline_json(self):
        r = client.post(
            "/api/templates/t-1/scan",
            json={"template_json": '{"safe": true}'},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["safe"] is True
        assert data["template_id"] == "t-1"

    def test_scan_detects_dangerous(self):
        r = client.post(
            "/api/templates/t-1/scan",
            json={"template_json": "<script>alert(1)</script>"},
        )
        assert r.status_code == 200
        assert r.json()["safe"] is False

    def test_submit_review_no_db(self):
        r = client.post("/api/templates/t-1/submit-review")
        assert r.status_code == 503

    def test_approve_no_db(self):
        r = client.post("/api/templates/t-1/approve")
        assert r.status_code == 503

    def test_reject_no_db(self):
        r = client.post(
            "/api/templates/t-1/reject",
            json={"reason": "Bad content"},
        )
        assert r.status_code == 503

    def test_pending_review_no_db(self):
        r = client.get("/api/templates/pending-review")
        assert r.status_code == 200
        data = r.json()
        assert data["templates"] == []


# =====================================================================
# 5. Schema validation for all new schemas
# =====================================================================

class TestSchemaValidation:
    """Cross-cutting schema validation tests."""

    def test_resource_limits_zero_budget(self):
        from app.schemas.tenant_lifecycle import ResourceLimits
        limits = ResourceLimits(ai_budget=0)
        assert limits.ai_budget == 0.0

    def test_provision_request_serializes(self):
        from app.schemas.tenant_lifecycle import TenantProvisionRequest
        req = TenantProvisionRequest(
            name="Serialize Test",
            admin_email="a@b.com",
        )
        d = req.model_dump()
        assert d["name"] == "Serialize Test"
        assert "resource_limits" in d

    def test_offboard_response_fields(self):
        from app.schemas.tenant_lifecycle import TenantOffboardResponse
        resp = TenantOffboardResponse(
            tenant_id="t-1",
            is_active=False,
            archive=True,
            retention_days=90,
            message="Offboarded",
        )
        assert resp.tenant_id == "t-1"
        assert resp.message == "Offboarded"

    def test_settings_response_from_attributes(self):
        from app.schemas.tenant_lifecycle import TenantSettingsResponse
        assert TenantSettingsResponse.model_config.get(
            "from_attributes",
        ) is True

    def test_resource_limits_model_dump(self):
        from app.schemas.tenant_lifecycle import ResourceLimits
        limits = ResourceLimits(
            max_projects=5, max_users=10, ai_budget=200.0,
        )
        d = limits.model_dump()
        assert d == {
            "max_projects": 5,
            "max_users": 10,
            "ai_budget": 200.0,
        }

    def test_settings_update_all_none(self):
        from app.schemas.tenant_lifecycle import TenantSettingsUpdate
        update = TenantSettingsUpdate()
        assert update.resource_limits is None
        assert update.feature_flags is None

    def test_provision_request_long_name(self):
        from app.schemas.tenant_lifecycle import TenantProvisionRequest
        name = "A" * 255
        req = TenantProvisionRequest(
            name=name, admin_email="a@b.com",
        )
        assert len(req.name) == 255

    def test_provision_request_too_long_name(self):
        from app.schemas.tenant_lifecycle import TenantProvisionRequest
        with pytest.raises(Exception):
            TenantProvisionRequest(
                name="A" * 256, admin_email="a@b.com",
            )

    def test_offboard_zero_retention(self):
        from app.schemas.tenant_lifecycle import TenantOffboardRequest
        req = TenantOffboardRequest(retention_days=0)
        assert req.retention_days == 0

    def test_resource_limits_max_boundary(self):
        from app.schemas.tenant_lifecycle import ResourceLimits
        limits = ResourceLimits(max_projects=10000, max_users=100000)
        assert limits.max_projects == 10000
        assert limits.max_users == 100000


# =====================================================================
# 6. Integration-style route tests (async)
# =====================================================================

class TestAsyncRoutes:
    """Async HTTP tests for new endpoints."""

    @pytest.mark.asyncio
    async def test_project_permissions_async(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test",
        ) as ac:
            r = await ac.get("/api/projects/p-1/permissions")
            assert r.status_code == 200
            assert r.json()["effective_role"] == "admin"

    @pytest.mark.asyncio
    async def test_project_roles_async(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test",
        ) as ac:
            r = await ac.get("/api/projects/p-1/roles")
            assert r.status_code == 200
            assert r.json()["members"] == []

    @pytest.mark.asyncio
    async def test_audit_query_async(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test",
        ) as ac:
            r = await ac.get("/api/audit/events")
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_pending_review_async(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test",
        ) as ac:
            r = await ac.get("/api/templates/pending-review")
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_scan_template_async(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test",
        ) as ac:
            r = await ac.post(
                "/api/templates/t-1/scan",
                json={"template_json": '{"ok": true}'},
            )
            assert r.status_code == 200
            assert r.json()["safe"] is True
