"""Tests for the ProjectRBACService — role hierarchy and static helpers."""

import pytest

from app.services.project_rbac_service import ROLE_HIERARCHY, project_rbac


class TestRoleHierarchy:
    """Test the role hierarchy configuration."""

    def test_admin_is_highest(self):
        assert ROLE_HIERARCHY["admin"] == max(ROLE_HIERARCHY.values())

    def test_viewer_is_lowest(self):
        assert ROLE_HIERARCHY["viewer"] == min(ROLE_HIERARCHY.values())

    def test_hierarchy_ordering(self):
        assert ROLE_HIERARCHY["viewer"] < ROLE_HIERARCHY["contributor"]
        assert ROLE_HIERARCHY["contributor"] < ROLE_HIERARCHY["reviewer"]
        assert ROLE_HIERARCHY["reviewer"] < ROLE_HIERARCHY["editor"]
        assert ROLE_HIERARCHY["editor"] < ROLE_HIERARCHY["owner"]
        assert ROLE_HIERARCHY["owner"] < ROLE_HIERARCHY["admin"]

    def test_all_expected_roles_present(self):
        expected = {"viewer", "contributor", "reviewer", "editor", "owner", "admin"}
        assert set(ROLE_HIERARCHY.keys()) == expected


class TestRoleRank:
    """Test the _role_rank static method."""

    def test_known_role(self):
        assert project_rbac._role_rank("admin") == 5

    def test_unknown_role_returns_negative(self):
        assert project_rbac._role_rank("unknown") == -1


class TestRequireProjectRole:
    """Test require_project_role returns a callable dependency."""

    def test_returns_callable(self):
        dep = project_rbac.require_project_role("viewer")
        assert callable(dep)
