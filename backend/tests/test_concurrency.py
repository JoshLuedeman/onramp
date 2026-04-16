"""Tests for optimistic concurrency control and enhanced diff.

Covers:
- concurrency.check_version / increment_version / ConflictError
- version_service.diff_versions (basic)
- version_service.enhanced_diff_versions (property-level, categories)
- Schema validation (ConflictResponse, EnhancedVersionDiffResponse)
- Architecture route concurrency enforcement
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.concurrency import ConflictError, check_version, increment_version
from app.schemas.version import (
    CategoryGroup,
    ComponentChange,
    ConflictResponse,
    EnhancedComponentChange,
    EnhancedVersionDiffResponse,
    PropertyDiff,
    VersionDiffResponse,
)
from app.services.version_service import (
    _build_readable_summary,
    _compute_property_diffs,
    _describe_modification,
    _extract_components,
    _get_category,
    diff_versions,
    enhanced_diff_versions,
)


# ─── Fixtures ────────────────────────────────────────────────────────────

def _make_arch_json(**overrides: Any) -> str:
    """Build a minimal architecture JSON string."""
    data: dict[str, Any] = {
        "management_groups": [{"name": "root"}],
        "subscriptions": [{"name": "prod"}],
        "network_topology": {"hub": "10.0.0.0/16"},
        "policies": {"enforce_tls": True},
    }
    data.update(overrides)
    return json.dumps(data)


class FakeModel:
    """Minimal stand-in for an SQLAlchemy model with id + version."""
    __name__ = "FakeModel"
    id = "arch-1"
    version = 3
    architecture_data = {"management_groups": []}


# ─── ConflictError ───────────────────────────────────────────────────────

class TestConflictError:
    def test_status_code_is_409(self):
        err = ConflictError(
            current_version=3, submitted_version=1,
        )
        assert err.status_code == 409

    def test_detail_contains_versions(self):
        err = ConflictError(
            current_version=5, submitted_version=2,
        )
        assert err.detail["current_version"] == 5
        assert err.detail["submitted_version"] == 2

    def test_detail_contains_default_message(self):
        err = ConflictError(
            current_version=3, submitted_version=1,
        )
        assert "version 1" in err.detail["message"]
        assert "version is 3" in err.detail["message"]

    def test_custom_message(self):
        err = ConflictError(
            current_version=3, submitted_version=1,
            message="Custom conflict msg",
        )
        assert err.detail["message"] == "Custom conflict msg"

    def test_current_data_default_empty(self):
        err = ConflictError(
            current_version=3, submitted_version=1,
        )
        assert err.detail["current_data"] == {}

    def test_current_data_populated(self):
        data = {"policies": {"enforce_tls": True}}
        err = ConflictError(
            current_version=3, submitted_version=1,
            current_data=data,
        )
        assert err.detail["current_data"] == data

    def test_is_http_exception(self):
        err = ConflictError(
            current_version=1, submitted_version=0,
        )
        assert isinstance(err, HTTPException)


# ─── check_version ───────────────────────────────────────────────────────

class TestCheckVersion:
    @pytest.fixture()
    def mock_db(self):
        db = AsyncMock()
        return db

    @pytest.fixture()
    def mock_model(self):
        model = MagicMock()
        model.__name__ = "Architecture"
        model.id = "arch-1"
        return model

    async def test_raises_404_when_not_found(
        self, mock_db, mock_model,
    ):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(HTTPException) as exc_info:
            await check_version(mock_db, mock_model, "x", 1)
        assert exc_info.value.status_code == 404

    async def test_raises_409_when_versions_mismatch(
        self, mock_db, mock_model,
    ):
        instance = MagicMock(version=5, architecture_data={"a": 1})
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = instance
        mock_db.execute.return_value = result_mock

        with pytest.raises(ConflictError) as exc_info:
            await check_version(mock_db, mock_model, "arch-1", 2)
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail["current_version"] == 5

    async def test_returns_instance_when_versions_match(
        self, mock_db, mock_model,
    ):
        instance = MagicMock(version=3)
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = instance
        mock_db.execute.return_value = result_mock

        result = await check_version(
            mock_db, mock_model, "arch-1", 3,
        )
        assert result is instance

    async def test_conflict_includes_current_data(
        self, mock_db, mock_model,
    ):
        data = {"policies": {"tls": True}}
        instance = MagicMock(version=4, architecture_data=data)
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = instance
        mock_db.execute.return_value = result_mock

        with pytest.raises(ConflictError) as exc_info:
            await check_version(mock_db, mock_model, "arch-1", 1)
        assert exc_info.value.detail["current_data"] == data

    async def test_conflict_with_no_architecture_data(
        self, mock_db, mock_model,
    ):
        instance = MagicMock(version=4, spec=["version", "id"])
        del instance.architecture_data
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = instance
        mock_db.execute.return_value = result_mock

        with pytest.raises(ConflictError) as exc_info:
            await check_version(mock_db, mock_model, "arch-1", 1)
        assert exc_info.value.detail["current_data"] == {}


# ─── increment_version ──────────────────────────────────────────────────

class TestIncrementVersion:
    def test_increments_from_current(self):
        obj = MagicMock(version=5)
        result = increment_version(obj)
        assert result == 6
        assert obj.version == 6

    def test_increments_from_zero(self):
        obj = MagicMock(version=0)
        result = increment_version(obj)
        assert result == 1

    def test_increments_from_1(self):
        obj = MagicMock(version=1)
        result = increment_version(obj)
        assert result == 2

    def test_handles_missing_version_attr(self):
        """Falls back to 0 when version attr doesn't exist."""
        obj = MagicMock(spec=[])
        result = increment_version(obj)
        assert result == 1

    def test_multiple_increments(self):
        obj = MagicMock(version=1)
        increment_version(obj)
        increment_version(obj)
        assert obj.version == 3


