"""Tests for tagging compliance monitor, models, schemas, and API routes."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PROJECT_ID = "proj-test-tagging"


# ── Model & schema import tests ──────────────────────────────────────────────


class TestTaggingModelsImportable:
    """Verify models load and have correct table names."""

    def test_models_importable(self):
        from app.models import TaggingPolicy, TaggingScanResult, TaggingViolation

        assert TaggingPolicy.__tablename__ == "tagging_policies"
        assert TaggingScanResult.__tablename__ == "tagging_scan_results"
        assert TaggingViolation.__tablename__ == "tagging_violations"

    def test_models_in_metadata(self):
        from app.models import Base

        table_names = set(Base.metadata.tables.keys())
        assert "tagging_policies" in table_names
        assert "tagging_scan_results" in table_names
        assert "tagging_violations" in table_names

    def test_policy_has_expected_columns(self):
        from app.models.tagging import TaggingPolicy

        cols = {c.name for c in TaggingPolicy.__table__.columns}
        expected = {
            "id", "project_id", "tenant_id", "name", "required_tags",
            "created_at", "updated_at",
        }
        assert expected.issubset(cols)

    def test_scan_result_has_expected_columns(self):
        from app.models.tagging import TaggingScanResult

        cols = {c.name for c in TaggingScanResult.__table__.columns}
        expected = {
            "id", "project_id", "policy_id", "tenant_id",
            "total_resources", "compliant_count", "non_compliant_count",
            "compliance_percentage", "scan_timestamp", "status", "created_at",
        }
        assert expected.issubset(cols)

    def test_violation_has_expected_columns(self):
        from app.models.tagging import TaggingViolation

        cols = {c.name for c in TaggingViolation.__table__.columns}
        expected = {
            "id", "scan_result_id", "resource_id", "resource_type",
            "resource_name", "violation_type", "tag_name",
            "expected_value", "actual_value", "created_at",
        }
        assert expected.issubset(cols)

    def test_policy_indexes(self):
        from app.models.tagging import TaggingPolicy

        index_names = {idx.name for idx in TaggingPolicy.__table__.indexes}
        assert "ix_tagging_policies_project" in index_names

    def test_scan_result_indexes(self):
        from app.models.tagging import TaggingScanResult

        index_names = {idx.name for idx in TaggingScanResult.__table__.indexes}
        assert "ix_tagging_scan_results_project_timestamp" in index_names

    def test_violation_indexes(self):
        from app.models.tagging import TaggingViolation

        index_names = {idx.name for idx in TaggingViolation.__table__.indexes}
        assert "ix_tagging_violations_scan_result" in index_names


# ── Schema tests ─────────────────────────────────────────────────────────────


class TestTaggingSchemasImportable:
    """Verify schemas load and validate correctly."""

    def test_violation_type_enum(self):
        from app.schemas.tagging import ViolationType

        assert ViolationType.MISSING_TAG == "missing_tag"
        assert ViolationType.INVALID_VALUE == "invalid_value"
        assert ViolationType.NAMING_VIOLATION == "naming_violation"

    def test_tag_rule_schema(self):
        from app.schemas.tagging import TagRuleSchema

        rule = TagRuleSchema(
            name="Environment",
            required=True,
            allowed_values=["dev", "staging", "prod"],
            pattern=None,
        )
        assert rule.name == "Environment"
        assert rule.required is True
        assert rule.allowed_values == ["dev", "staging", "prod"]

    def test_tag_rule_schema_minimal(self):
        from app.schemas.tagging import TagRuleSchema

        rule = TagRuleSchema(name="Owner")
        assert rule.required is True
        assert rule.allowed_values is None
        assert rule.pattern is None

    def test_policy_create_schema(self):
        from app.schemas.tagging import TaggingPolicyCreate, TagRuleSchema

        payload = TaggingPolicyCreate(
            project_id="p1",
            name="Default Policy",
            required_tags=[
                TagRuleSchema(name="Environment", allowed_values=["dev", "prod"]),
                TagRuleSchema(name="Owner"),
            ],
        )
        assert payload.project_id == "p1"
        assert len(payload.required_tags) == 2
        assert payload.tenant_id is None

    def test_policy_update_schema(self):
        from app.schemas.tagging import TaggingPolicyUpdate

        update = TaggingPolicyUpdate(name="Updated Policy")
        assert update.name == "Updated Policy"
        assert update.required_tags is None

    def test_policy_response_schema(self):
        from app.schemas.tagging import TaggingPolicyResponse

        now = datetime.now(timezone.utc)
        resp = TaggingPolicyResponse(
            id="p1",
            project_id="proj1",
            name="Test",
            required_tags=[{"name": "Env", "required": True}],
            created_at=now,
            updated_at=now,
        )
        assert resp.id == "p1"
        assert resp.tenant_id is None

    def test_scan_result_response_schema(self):
        from app.schemas.tagging import TaggingScanResultResponse

        now = datetime.now(timezone.utc)
        resp = TaggingScanResultResponse(
            id="s1",
            project_id="proj1",
            policy_id="pol1",
            total_resources=10,
            compliant_count=8,
            non_compliant_count=2,
            compliance_percentage=80.0,
            scan_timestamp=now,
            status="completed",
            created_at=now,
        )
        assert resp.compliance_percentage == 80.0
        assert resp.violations == []

    def test_scan_result_list_schema(self):
        from app.schemas.tagging import TaggingScanResultList

        result_list = TaggingScanResultList(scan_results=[], total=0)
        assert result_list.scan_results == []
        assert result_list.total == 0

    def test_summary_defaults(self):
        from app.schemas.tagging import TaggingSummary

        summary = TaggingSummary(project_id="p1")
        assert summary.compliance_percentage == 0.0
        assert summary.total_resources == 0
        assert summary.compliant_count == 0
        assert summary.non_compliant_count == 0
        assert summary.violations_by_type["missing_tag"] == 0
        assert summary.violations_by_type["invalid_value"] == 0
        assert summary.violations_by_type["naming_violation"] == 0
        assert summary.worst_offending_resources == []
        assert summary.latest_scan_at is None
        assert summary.policy_name is None

    def test_violation_response_schema(self):
        from app.schemas.tagging import TaggingViolationResponse

        now = datetime.now(timezone.utc)
        v = TaggingViolationResponse(
            id="v1",
            scan_result_id="s1",
            resource_id="/sub/rg/vm1",
            resource_type="Microsoft.Compute/virtualMachines",
            violation_type="missing_tag",
            tag_name="Environment",
            created_at=now,
        )
        assert v.violation_type == "missing_tag"
        assert v.resource_name is None
        assert v.expected_value is None
        assert v.actual_value is None


# ── Tagging monitor unit tests ───────────────────────────────────────────────


class TestTaggingMonitorEvaluation:
    """Test the evaluate_compliance method directly."""

    @pytest.fixture
    def monitor(self):
        from app.services.tagging_monitor import TaggingMonitor
        return TaggingMonitor()

    @pytest.fixture
    def policy(self):
        return [
            {
                "name": "Environment",
                "required": True,
                "allowed_values": ["dev", "staging", "prod"],
                "pattern": None,
            },
            {
                "name": "Owner",
                "required": True,
                "allowed_values": None,
                "pattern": r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$",
            },
            {
                "name": "CostCenter",
                "required": True,
                "allowed_values": None,
                "pattern": r"^CC-\d{4,6}$",
            },
        ]

    @pytest.mark.asyncio
    async def test_fully_compliant_resource(self, monitor, policy):
        resources = [{
            "id": "/sub/rg/vm1",
            "type": "Microsoft.Compute/virtualMachines",
            "name": "vm1",
            "tags": {
                "Environment": "prod",
                "Owner": "alice@contoso.com",
                "CostCenter": "CC-1001",
            },
        }]
        result = await monitor.evaluate_compliance(resources, policy)
        assert result["total_resources"] == 1
        assert result["compliant_count"] == 1
        assert result["non_compliant_count"] == 0
        assert len(result["violations"]) == 0

    @pytest.mark.asyncio
    async def test_missing_tag_violation(self, monitor, policy):
        resources = [{
            "id": "/sub/rg/vm2",
            "type": "Microsoft.Compute/virtualMachines",
            "name": "vm2",
            "tags": {
                "Environment": "dev",
                "Owner": "bob@contoso.com",
                # Missing CostCenter
            },
        }]
        result = await monitor.evaluate_compliance(resources, policy)
        assert result["non_compliant_count"] == 1
        violations = result["violations"]
        assert len(violations) == 1
        assert violations[0]["violation_type"] == "missing_tag"
        assert violations[0]["tag_name"] == "CostCenter"

    @pytest.mark.asyncio
    async def test_invalid_value_violation(self, monitor, policy):
        resources = [{
            "id": "/sub/rg/vm3",
            "type": "Microsoft.Compute/virtualMachines",
            "name": "vm3",
            "tags": {
                "Environment": "development",  # Not in allowed values
                "Owner": "carol@contoso.com",
                "CostCenter": "CC-2001",
            },
        }]
        result = await monitor.evaluate_compliance(resources, policy)
        assert result["non_compliant_count"] == 1
        violations = [v for v in result["violations"] if v["violation_type"] == "invalid_value"]
        assert len(violations) == 1
        assert violations[0]["tag_name"] == "Environment"
        assert violations[0]["actual_value"] == "development"

    @pytest.mark.asyncio
    async def test_naming_violation(self, monitor, policy):
        resources = [{
            "id": "/sub/rg/vm4",
            "type": "Microsoft.Compute/virtualMachines",
            "name": "vm4",
            "tags": {
                "Environment": "prod",
                "Owner": "not-an-email",  # Doesn't match email pattern
                "CostCenter": "CC-1001",
            },
        }]
        result = await monitor.evaluate_compliance(resources, policy)
        assert result["non_compliant_count"] == 1
        violations = [v for v in result["violations"] if v["violation_type"] == "naming_violation"]
        assert len(violations) == 1
        assert violations[0]["tag_name"] == "Owner"
        assert violations[0]["actual_value"] == "not-an-email"

    @pytest.mark.asyncio
    async def test_multiple_violations_on_one_resource(self, monitor, policy):
        resources = [{
            "id": "/sub/rg/vm5",
            "type": "Microsoft.Compute/virtualMachines",
            "name": "vm5",
            "tags": {
                "Environment": "production",  # Invalid value
                "Owner": "bad-owner",  # Naming violation
                "CostCenter": "INVALID",  # Naming violation
            },
        }]
        result = await monitor.evaluate_compliance(resources, policy)
        assert result["non_compliant_count"] == 1
        assert len(result["violations"]) == 3  # invalid_value + 2 naming_violations

    @pytest.mark.asyncio
    async def test_no_tags_at_all(self, monitor, policy):
        resources = [{
            "id": "/sub/rg/vm6",
            "type": "Microsoft.Compute/virtualMachines",
            "name": "vm6",
            "tags": {},
        }]
        result = await monitor.evaluate_compliance(resources, policy)
        assert result["non_compliant_count"] == 1
        missing_violations = [v for v in result["violations"] if v["violation_type"] == "missing_tag"]
        assert len(missing_violations) == 3  # All 3 tags missing

    @pytest.mark.asyncio
    async def test_empty_resources_list(self, monitor, policy):
        result = await monitor.evaluate_compliance([], policy)
        assert result["total_resources"] == 0
        assert result["compliant_count"] == 0
        assert result["non_compliant_count"] == 0
        assert len(result["violations"]) == 0

    @pytest.mark.asyncio
    async def test_non_required_tag_not_flagged_when_missing(self, monitor):
        policy = [
            {"name": "Environment", "required": True, "allowed_values": ["dev", "prod"], "pattern": None},
            {"name": "Optional", "required": False, "allowed_values": None, "pattern": None},
        ]
        resources = [{
            "id": "/sub/rg/vm7",
            "type": "Microsoft.Compute/virtualMachines",
            "name": "vm7",
            "tags": {"Environment": "dev"},
        }]
        result = await monitor.evaluate_compliance(resources, policy)
        assert result["compliant_count"] == 1
        assert result["non_compliant_count"] == 0
        assert len(result["violations"]) == 0

    @pytest.mark.asyncio
    async def test_none_tags_treated_as_empty(self, monitor, policy):
        resources = [{
            "id": "/sub/rg/vm8",
            "type": "Microsoft.Compute/virtualMachines",
            "name": "vm8",
            "tags": None,
        }]
        result = await monitor.evaluate_compliance(resources, policy)
        assert result["non_compliant_count"] == 1
        missing_violations = [v for v in result["violations"] if v["violation_type"] == "missing_tag"]
        assert len(missing_violations) == 3


class TestTaggingMonitorScore:
    """Test the get_tagging_score method."""

    @pytest.fixture
    def monitor(self):
        from app.services.tagging_monitor import TaggingMonitor
        return TaggingMonitor()

    @pytest.mark.asyncio
    async def test_perfect_score(self, monitor):
        results = {
            "total_resources": 10,
            "compliant_count": 10,
            "non_compliant_count": 0,
        }
        score = await monitor.get_tagging_score(results)
        assert score["compliance_percentage"] == 100.0

    @pytest.mark.asyncio
    async def test_zero_score(self, monitor):
        results = {
            "total_resources": 10,
            "compliant_count": 0,
            "non_compliant_count": 10,
        }
        score = await monitor.get_tagging_score(results)
        assert score["compliance_percentage"] == 0.0

    @pytest.mark.asyncio
    async def test_partial_score(self, monitor):
        results = {
            "total_resources": 15,
            "compliant_count": 9,
            "non_compliant_count": 6,
        }
        score = await monitor.get_tagging_score(results)
        assert score["compliance_percentage"] == 60.0
        assert score["total_resources"] == 15
        assert score["compliant_count"] == 9
        assert score["non_compliant_count"] == 6

    @pytest.mark.asyncio
    async def test_empty_resources_score(self, monitor):
        results = {
            "total_resources": 0,
            "compliant_count": 0,
            "non_compliant_count": 0,
        }
        score = await monitor.get_tagging_score(results)
        assert score["compliance_percentage"] == 100.0

    @pytest.mark.asyncio
    async def test_score_rounding(self, monitor):
        results = {
            "total_resources": 3,
            "compliant_count": 1,
            "non_compliant_count": 2,
        }
        score = await monitor.get_tagging_score(results)
        assert score["compliance_percentage"] == 33.33


class TestTaggingMonitorScanFlow:
    """Test the full scan_tagging_compliance flow."""

    @pytest.fixture
    def monitor(self):
        from app.services.tagging_monitor import TaggingMonitor
        return TaggingMonitor()

    @pytest.mark.asyncio
    async def test_scan_without_db(self, monitor):
        """Scan should work without a database connection."""
        with patch.object(monitor, "get_resource_tags") as mock_get:
            mock_get.return_value = [
                {
                    "id": "/sub/rg/vm1",
                    "type": "Microsoft.Compute/virtualMachines",
                    "name": "vm1",
                    "tags": {
                        "Environment": "prod",
                        "Owner": "alice@contoso.com",
                        "CostCenter": "CC-1001",
                        "Application": "WebApp",
                        "ManagedBy": "terraform",
                    },
                },
                {
                    "id": "/sub/rg/vm2",
                    "type": "Microsoft.Compute/virtualMachines",
                    "name": "vm2",
                    "tags": {},  # No tags
                },
            ]
            result = await monitor.scan_tagging_compliance(
                project_id="proj1",
                subscription_id="sub1",
            )
            assert result["project_id"] == "proj1"
            assert result["status"] == "completed"
            assert result["total_resources"] == 2
            assert result["compliant_count"] == 1
            assert result["non_compliant_count"] == 1
            assert result["compliance_percentage"] == 50.0
            assert len(result["violations"]) > 0

    @pytest.mark.asyncio
    async def test_scan_publishes_sse_event(self, monitor):
        """Scan should publish a governance_score_updated SSE event."""
        with patch.object(monitor, "get_resource_tags") as mock_get, \
             patch("app.services.tagging_monitor.event_stream") as mock_stream:
            mock_get.return_value = [{
                "id": "/sub/rg/vm1",
                "type": "Microsoft.Compute/virtualMachines",
                "name": "vm1",
                "tags": {
                    "Environment": "prod",
                    "Owner": "alice@contoso.com",
                    "CostCenter": "CC-1001",
                    "Application": "WebApp",
                    "ManagedBy": "terraform",
                },
            }]
            mock_stream.publish = AsyncMock()

            await monitor.scan_tagging_compliance(
                project_id="proj1",
                subscription_id="sub1",
            )

            mock_stream.publish.assert_called_once()
            call_kwargs = mock_stream.publish.call_args
            assert call_kwargs[1]["event_type"] == "governance_score_updated"
            assert call_kwargs[1]["data"]["component"] == "tagging"

    @pytest.mark.asyncio
    async def test_get_resource_tags_dev_mode(self, monitor):
        """In dev mode, get_resource_tags returns mock data."""
        resources = await monitor.get_resource_tags("any-subscription")
        assert len(resources) >= 10
        assert all("id" in r for r in resources)
        assert all("type" in r for r in resources)
        assert all("tags" in r for r in resources)


class TestTaggingMonitorPeriodicTask:
    """Test the periodic task registration."""

    def test_tagging_task_registered(self):
        from app.services.task_scheduler import task_scheduler

        tasks = task_scheduler.registered_tasks
        assert "tagging_compliance" in tasks

    @pytest.mark.asyncio
    async def test_periodic_scan_no_project_id(self):
        from app.services.tagging_monitor import scan_tagging_periodic

        result = await scan_tagging_periodic()
        assert "skipping" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_periodic_scan_with_project_id(self):
        from app.services.tagging_monitor import scan_tagging_periodic

        result = await scan_tagging_periodic(project_id="proj-test", tenant_id=None)
        assert result["message"] == "Tagging compliance scan completed"
        assert "compliance_percentage" in result
        assert "total_resources" in result
        assert "non_compliant_count" in result


# ── API route tests (no-DB / mock mode) ─────────────────────────────────────


class TestPolicyRoutesNoDB:
    """Test policy endpoints when no DB is configured."""

    def test_create_policy(self):
        payload = {
            "project_id": PROJECT_ID,
            "name": "Test Policy",
            "required_tags": [
                {"name": "Environment", "required": True, "allowed_values": ["dev", "prod"]},
                {"name": "Owner", "required": True},
            ],
        }
        r = client.post("/api/governance/tagging/policies", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == PROJECT_ID
        assert data["name"] == "Test Policy"
        assert len(data["required_tags"]) == 2
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_policy_with_tenant(self):
        payload = {
            "project_id": PROJECT_ID,
            "tenant_id": "t1",
            "name": "Tenant Policy",
            "required_tags": [
                {"name": "Environment", "required": True},
            ],
        }
        r = client.post("/api/governance/tagging/policies", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["tenant_id"] == "t1"

    def test_create_policy_missing_fields(self):
        payload = {"project_id": PROJECT_ID}
        r = client.post("/api/governance/tagging/policies", json=payload)
        assert r.status_code == 422

    def test_list_policies_empty(self):
        r = client.get(
            "/api/governance/tagging/policies",
            params={"project_id": PROJECT_ID},
        )
        assert r.status_code == 200
        assert r.json() == []

    def test_list_policies_requires_project_id(self):
        r = client.get("/api/governance/tagging/policies")
        assert r.status_code == 422

    def test_get_policy_no_db(self):
        r = client.get("/api/governance/tagging/policies/non-existent")
        assert r.status_code == 404

    def test_update_policy_no_db(self):
        r = client.put(
            "/api/governance/tagging/policies/non-existent",
            json={"name": "Updated"},
        )
        assert r.status_code == 404

    def test_delete_policy_no_db(self):
        r = client.delete("/api/governance/tagging/policies/non-existent")
        assert r.status_code == 404


class TestScanRoutesNoDB:
    """Test scan endpoints when no DB is configured."""

    def test_trigger_scan(self):
        r = client.post(f"/api/governance/tagging/scan/{PROJECT_ID}")
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == PROJECT_ID
        assert data["status"] == "completed"
        assert "total_resources" in data
        assert "compliance_percentage" in data
        assert "compliant_count" in data
        assert "non_compliant_count" in data
        assert data["total_resources"] > 0

    def test_trigger_scan_with_subscription(self):
        r = client.post(
            f"/api/governance/tagging/scan/{PROJECT_ID}",
            params={"subscription_id": "sub-123"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "completed"


class TestResultsRoutesNoDB:
    """Test result endpoints when no DB is configured."""

    def test_list_results_empty(self):
        r = client.get("/api/governance/tagging/results")
        assert r.status_code == 200
        data = r.json()
        assert data["scan_results"] == []
        assert data["total"] == 0

    def test_list_results_with_filter(self):
        r = client.get(
            "/api/governance/tagging/results",
            params={"project_id": PROJECT_ID},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["scan_results"] == []
        assert data["total"] == 0

    def test_get_result_no_db(self):
        r = client.get("/api/governance/tagging/results/non-existent")
        assert r.status_code == 404


class TestSummaryRoutesNoDB:
    """Test summary endpoint when no DB is configured."""

    def test_get_summary_no_db(self):
        r = client.get(f"/api/governance/tagging/summary/{PROJECT_ID}")
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == PROJECT_ID
        assert data["compliance_percentage"] == 0.0
        assert data["total_resources"] == 0
        assert data["compliant_count"] == 0
        assert data["non_compliant_count"] == 0
        assert data["violations_by_type"]["missing_tag"] == 0
        assert data["violations_by_type"]["invalid_value"] == 0
        assert data["violations_by_type"]["naming_violation"] == 0
        assert data["worst_offending_resources"] == []
        assert data["latest_scan_at"] is None
        assert data["policy_name"] is None


# ── Router registration test ─────────────────────────────────────────────────


class TestRouterRegistration:
    """Verify the tagging router is registered in the app."""

    def test_tagging_routes_registered(self):
        route_paths = [r.path for r in app.routes]
        assert "/api/governance/tagging/policies" in route_paths
        assert "/api/governance/tagging/policies/{policy_id}" in route_paths
        assert "/api/governance/tagging/scan/{project_id}" in route_paths
        assert "/api/governance/tagging/results" in route_paths
        assert "/api/governance/tagging/results/{result_id}" in route_paths
        assert "/api/governance/tagging/summary/{project_id}" in route_paths


# ── Default policy seed data test ────────────────────────────────────────────


class TestDefaultTaggingPolicy:
    """Verify the default tagging policy configuration."""

    def test_default_required_tags(self):
        from app.services.tagging_monitor import DEFAULT_REQUIRED_TAGS

        tag_names = [t["name"] for t in DEFAULT_REQUIRED_TAGS]
        assert "Environment" in tag_names
        assert "Owner" in tag_names
        assert "CostCenter" in tag_names
        assert "Application" in tag_names
        assert "ManagedBy" in tag_names

    def test_environment_has_allowed_values(self):
        from app.services.tagging_monitor import DEFAULT_REQUIRED_TAGS

        env_tag = next(t for t in DEFAULT_REQUIRED_TAGS if t["name"] == "Environment")
        assert env_tag["allowed_values"] == ["dev", "staging", "prod"]
        assert env_tag["required"] is True

    def test_owner_has_email_pattern(self):
        from app.services.tagging_monitor import DEFAULT_REQUIRED_TAGS

        owner_tag = next(t for t in DEFAULT_REQUIRED_TAGS if t["name"] == "Owner")
        assert owner_tag["pattern"] is not None
        assert owner_tag["required"] is True

    def test_cost_center_has_pattern(self):
        from app.services.tagging_monitor import DEFAULT_REQUIRED_TAGS

        cc_tag = next(t for t in DEFAULT_REQUIRED_TAGS if t["name"] == "CostCenter")
        assert cc_tag["pattern"] is not None
        assert "CC-" in cc_tag["pattern"]

    def test_managed_by_has_allowed_values(self):
        from app.services.tagging_monitor import DEFAULT_REQUIRED_TAGS

        mb_tag = next(t for t in DEFAULT_REQUIRED_TAGS if t["name"] == "ManagedBy")
        assert "terraform" in mb_tag["allowed_values"]
        assert "bicep" in mb_tag["allowed_values"]


# ── Mock resource data test ──────────────────────────────────────────────────


class TestMockResources:
    """Verify mock data quality."""

    def test_mock_resources_count(self):
        from app.services.tagging_monitor import MOCK_RESOURCES

        assert len(MOCK_RESOURCES) >= 15

    def test_mock_resources_have_required_fields(self):
        from app.services.tagging_monitor import MOCK_RESOURCES

        for resource in MOCK_RESOURCES:
            assert "id" in resource
            assert "type" in resource
            assert "name" in resource
            assert "tags" in resource

    def test_mock_resources_include_compliant_and_non_compliant(self):
        """Ensure mock data has both compliant and non-compliant resources."""
        from app.services.tagging_monitor import DEFAULT_REQUIRED_TAGS, MOCK_RESOURCES

        has_compliant = False
        has_non_compliant = False

        for resource in MOCK_RESOURCES:
            tags = resource.get("tags", {})
            all_present = all(
                tags.get(rule["name"]) is not None
                for rule in DEFAULT_REQUIRED_TAGS
                if rule.get("required", True)
            )
            if all_present:
                has_compliant = True
            else:
                has_non_compliant = True

        assert has_compliant, "Mock data should include compliant resources"
        assert has_non_compliant, "Mock data should include non-compliant resources"
