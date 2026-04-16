"""Tests for collaboration API routes, schemas, service, and models."""

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.main import app

client = TestClient(app)

# ── Member endpoint tests (sync) ────────────────────────────────────────


def test_list_members_empty():
    """GET /members returns empty list when DB is not configured."""
    r = client.get("/api/projects/test-proj/members")
    assert r.status_code == 200
    data = r.json()
    assert "members" in data
    assert data["members"] == []
    assert data["total"] == 0


def test_add_member_returns_mock():
    """POST /members returns mock member in dev mode."""
    r = client.post(
        "/api/projects/test-proj/members",
        json={"email": "alice@example.com", "role": "editor"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "alice@example.com"
    assert data["role"] == "editor"
    assert "id" in data
    assert "user_id" in data
    assert "invited_at" in data


def test_add_member_default_role():
    """POST /members with no role defaults to viewer."""
    r = client.post(
        "/api/projects/test-proj/members",
        json={"email": "bob@example.com"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["role"] == "viewer"


def test_add_member_invalid_role():
    """POST /members with invalid role returns 422."""
    r = client.post(
        "/api/projects/test-proj/members",
        json={"email": "bad@example.com", "role": "superadmin"},
    )
    assert r.status_code == 422


def test_add_member_missing_email():
    """POST /members without email returns 422."""
    r = client.post(
        "/api/projects/test-proj/members",
        json={"role": "viewer"},
    )
    assert r.status_code == 422


def test_add_member_owner_role():
    """POST /members with owner role succeeds."""
    r = client.post(
        "/api/projects/test-proj/members",
        json={"email": "owner@example.com", "role": "owner"},
    )
    assert r.status_code == 200
    assert r.json()["role"] == "owner"


def test_add_member_viewer_role():
    """POST /members with viewer role succeeds."""
    r = client.post(
        "/api/projects/test-proj/members",
        json={"email": "viewer@example.com", "role": "viewer"},
    )
    assert r.status_code == 200
    assert r.json()["role"] == "viewer"


def test_remove_member_mock():
    """DELETE /members/{user_id} returns success in dev mode."""
    r = client.delete("/api/projects/test-proj/members/some-user-id")
    assert r.status_code == 200
    data = r.json()
    assert data["removed"] is True
    assert data["user_id"] == "some-user-id"


def test_remove_member_different_ids():
    """DELETE /members returns the correct user_id."""
    r = client.delete("/api/projects/proj-1/members/user-abc")
    assert r.status_code == 200
    assert r.json()["user_id"] == "user-abc"


# ── Comment endpoint tests (sync) ───────────────────────────────────────


def test_list_comments_empty():
    """GET /comments returns empty list when DB is not configured."""
    r = client.get("/api/projects/test-proj/comments")
    assert r.status_code == 200
    data = r.json()
    assert data["comments"] == []
    assert data["total"] == 0


def test_add_comment():
    """POST /comments creates a comment in dev mode."""
    r = client.post(
        "/api/projects/test-proj/comments",
        json={"content": "Looks great!", "component_ref": "vnet-hub"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["content"] == "Looks great!"
    assert data["component_ref"] == "vnet-hub"
    assert "id" in data
    assert "user_id" in data
    assert "created_at" in data


def test_add_comment_without_component_ref():
    """POST /comments without component_ref succeeds."""
    r = client.post(
        "/api/projects/test-proj/comments",
        json={"content": "General comment"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["content"] == "General comment"
    assert data["component_ref"] is None


def test_add_comment_empty_content():
    """POST /comments with empty content returns 422."""
    r = client.post(
        "/api/projects/test-proj/comments",
        json={"content": ""},
    )
    assert r.status_code == 422


def test_add_comment_missing_content():
    """POST /comments without content returns 422."""
    r = client.post(
        "/api/projects/test-proj/comments",
        json={},
    )
    assert r.status_code == 422


def test_add_comment_long_content():
    """POST /comments with content at max length succeeds."""
    content = "A" * 5000
    r = client.post(
        "/api/projects/test-proj/comments",
        json={"content": content},
    )
    assert r.status_code == 200
    assert r.json()["content"] == content


def test_add_comment_too_long_content():
    """POST /comments with content exceeding max returns 422."""
    content = "A" * 5001
    r = client.post(
        "/api/projects/test-proj/comments",
        json={"content": content},
    )
    assert r.status_code == 422


def test_list_comments_with_component_ref_filter():
    """GET /comments with component_ref filter returns 200."""
    r = client.get(
        "/api/projects/test-proj/comments?component_ref=firewall"
    )
    assert r.status_code == 200
    data = r.json()
    assert "comments" in data
    assert "total" in data


def test_add_comment_has_display_name():
    """POST /comments response includes display_name field."""
    r = client.post(
        "/api/projects/proj-1/comments",
        json={"content": "Test display name"},
    )
    assert r.status_code == 200
    assert "display_name" in r.json()


# ── Activity feed endpoint tests (sync) ─────────────────────────────────


def test_activity_feed_empty():
    """GET /activity returns empty list when DB is not configured."""
    r = client.get("/api/projects/test-proj/activity")
    assert r.status_code == 200
    data = r.json()
    assert "activities" in data
    assert data["activities"] == []


def test_activity_feed_different_projects():
    """GET /activity returns 200 for different project IDs."""
    for pid in ["proj-a", "proj-b", "proj-c"]:
        r = client.get(f"/api/projects/{pid}/activity")
        assert r.status_code == 200
        assert "activities" in r.json()


# ── Schema validation tests ─────────────────────────────────────────────


def test_schema_project_member_create_valid():
    """ProjectMemberCreate accepts valid data."""
    from app.schemas.collaboration import ProjectMemberCreate

    m = ProjectMemberCreate(email="test@example.com", role="editor")
    assert m.email == "test@example.com"
    assert m.role == "editor"


def test_schema_project_member_create_default_role():
    """ProjectMemberCreate defaults role to viewer."""
    from app.schemas.collaboration import ProjectMemberCreate

    m = ProjectMemberCreate(email="test@example.com")
    assert m.role == "viewer"


def test_schema_project_member_create_invalid_role():
    """ProjectMemberCreate rejects invalid role."""
    from pydantic import ValidationError

    from app.schemas.collaboration import ProjectMemberCreate

    with pytest.raises(ValidationError):
        ProjectMemberCreate(email="test@example.com", role="superadmin")


def test_schema_comment_create_valid():
    """CommentCreate accepts valid data."""
    from app.schemas.collaboration import CommentCreate

    c = CommentCreate(content="Hello", component_ref="subnet-1")
    assert c.content == "Hello"
    assert c.component_ref == "subnet-1"


def test_schema_comment_create_no_component():
    """CommentCreate with no component_ref defaults to None."""
    from app.schemas.collaboration import CommentCreate

    c = CommentCreate(content="Hello")
    assert c.component_ref is None


def test_schema_comment_create_empty_content():
    """CommentCreate rejects empty content."""
    from pydantic import ValidationError

    from app.schemas.collaboration import CommentCreate

    with pytest.raises(ValidationError):
        CommentCreate(content="")


def test_schema_comment_create_too_long():
    """CommentCreate rejects content over 5000 chars."""
    from pydantic import ValidationError

    from app.schemas.collaboration import CommentCreate

    with pytest.raises(ValidationError):
        CommentCreate(content="X" * 5001)


def test_schema_member_response():
    """ProjectMemberResponse can be constructed."""
    from datetime import datetime, timezone

    from app.schemas.collaboration import ProjectMemberResponse

    now = datetime.now(timezone.utc)
    resp = ProjectMemberResponse(
        id="abc",
        user_id="user-1",
        email="a@b.com",
        display_name="Alice",
        role="editor",
        invited_at=now,
    )
    assert resp.id == "abc"
    assert resp.accepted_at is None


def test_schema_comment_response():
    """CommentResponse can be constructed."""
    from datetime import datetime, timezone

    from app.schemas.collaboration import CommentResponse

    now = datetime.now(timezone.utc)
    resp = CommentResponse(
        id="c-1",
        content="Nice",
        user_id="u-1",
        created_at=now,
    )
    assert resp.component_ref is None
    assert resp.display_name == ""


def test_schema_member_list_response():
    """ProjectMemberListResponse with members list."""
    from app.schemas.collaboration import (
        ProjectMemberListResponse,
    )

    resp = ProjectMemberListResponse(members=[], total=0)
    assert resp.total == 0
    assert resp.members == []


def test_schema_comment_list_response():
    """CommentListResponse with comments list."""
    from app.schemas.collaboration import CommentListResponse

    resp = CommentListResponse(comments=[], total=0)
    assert resp.total == 0


def test_schema_activity_entry():
    """ActivityEntry can be constructed."""
    from datetime import datetime, timezone

    from app.schemas.collaboration import ActivityEntry

    entry = ActivityEntry(
        type="comment_added",
        user_id="u-1",
        description="Alice commented",
        timestamp=datetime.now(timezone.utc),
    )
    assert entry.type == "comment_added"


def test_schema_activity_feed_response():
    """ActivityFeedResponse with activities."""
    from app.schemas.collaboration import ActivityFeedResponse

    resp = ActivityFeedResponse(activities=[])
    assert resp.activities == []


# ── Service unit tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_service_add_member_mock():
    """Service add_member with db=None returns mock data."""
    from app.services.collaboration_service import (
        collaboration_service,
    )

    result = await collaboration_service.add_member(
        db=None,
        project_id="proj-1",
        email="test@example.com",
        role="editor",
    )
    assert result["email"] == "test@example.com"
    assert result["role"] == "editor"
    assert result["accepted_at"] is None


@pytest.mark.asyncio
async def test_service_add_member_invalid_role():
    """Service add_member raises ValueError for invalid role."""
    from app.services.collaboration_service import (
        collaboration_service,
    )

    with pytest.raises(ValueError, match="Invalid role"):
        await collaboration_service.add_member(
            db=None,
            project_id="proj-1",
            email="test@example.com",
            role="superadmin",
        )


@pytest.mark.asyncio
async def test_service_list_members_mock():
    """Service list_members with db=None returns empty."""
    from app.services.collaboration_service import (
        collaboration_service,
    )

    result = await collaboration_service.list_members(
        db=None, project_id="proj-1"
    )
    assert result["members"] == []
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_service_remove_member_mock():
    """Service remove_member with db=None returns True."""
    from app.services.collaboration_service import (
        collaboration_service,
    )

    result = await collaboration_service.remove_member(
        db=None, project_id="proj-1", user_id="u-1"
    )
    assert result is True


@pytest.mark.asyncio
async def test_service_check_access_mock():
    """Service check_project_access with db=None allows all."""
    from app.services.collaboration_service import (
        collaboration_service,
    )

    result = await collaboration_service.check_project_access(
        db=None,
        project_id="proj-1",
        user_id="u-1",
        required_role="owner",
    )
    assert result is True


@pytest.mark.asyncio
async def test_service_add_comment_mock():
    """Service add_comment with db=None returns mock."""
    from app.services.collaboration_service import (
        collaboration_service,
    )

    result = await collaboration_service.add_comment(
        db=None,
        project_id="proj-1",
        user_id="u-1",
        content="Great design!",
        component_ref="firewall",
    )
    assert result["content"] == "Great design!"
    assert result["component_ref"] == "firewall"
    assert result["display_name"] == "Dev User"


@pytest.mark.asyncio
async def test_service_add_comment_no_ref():
    """Service add_comment without component_ref."""
    from app.services.collaboration_service import (
        collaboration_service,
    )

    result = await collaboration_service.add_comment(
        db=None,
        project_id="proj-1",
        user_id="u-1",
        content="Hello",
    )
    assert result["component_ref"] is None


@pytest.mark.asyncio
async def test_service_list_comments_mock():
    """Service list_comments with db=None returns empty."""
    from app.services.collaboration_service import (
        collaboration_service,
    )

    result = await collaboration_service.list_comments(
        db=None, project_id="proj-1"
    )
    assert result["comments"] == []
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_service_list_comments_with_filter():
    """Service list_comments with component_ref filter."""
    from app.services.collaboration_service import (
        collaboration_service,
    )

    result = await collaboration_service.list_comments(
        db=None, project_id="proj-1", component_ref="vnet"
    )
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_service_activity_feed_mock():
    """Service get_activity_feed with db=None returns empty."""
    from app.services.collaboration_service import (
        collaboration_service,
    )

    result = await collaboration_service.get_activity_feed(
        db=None, project_id="proj-1"
    )
    assert result["activities"] == []


@pytest.mark.asyncio
async def test_service_activity_feed_custom_limit():
    """Service get_activity_feed respects custom limit."""
    from app.services.collaboration_service import (
        collaboration_service,
    )

    result = await collaboration_service.get_activity_feed(
        db=None, project_id="proj-1", limit=10
    )
    assert result["activities"] == []


# ── Role hierarchy tests ────────────────────────────────────────────────


def test_role_hierarchy_values():
    """ROLE_HIERARCHY has correct ordering."""
    from app.services.collaboration_service import ROLE_HIERARCHY

    assert ROLE_HIERARCHY["owner"] > ROLE_HIERARCHY["editor"]
    assert ROLE_HIERARCHY["editor"] > ROLE_HIERARCHY["viewer"]
    assert ROLE_HIERARCHY["owner"] == 3
    assert ROLE_HIERARCHY["editor"] == 2
    assert ROLE_HIERARCHY["viewer"] == 1


def test_role_hierarchy_all_roles_present():
    """All expected roles exist in the hierarchy."""
    from app.services.collaboration_service import ROLE_HIERARCHY

    assert set(ROLE_HIERARCHY.keys()) == {"owner", "editor", "viewer"}


# ── Model tests ─────────────────────────────────────────────────────────


def test_project_member_model_tablename():
    """ProjectMember has correct table name."""
    from app.models.project_member import ProjectMember

    assert ProjectMember.__tablename__ == "project_members"


def test_comment_model_tablename():
    """Comment has correct table name."""
    from app.models.comment import Comment

    assert Comment.__tablename__ == "comments"


def test_project_member_roles():
    """PROJECT_MEMBER_ROLES includes expected values."""
    from app.models.project_member import PROJECT_MEMBER_ROLES

    assert "owner" in PROJECT_MEMBER_ROLES
    assert "editor" in PROJECT_MEMBER_ROLES
    assert "viewer" in PROJECT_MEMBER_ROLES


def test_models_registered_in_init():
    """ProjectMember and Comment are exported from models __init__."""
    from app.models import Comment, ProjectMember

    assert ProjectMember is not None
    assert Comment is not None


# ── Async endpoint tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_members_async():
    """Async GET /members returns empty list."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        r = await ac.get("/api/projects/test-proj/members")
        assert r.status_code == 200
        assert r.json()["total"] == 0


@pytest.mark.asyncio
async def test_add_member_async():
    """Async POST /members returns member."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        r = await ac.post(
            "/api/projects/test-proj/members",
            json={"email": "async@example.com", "role": "editor"},
        )
        assert r.status_code == 200
        assert r.json()["email"] == "async@example.com"


@pytest.mark.asyncio
async def test_remove_member_async():
    """Async DELETE /members/{user_id} returns success."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        r = await ac.delete(
            "/api/projects/test-proj/members/user-async"
        )
        assert r.status_code == 200
        assert r.json()["removed"] is True


@pytest.mark.asyncio
async def test_add_comment_async():
    """Async POST /comments returns comment."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        r = await ac.post(
            "/api/projects/test-proj/comments",
            json={"content": "Async comment", "component_ref": "nsg"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["content"] == "Async comment"
        assert data["component_ref"] == "nsg"


@pytest.mark.asyncio
async def test_list_comments_async():
    """Async GET /comments returns list."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        r = await ac.get("/api/projects/test-proj/comments")
        assert r.status_code == 200
        assert "comments" in r.json()


@pytest.mark.asyncio
async def test_activity_feed_async():
    """Async GET /activity returns feed."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        r = await ac.get("/api/projects/test-proj/activity")
        assert r.status_code == 200
        assert "activities" in r.json()


@pytest.mark.asyncio
async def test_add_member_all_roles_async():
    """Async POST /members with each valid role."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        for role in ["owner", "editor", "viewer"]:
            r = await ac.post(
                "/api/projects/test-proj/members",
                json={
                    "email": f"{role}@example.com",
                    "role": role,
                },
            )
            assert r.status_code == 200
            assert r.json()["role"] == role


@pytest.mark.asyncio
async def test_add_comment_no_ref_async():
    """Async POST /comments without component_ref."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        r = await ac.post(
            "/api/projects/test-proj/comments",
            json={"content": "No ref"},
        )
        assert r.status_code == 200
        assert r.json()["component_ref"] is None


@pytest.mark.asyncio
async def test_list_comments_with_filter_async():
    """Async GET /comments with component_ref param."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        r = await ac.get(
            "/api/projects/proj-1/comments?component_ref=lb"
        )
        assert r.status_code == 200
        assert r.json()["total"] == 0


@pytest.mark.asyncio
async def test_multiple_projects_members_async():
    """Async: list members for multiple projects."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        for pid in ["proj-1", "proj-2", "proj-3"]:
            r = await ac.get(f"/api/projects/{pid}/members")
            assert r.status_code == 200


@pytest.mark.asyncio
async def test_multiple_projects_comments_async():
    """Async: list comments for multiple projects."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        for pid in ["proj-1", "proj-2", "proj-3"]:
            r = await ac.get(f"/api/projects/{pid}/comments")
            assert r.status_code == 200


@pytest.mark.asyncio
async def test_invalid_role_async():
    """Async POST /members with invalid role returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        r = await ac.post(
            "/api/projects/test-proj/members",
            json={"email": "bad@test.com", "role": "admin"},
        )
        assert r.status_code == 422


@pytest.mark.asyncio
async def test_empty_comment_async():
    """Async POST /comments with empty content returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        r = await ac.post(
            "/api/projects/test-proj/comments",
            json={"content": ""},
        )
        assert r.status_code == 422


# ── Edge case tests ─────────────────────────────────────────────────────


def test_add_member_with_special_chars_in_email():
    """Member email with special characters."""
    r = client.post(
        "/api/projects/proj-1/members",
        json={
            "email": "user+tag@sub.example.com",
            "role": "viewer",
        },
    )
    assert r.status_code == 200
    assert r.json()["email"] == "user+tag@sub.example.com"


def test_comment_with_unicode_content():
    """Comment with unicode characters."""
    r = client.post(
        "/api/projects/proj-1/comments",
        json={"content": "Great design! 🎉 Très bien! 日本語"},
    )
    assert r.status_code == 200
    assert "🎉" in r.json()["content"]


def test_comment_with_newlines():
    """Comment with multi-line content."""
    content = "Line 1\nLine 2\nLine 3"
    r = client.post(
        "/api/projects/proj-1/comments",
        json={"content": content},
    )
    assert r.status_code == 200
    assert r.json()["content"] == content


def test_member_response_has_invited_at():
    """Member response always includes invited_at."""
    r = client.post(
        "/api/projects/proj-1/members",
        json={"email": "ts@example.com", "role": "viewer"},
    )
    assert r.status_code == 200
    assert r.json()["invited_at"] is not None


def test_member_response_accepted_at_null():
    """New member accepted_at is null."""
    r = client.post(
        "/api/projects/proj-1/members",
        json={"email": "new@example.com", "role": "editor"},
    )
    assert r.status_code == 200
    assert r.json()["accepted_at"] is None


def test_member_display_name_from_email():
    """Mock display_name is derived from email prefix."""
    r = client.post(
        "/api/projects/proj-1/members",
        json={"email": "jane.doe@company.com", "role": "viewer"},
    )
    assert r.status_code == 200
    assert r.json()["display_name"] == "jane.doe"