# ─── Schema validation ──────────────────────────────────────────────────

class TestConflictResponseSchema:
    def test_valid_schema(self):
        resp = ConflictResponse(
            current_version=5,
            submitted_version=3,
            current_data={"policies": {}},
            message="Version conflict",
        )
        assert resp.current_version == 5
        assert resp.submitted_version == 3

    def test_empty_current_data(self):
        resp = ConflictResponse(
            current_version=1,
            submitted_version=0,
            message="Conflict",
        )
        assert resp.current_data == {}

    def test_serialization(self):
        resp = ConflictResponse(
            current_version=5,
            submitted_version=3,
            message="Conflict",
        )
        data = resp.model_dump()
        assert "current_version" in data
        assert "submitted_version" in data
        assert "message" in data

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            ConflictResponse(
                current_version=1,
                submitted_version=0,
            )  # missing message


class TestPropertyDiffSchema:
    def test_valid(self):
        pd = PropertyDiff(
            property_name="hub",
            old_value="10.0.0.0/16",
            new_value="10.1.0.0/16",
            change_type="modified",
        )
        assert pd.property_name == "hub"

    def test_default_change_type(self):
        pd = PropertyDiff(property_name="x")
        assert pd.change_type == "modified"


class TestEnhancedComponentChangeSchema:
    def test_with_property_diffs(self):
        ecc = EnhancedComponentChange(
            name="network_topology",
            detail="Modified",
            category="networking",
            property_diffs=[
                PropertyDiff(
                    property_name="hub",
                    old_value="a",
                    new_value="b",
                ),
            ],
        )
        assert len(ecc.property_diffs) == 1

    def test_defaults(self):
        ecc = EnhancedComponentChange(name="test")
        assert ecc.category == "general"
        assert ecc.property_diffs == []


class TestCategoryGroupSchema:
    def test_total_changes_property(self):
        cg = CategoryGroup(
            category="networking",
            display_name="Networking",
            added=[
                EnhancedComponentChange(name="a"),
                EnhancedComponentChange(name="b"),
            ],
            removed=[EnhancedComponentChange(name="c")],
        )
        assert cg.total_changes == 3


class TestEnhancedVersionDiffResponseSchema:
    def test_valid(self):
        resp = EnhancedVersionDiffResponse(
            from_version=1,
            to_version=2,
            added_components=[],
            removed_components=[],
            modified_components=[],
            summary="No changes",
            change_counts={"added": 0, "removed": 0, "total": 0},
            category_groups=[],
        )
        assert resp.from_version == 1

    def test_defaults(self):
        resp = EnhancedVersionDiffResponse(
            from_version=1,
            to_version=2,
            added_components=[],
            removed_components=[],
            modified_components=[],
            summary="No changes",
        )
        assert resp.change_counts == {}
        assert resp.category_groups == []


