"""Tests for the CollaborationService — dev-mode (db=None) paths."""

import pytest

from app.services.collaboration_service import (
    ROLE_HIERARCHY,
    collaboration_service,
)


class TestRoleHierarchy:
    """Test role hierarchy configuration."""

    def test_owner_highest(self):
        assert ROLE_HIERARCHY["owner"] > ROLE_HIERARCHY["editor"]
        assert ROLE_HIERARCHY["owner"] > ROLE_HIERARCHY["viewer"]

    def test_editor_above_viewer(self):
        assert ROLE_HIERARCHY["editor"] > ROLE_HIERARCHY["viewer"]

    def test_all_roles_present(self):
        assert set(ROLE_HIERARCHY.keys()) == {"owner", "editor", "viewer"}


class TestAddMember:
    """Test add_member in dev mode."""

    @pytest.mark.asyncio
    async def test_add_viewer(self):
        result = await collaboration_service.add_member(
            db=None, project_id="proj-1", email="alice@example.com"
        )
        assert result["email"] == "alice@example.com"
        assert result["role"] == "viewer"
        assert result["display_name"] == "alice"

    @pytest.mark.asyncio
    async def test_add_editor(self):
        result = await collaboration_service.add_member(
            db=None, project_id="proj-1", email="bob@example.com", role="editor"
        )
        assert result["role"] == "editor"

    @pytest.mark.asyncio
    async def test_add_owner(self):
        result = await collaboration_service.add_member(
            db=None, project_id="proj-1", email="admin@example.com", role="owner"
        )
        assert result["role"] == "owner"

    @pytest.mark.asyncio
    async def test_invalid_role_raises(self):
        with pytest.raises(ValueError, match="Invalid role"):
            await collaboration_service.add_member(
                db=None, project_id="proj-1", email="x@x.com", role="superuser"
            )


class TestListMembers:
    """Test list_members in dev mode."""

    @pytest.mark.asyncio
    async def test_returns_empty_in_dev_mode(self):
        result = await collaboration_service.list_members(
            db=None, project_id="proj-1"
        )
        assert result["members"] == []
        assert result["total"] == 0


class TestRemoveMember:
    """Test remove_member in dev mode."""

    @pytest.mark.asyncio
    async def test_always_returns_true(self):
        result = await collaboration_service.remove_member(
            db=None, project_id="proj-1", user_id="user-1"
        )
        assert result is True


class TestCheckProjectAccess:
    """Test check_project_access in dev mode."""

    @pytest.mark.asyncio
    async def test_dev_mode_always_allows(self):
        result = await collaboration_service.check_project_access(
            db=None, project_id="proj-1", user_id="user-1", required_role="owner"
        )
        assert result is True


class TestAddComment:
    """Test add_comment in dev mode."""

    @pytest.mark.asyncio
    async def test_returns_comment_dict(self):
        result = await collaboration_service.add_comment(
            db=None,
            project_id="proj-1",
            user_id="user-1",
            content="Looks good!",
        )
        assert result["content"] == "Looks good!"
        assert result["user_id"] == "user-1"
        assert result["display_name"] == "Dev User"

    @pytest.mark.asyncio
    async def test_comment_with_component_ref(self):
        result = await collaboration_service.add_comment(
            db=None,
            project_id="proj-1",
            user_id="user-1",
            content="Check this",
            component_ref="network_topology",
        )
        assert result["component_ref"] == "network_topology"


class TestListComments:
    """Test list_comments in dev mode."""

    @pytest.mark.asyncio
    async def test_returns_empty_in_dev_mode(self):
        result = await collaboration_service.list_comments(
            db=None, project_id="proj-1"
        )
        assert result["comments"] == []
        assert result["total"] == 0