# ─── _extract_components ─────────────────────────────────────────────────

class TestExtractComponents:
    def test_extracts_known_keys(self):
        data = {
            "management_groups": [1],
            "subscriptions": [2],
            "network_topology": {},
            "policies": {},
            "compliance_frameworks": [],
        }
        result = _extract_components(data)
        assert set(result.keys()) == {
            "management_groups",
            "subscriptions",
            "network_topology",
            "policies",
            "compliance_frameworks",
        }

    def test_extracts_unknown_non_metadata(self):
        data = {"custom_field": "value", "version": 1}
        result = _extract_components(data)
        assert "custom_field" in result
        assert "version" not in result

    def test_skips_metadata(self):
        data = {
            "id": "x",
            "project_id": "y",
            "status": "draft",
            "ai_reasoning": "test",
        }
        result = _extract_components(data)
        assert len(result) == 0

    def test_empty_data(self):
        result = _extract_components({})
        assert result == {}


# ─── _compute_property_diffs ─────────────────────────────────────────────

class TestComputePropertyDiffs:
    def test_dict_added_key(self):
        diffs = _compute_property_diffs(
            {"a": 1}, {"a": 1, "b": 2},
        )
        added = [d for d in diffs if d.change_type == "added"]
        assert len(added) == 1
        assert added[0].property_name == "b"

    def test_dict_removed_key(self):
        diffs = _compute_property_diffs(
            {"a": 1, "b": 2}, {"a": 1},
        )
        removed = [d for d in diffs if d.change_type == "removed"]
        assert len(removed) == 1
        assert removed[0].property_name == "b"

    def test_dict_modified_key(self):
        diffs = _compute_property_diffs(
            {"a": 1}, {"a": 2},
        )
        modified = [d for d in diffs if d.change_type == "modified"]
        assert len(modified) == 1
        assert modified[0].old_value == 1
        assert modified[0].new_value == 2

    def test_list_added_element(self):
        diffs = _compute_property_diffs([1], [1, 2])
        added = [d for d in diffs if d.change_type == "added"]
        assert len(added) == 1
        assert added[0].property_name == "[1]"

    def test_list_removed_element(self):
        diffs = _compute_property_diffs([1, 2], [1])
        removed = [d for d in diffs if d.change_type == "removed"]
        assert len(removed) == 1
        assert removed[0].property_name == "[1]"

    def test_list_modified_element(self):
        diffs = _compute_property_diffs([1, 2], [1, 3])
        modified = [d for d in diffs if d.change_type == "modified"]
        assert len(modified) == 1
        assert modified[0].new_value == 3

    def test_scalar_change(self):
        diffs = _compute_property_diffs("old", "new")
        assert len(diffs) == 1
        assert diffs[0].property_name == "value"
        assert diffs[0].old_value == "old"
        assert diffs[0].new_value == "new"

    def test_empty_dicts(self):
        diffs = _compute_property_diffs({}, {})
        assert len(diffs) == 0

    def test_empty_lists(self):
        diffs = _compute_property_diffs([], [])
        assert len(diffs) == 0


# ─── _describe_modification ─────────────────────────────────────────────

class TestDescribeModification:
    def test_list_items_added(self):
        result = _describe_modification("subs", [1], [1, 2])
        assert "1 item(s) added" in result
        assert "total 2" in result

    def test_list_items_removed(self):
        result = _describe_modification("subs", [1, 2, 3], [1])
        assert "2 item(s) removed" in result

    def test_list_items_modified(self):
        result = _describe_modification("subs", [1, 2], [3, 4])
        assert "items modified" in result
        assert "count unchanged" in result

    def test_dict_keys_added(self):
        result = _describe_modification("net", {"a": 1}, {"a": 1, "b": 2})
        assert "1 key(s) added" in result

    def test_dict_keys_removed(self):
        result = _describe_modification(
            "net", {"a": 1, "b": 2}, {"a": 1},
        )
        assert "1 key(s) removed" in result

    def test_dict_keys_changed(self):
        result = _describe_modification("net", {"a": 1}, {"a": 2})
        assert "1 key(s) changed" in result

    def test_dict_content_changed(self):
        """When keys are identical but content differs subtly."""
        result = _describe_modification(
            "net", {"a": {"nested": 1}}, {"a": {"nested": 2}},
        )
        assert "changed" in result

    def test_scalar_value_changed(self):
        result = _describe_modification("x", "old", "new")
        assert "value changed" in result


# ─── _get_category ───────────────────────────────────────────────────────

class TestGetCategory:
    def test_known_networking(self):
        cat, name = _get_category("network_topology")
        assert cat == "networking"

    def test_known_security(self):
        cat, name = _get_category("policies")
        assert cat == "security"

    def test_unknown_defaults_general(self):
        cat, name = _get_category("unknown_thing")
        assert cat == "general"
        assert name == "General"


# ─── diff_versions (basic) ──────────────────────────────────────────────

class TestDiffVersions:
    def test_no_changes(self):
        j = _make_arch_json()
        result = diff_versions(j, j)
        assert result.summary == "No changes detected"
        assert len(result.added_components) == 0

    def test_added_component(self):
        a = json.dumps({"policies": {}})
        b = json.dumps({"policies": {}, "compliance_frameworks": []})
        result = diff_versions(a, b)
        assert len(result.added_components) == 1
        assert result.added_components[0].name == "compliance_frameworks"

    def test_removed_component(self):
        a = json.dumps({"policies": {}, "subscriptions": []})
        b = json.dumps({"policies": {}})
        result = diff_versions(a, b)
        assert len(result.removed_components) == 1
        assert result.removed_components[0].name == "subscriptions"

    def test_modified_component(self):
        a = json.dumps({"policies": {"tls": True}})
        b = json.dumps({"policies": {"tls": False}})
        result = diff_versions(a, b)
        assert len(result.modified_components) == 1

    def test_empty_json_from(self):
        b = json.dumps({"policies": {}})
        result = diff_versions("", b)
        assert len(result.added_components) == 1

    def test_empty_json_to(self):
        a = json.dumps({"policies": {}})
        result = diff_versions(a, "")
        assert len(result.removed_components) == 1

    def test_summary_includes_counts(self):
        a = json.dumps({"policies": {"a": 1}})
        b = json.dumps({"policies": {"a": 2}, "subscriptions": []})
        result = diff_versions(a, b)
        assert "added" in result.summary
        assert "modified" in result.summary

    def test_from_and_to_version_default_zero(self):
        result = diff_versions("{}", "{}")
        assert result.from_version == 0
        assert result.to_version == 0


# ─── enhanced_diff_versions ─────────────────────────────────────────────

class TestEnhancedDiffVersions:
    def test_no_changes(self):
        j = _make_arch_json()
        result = enhanced_diff_versions(j, j)
        assert result.change_counts["total"] == 0
        assert result.summary == "No changes detected"

    def test_added_has_category(self):
        a = json.dumps({})
        b = json.dumps({"policies": {"enforce": True}})
        result = enhanced_diff_versions(a, b)
        assert len(result.added_components) == 1
        assert result.added_components[0].category == "security"

    def test_removed_has_category(self):
        a = json.dumps({"network_topology": {"hub": "10.0.0.0/16"}})
        b = json.dumps({})
        result = enhanced_diff_versions(a, b)
        assert result.removed_components[0].category == "networking"

    def test_modified_has_property_diffs(self):
        a = json.dumps({"policies": {"tls": True}})
        b = json.dumps({"policies": {"tls": False, "mfa": True}})
        result = enhanced_diff_versions(a, b)
        assert len(result.modified_components) == 1
        mc = result.modified_components[0]
        assert len(mc.property_diffs) >= 1

    def test_category_groups_created(self):
        a = json.dumps({"policies": {}, "network_topology": {}})
        b = json.dumps({
            "policies": {"new": True},
            "network_topology": {"changed": True},
        })
        result = enhanced_diff_versions(a, b)
        assert len(result.category_groups) >= 1

    def test_change_counts_correct(self):
        a = json.dumps({"policies": {}})
        b = json.dumps({"policies": {"new": True}, "subscriptions": []})
        result = enhanced_diff_versions(a, b)
        counts = result.change_counts
        assert counts["added"] == 1
        assert counts["modified"] == 1
        assert counts["total"] == 2

    def test_category_group_has_display_name(self):
        a = json.dumps({})
        b = json.dumps({"policies": {}})
        result = enhanced_diff_versions(a, b)
        groups = result.category_groups
        assert len(groups) == 1
        assert groups[0].display_name == "Security & Compliance"

    def test_summary_includes_names(self):
        a = json.dumps({})
        b = json.dumps({
            "policies": {},
            "subscriptions": [],
            "compliance_frameworks": [],
        })
        result = enhanced_diff_versions(a, b)
        assert "policies" in result.summary.lower() or "Added 3" in result.summary

    def test_multiple_categories(self):
        a = json.dumps({})
        b = json.dumps({
            "policies": {},
            "network_topology": {},
            "identity": {},
        })
        result = enhanced_diff_versions(a, b)
        cats = {g.category for g in result.category_groups}
        assert len(cats) >= 2


# ─── _build_readable_summary ────────────────────────────────────────────

class TestBuildReadableSummary:
    def test_empty(self):
        result = _build_readable_summary([], [], [])
        assert result == "No changes detected"

    def test_added_only(self):
        added = [EnhancedComponentChange(name="policies")]
        result = _build_readable_summary(added, [], [])
        assert "Added 1" in result
        assert "policies" in result

    def test_truncates_long_lists(self):
        added = [
            EnhancedComponentChange(name=f"c{i}") for i in range(5)
        ]
        result = _build_readable_summary(added, [], [])
        assert "+2 more" in result

    def test_all_types(self):
        added = [EnhancedComponentChange(name="a")]
        removed = [EnhancedComponentChange(name="b")]
        modified = [EnhancedComponentChange(name="c")]
        result = _build_readable_summary(added, removed, modified)
        assert "Added" in result
        assert "Removed" in result
        assert "Modified" in result


# ─── Concurrency on multiple updates ────────────────────────────────────

class TestConcurrentUpdates:
    """Simulate two concurrent updates — only first succeeds."""

    async def test_first_update_succeeds(self):
        db = AsyncMock()
        model = MagicMock()
        model.__name__ = "Architecture"
        instance = MagicMock(version=1, architecture_data={})
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = instance
        db.execute.return_value = result_mock

        # First update matches version 1
        result = await check_version(db, model, "arch-1", 1)
        assert result is instance

    async def test_second_update_fails_after_increment(self):
        db = AsyncMock()
        model = MagicMock()
        model.__name__ = "Architecture"

        # After first update, version is now 2
        instance = MagicMock(version=2, architecture_data={})
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = instance
        db.execute.return_value = result_mock

        # Second update still submits version 1 — should fail
        with pytest.raises(ConflictError):
            await check_version(db, model, "arch-1", 1)

    async def test_sequential_updates_with_increments(self):
        db = AsyncMock()
        model = MagicMock()
        model.__name__ = "Architecture"

        # Version starts at 1
        instance = MagicMock(version=1, architecture_data={})
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = instance
        db.execute.return_value = result_mock

        await check_version(db, model, "arch-1", 1)
        new_ver = increment_version(instance)
        assert new_ver == 2

        # Update mock to reflect v2
        instance2 = MagicMock(version=2, architecture_data={})
        result_mock2 = MagicMock()
        result_mock2.scalars.return_value.first.return_value = instance2
        db.execute.return_value = result_mock2

        await check_version(db, model, "arch-1", 2)
        new_ver2 = increment_version(instance2)
        assert new_ver2 == 3


# ─── VersionDiffResponse schema ─────────────────────────────────────────

class TestVersionDiffResponseSchema:
    def test_basic_creation(self):
        resp = VersionDiffResponse(
            from_version=1,
            to_version=2,
            added_components=[ComponentChange(name="a")],
            removed_components=[],
            modified_components=[],
            summary="1 added",
        )
        assert resp.from_version == 1
        assert len(resp.added_components) == 1

    def test_serialization_roundtrip(self):
        resp = VersionDiffResponse(
            from_version=1,
            to_version=2,
            added_components=[],
            removed_components=[],
            modified_components=[],
            summary="None",
        )
        data = resp.model_dump()
        resp2 = VersionDiffResponse(**data)
        assert resp2 == resp


class TestComponentChangeSchema:
    def test_default_detail(self):
        cc = ComponentChange(name="test")
        assert cc.detail == ""

    def test_with_detail(self):
        cc = ComponentChange(name="test", detail="Changed")
        assert cc.detail == "Changed"
