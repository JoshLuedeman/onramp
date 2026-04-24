"""Comprehensive tests for conversation state management.

Covers: models, schemas, ConversationManager CRUD, send_message,
context window management, token counting, route endpoints, dev mode,
and stale conversation cleanup.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.base import Base, generate_uuid
from app.schemas.conversation import (
    ConversationCreate,
    ConversationMessageResponse,
    ConversationResponse,
    ConversationStatus,
    ConversationWithMessages,
    MessageRole,
    SendMessageRequest,
    SendMessageResponse,
)
from app.services.conversation_manager import (
    CHARS_PER_TOKEN,
    DEFAULT_MAX_TOKENS,
    SYSTEM_PROMPT,
    ConversationManager,
    estimate_tokens,
)

client = TestClient(app)


# ════════════════════════════════════════════════════════════════════
# Helper: in-memory async SQLite DB for integration tests
# ════════════════════════════════════════════════════════════════════

SQLITE_URL = "sqlite+aiosqlite:///:memory:"


async def _setup_db():
    """Create an in-memory async engine with all tables."""
    engine = create_async_engine(SQLITE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory


async def _seed_project(session: AsyncSession) -> str:
    """Insert a minimal tenant, user, and project; return project_id."""
    from app.models.tenant import Tenant
    from app.models.user import User
    from app.models.project import Project

    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())

    tenant = Tenant(id=tenant_id, name="Test Tenant")
    session.add(tenant)
    await session.flush()

    user = User(
        id=user_id,
        entra_object_id=str(uuid.uuid4()),
        email="test@example.com",
        display_name="Test User",
        tenant_id=tenant_id,
    )
    session.add(user)
    await session.flush()

    project = Project(
        id=project_id,
        name="Test Project",
        tenant_id=tenant_id,
        created_by=user_id,
    )
    session.add(project)
    await session.flush()
    return project_id, user_id, tenant_id


# ════════════════════════════════════════════════════════════════════
# 1. Schema / Enum tests
# ════════════════════════════════════════════════════════════════════


def test_conversation_status_values():
    assert ConversationStatus.ACTIVE == "active"
    assert ConversationStatus.ARCHIVED == "archived"
    assert ConversationStatus.DELETED == "deleted"


def test_message_role_values():
    assert MessageRole.SYSTEM == "system"
    assert MessageRole.USER == "user"
    assert MessageRole.ASSISTANT == "assistant"


def test_conversation_create_schema():
    c = ConversationCreate(project_id="proj-1")
    assert c.project_id == "proj-1"
    assert c.title is None


def test_conversation_create_with_title():
    c = ConversationCreate(project_id="proj-1", title="My Chat")
    assert c.title == "My Chat"


def test_send_message_request_schema():
    req = SendMessageRequest(content="Hello AI")
    assert req.content == "Hello AI"


def test_send_message_request_min_length():
    with pytest.raises(Exception):
        SendMessageRequest(content="")


def test_conversation_response_from_attributes():
    now = datetime.now(timezone.utc)
    r = ConversationResponse(
        id="abc",
        title="Chat",
        status="active",
        model_name="gpt-4o",
        total_tokens=100,
        project_id="proj-1",
        created_at=now,
        updated_at=now,
        message_count=5,
    )
    assert r.id == "abc"
    assert r.message_count == 5


def test_conversation_message_response():
    now = datetime.now(timezone.utc)
    m = ConversationMessageResponse(
        id="msg-1", role="user", content="Hi", token_count=1, created_at=now
    )
    assert m.role == "user"
    assert m.token_count == 1


def test_conversation_with_messages():
    now = datetime.now(timezone.utc)
    cw = ConversationWithMessages(
        id="abc",
        status="active",
        model_name="gpt-4o",
        total_tokens=0,
        project_id="proj-1",
        created_at=now,
        updated_at=now,
        messages=[],
    )
    assert cw.messages == []


def test_send_message_response():
    now = datetime.now(timezone.utc)
    msg = ConversationMessageResponse(
        id="m1", role="assistant", content="Reply", token_count=2, created_at=now
    )
    conv = ConversationResponse(
        id="c1",
        status="active",
        model_name="gpt-4o",
        total_tokens=10,
        project_id="p1",
        created_at=now,
        updated_at=now,
    )
    resp = SendMessageResponse(assistant_message=msg, conversation=conv)
    assert resp.assistant_message.role == "assistant"
    assert resp.conversation.id == "c1"


# ════════════════════════════════════════════════════════════════════
# 2. Token estimation tests
# ════════════════════════════════════════════════════════════════════


def test_estimate_tokens_empty():
    assert estimate_tokens("") == 1  # minimum 1


def test_estimate_tokens_short():
    assert estimate_tokens("Hi") == 1


def test_estimate_tokens_normal():
    text = "This is a normal sentence that should produce several tokens."
    tokens = estimate_tokens(text)
    assert tokens == len(text) // CHARS_PER_TOKEN


def test_estimate_tokens_long():
    text = "x" * 400
    assert estimate_tokens(text) == 100


# ════════════════════════════════════════════════════════════════════
# 3. Context window management tests
# ════════════════════════════════════════════════════════════════════


def test_context_window_empty():
    mgr = ConversationManager()
    result = mgr._build_context_window([])
    assert result == []


def test_context_window_single_system():
    mgr = ConversationManager()
    msgs = [MagicMock(role="system", content="You are a helper.", token_count=5)]
    result = mgr._build_context_window(msgs, max_tokens=100)
    assert len(result) == 1
    assert result[0]["role"] == "system"


def test_context_window_keeps_system_plus_user():
    mgr = ConversationManager()
    msgs = [
        MagicMock(role="system", content="System prompt.", token_count=3),
        MagicMock(role="user", content="Hello!", token_count=2),
    ]
    result = mgr._build_context_window(msgs, max_tokens=100)
    assert len(result) == 2
    assert result[0]["role"] == "system"
    assert result[1]["role"] == "user"


def test_context_window_respects_token_limit():
    mgr = ConversationManager()
    msgs = [
        MagicMock(role="system", content="Sys", token_count=5),
        MagicMock(role="user", content="Old message", token_count=50),
        MagicMock(role="assistant", content="Old reply", token_count=50),
        MagicMock(role="user", content="New message", token_count=10),
    ]
    # Budget = 20; system=5 leaves 15; latest user=10 fits; assistant=50 won't
    result = mgr._build_context_window(msgs, max_tokens=20)
    assert len(result) == 2  # system + latest user
    assert result[0]["role"] == "system"
    assert result[1]["content"] == "New message"


def test_context_window_preserves_order():
    mgr = ConversationManager()
    msgs = [
        MagicMock(role="system", content="Sys", token_count=2),
        MagicMock(role="user", content="Q1", token_count=2),
        MagicMock(role="assistant", content="A1", token_count=2),
        MagicMock(role="user", content="Q2", token_count=2),
        MagicMock(role="assistant", content="A2", token_count=2),
    ]
    result = mgr._build_context_window(msgs, max_tokens=100)
    roles = [m["role"] for m in result]
    assert roles == ["system", "user", "assistant", "user", "assistant"]


def test_context_window_truncates_oldest_first():
    mgr = ConversationManager()
    msgs = [
        MagicMock(role="system", content="Sys", token_count=2),
        MagicMock(role="user", content="Q1", token_count=5),
        MagicMock(role="assistant", content="A1", token_count=5),
        MagicMock(role="user", content="Q2", token_count=5),
        MagicMock(role="assistant", content="A2", token_count=5),
    ]
    # Budget = 17; system=2 leaves 15; from end: A2(5)=10, Q2(5)=5, A1(5)=0 — exactly fits 3
    result = mgr._build_context_window(msgs, max_tokens=17)
    assert len(result) == 4  # sys + A1+Q2+A2
    contents = [m["content"] for m in result]
    assert "Q1" not in contents  # oldest dropped
    assert "Sys" in contents
    assert "A2" in contents


def test_context_window_with_dict_messages():
    """Test that dict-based messages work (not just ORM objects)."""
    mgr = ConversationManager()
    msgs = [
        {"role": "system", "content": "Sys", "token_count": None},
        {"role": "user", "content": "Hello", "token_count": None},
    ]
    result = mgr._build_context_window(msgs, max_tokens=100)
    assert len(result) == 2


def test_context_window_very_large_system_prompt():
    """If system prompt nearly fills budget, only system is returned."""
    mgr = ConversationManager()
    msgs = [
        MagicMock(role="system", content="x" * 400, token_count=95),
        MagicMock(role="user", content="Hello", token_count=10),
    ]
    # System takes 95, only 5 left, user needs 10 — user is dropped
    result = mgr._build_context_window(msgs, max_tokens=100)
    assert len(result) == 1  # only system fits


# ════════════════════════════════════════════════════════════════════
# 4. Mock AI response tests
# ════════════════════════════════════════════════════════════════════


def test_mock_ai_architecture():
    mgr = ConversationManager()
    msgs = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "Tell me about landing zone architecture"},
    ]
    result = mgr._mock_ai_response(msgs)
    assert "hub-spoke" in result.lower() or "landing zone" in result.lower()


def test_mock_ai_compliance():
    mgr = ConversationManager()
    msgs = [{"role": "user", "content": "How do I ensure compliance?"}]
    result = mgr._mock_ai_response(msgs)
    assert "compliance" in result.lower() or "policy" in result.lower()


def test_mock_ai_cost():
    mgr = ConversationManager()
    msgs = [{"role": "user", "content": "Help with budget optimization"}]
    result = mgr._mock_ai_response(msgs)
    assert "cost" in result.lower() or "budget" in result.lower() or "reserved" in result.lower()


def test_mock_ai_deployment():
    mgr = ConversationManager()
    msgs = [{"role": "user", "content": "How to deploy with bicep?"}]
    result = mgr._mock_ai_response(msgs)
    assert "deploy" in result.lower() or "bicep" in result.lower()


def test_mock_ai_generic():
    mgr = ConversationManager()
    msgs = [{"role": "user", "content": "Tell me about dogs"}]
    result = mgr._mock_ai_response(msgs)
    assert "dogs" in result.lower() or "azure" in result.lower()


def test_mock_ai_no_user_message():
    mgr = ConversationManager()
    msgs = [{"role": "system", "content": "sys"}]
    result = mgr._mock_ai_response(msgs)
    assert isinstance(result, str)


# ════════════════════════════════════════════════════════════════════
# 5. ConversationManager CRUD (async, with real SQLite)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_conversation():
    engine, factory = await _setup_db()
    async with factory() as session:
        pid, uid, tid = await _seed_project(session)
        mgr = ConversationManager()
        conv = await mgr.create_conversation(session, pid, uid, tid, title="Test Chat")
        assert conv.id is not None
        assert conv.title == "Test Chat"
        assert conv.status == "active"
        assert conv.total_tokens > 0  # system prompt tokens
        await session.commit()
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_conversation_default_title():
    engine, factory = await _setup_db()
    async with factory() as session:
        pid, uid, tid = await _seed_project(session)
        mgr = ConversationManager()
        conv = await mgr.create_conversation(session, pid, uid, tid)
        assert conv.title == "New conversation"
        await session.commit()
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_conversation():
    engine, factory = await _setup_db()
    async with factory() as session:
        pid, uid, tid = await _seed_project(session)
        mgr = ConversationManager()
        conv = await mgr.create_conversation(session, pid, uid, tid)
        await session.commit()

    async with factory() as session:
        result = await mgr.get_conversation(session, conv.id)
        assert result is not None
        assert result.id == conv.id
        assert len(result.messages) == 1  # system prompt
        assert result.messages[0].role == "system"
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_conversation_not_found():
    engine, factory = await _setup_db()
    async with factory() as session:
        mgr = ConversationManager()
        result = await mgr.get_conversation(session, "nonexistent-id")
        assert result is None
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_deleted_conversation_returns_none():
    engine, factory = await _setup_db()
    async with factory() as session:
        pid, uid, tid = await _seed_project(session)
        mgr = ConversationManager()
        conv = await mgr.create_conversation(session, pid, uid, tid)
        await mgr.delete_conversation(session, conv.id)
        await session.commit()

    async with factory() as session:
        result = await mgr.get_conversation(session, conv.id)
        assert result is None
    await engine.dispose()


@pytest.mark.asyncio
async def test_list_conversations():
    engine, factory = await _setup_db()
    async with factory() as session:
        pid, uid, tid = await _seed_project(session)
        mgr = ConversationManager()
        await mgr.create_conversation(session, pid, uid, tid, title="Chat 1")
        await mgr.create_conversation(session, pid, uid, tid, title="Chat 2")
        await session.commit()

    async with factory() as session:
        rows = await mgr.list_conversations(session, pid, uid)
        assert len(rows) == 2
        # Should be ordered by created_at desc
        titles = [r["conversation"].title for r in rows]
        assert "Chat 1" in titles
        assert "Chat 2" in titles
    await engine.dispose()


@pytest.mark.asyncio
async def test_list_conversations_excludes_deleted():
    engine, factory = await _setup_db()
    async with factory() as session:
        pid, uid, tid = await _seed_project(session)
        mgr = ConversationManager()
        c1 = await mgr.create_conversation(session, pid, uid, tid, title="Active")
        c2 = await mgr.create_conversation(session, pid, uid, tid, title="Deleted")
        await mgr.delete_conversation(session, c2.id)
        await session.commit()

    async with factory() as session:
        rows = await mgr.list_conversations(session, pid, uid)
        assert len(rows) == 1
        assert rows[0]["conversation"].title == "Active"
    await engine.dispose()


@pytest.mark.asyncio
async def test_list_conversations_has_message_count():
    engine, factory = await _setup_db()
    async with factory() as session:
        pid, uid, tid = await _seed_project(session)
        mgr = ConversationManager()
        conv = await mgr.create_conversation(session, pid, uid, tid)
        await session.commit()

    async with factory() as session:
        rows = await mgr.list_conversations(session, pid, uid)
        assert rows[0]["message_count"] == 1  # system prompt
    await engine.dispose()


# ════════════════════════════════════════════════════════════════════
# 6. Send message tests (with mock AI)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_send_message():
    engine, factory = await _setup_db()
    async with factory() as session:
        pid, uid, tid = await _seed_project(session)
        mgr = ConversationManager()
        conv = await mgr.create_conversation(session, pid, uid, tid)
        await session.commit()

    async with factory() as session:
        # Re-fetch to attach to this session
        conv = await mgr.get_conversation(session, conv.id)
        initial_tokens = conv.total_tokens
        assistant_msg, updated_conv = await mgr.send_message(
            session, conv.id, "Tell me about landing zone architecture", uid
        )
        assert assistant_msg.role == "assistant"
        assert len(assistant_msg.content) > 0
        assert assistant_msg.token_count > 0
        assert updated_conv.total_tokens > initial_tokens
        await session.commit()
    await engine.dispose()


@pytest.mark.asyncio
async def test_send_message_stores_both_messages():
    engine, factory = await _setup_db()
    async with factory() as session:
        pid, uid, tid = await _seed_project(session)
        mgr = ConversationManager()
        conv = await mgr.create_conversation(session, pid, uid, tid)
        await session.commit()

    async with factory() as session:
        conv = await mgr.get_conversation(session, conv.id)
        await mgr.send_message(session, conv.id, "Hello", uid)
        await session.commit()

    async with factory() as session:
        conv = await mgr.get_conversation(session, conv.id)
        roles = [m.role for m in conv.messages]
        assert roles == ["system", "user", "assistant"]
    await engine.dispose()


@pytest.mark.asyncio
async def test_send_multiple_messages():
    engine, factory = await _setup_db()
    async with factory() as session:
        pid, uid, tid = await _seed_project(session)
        mgr = ConversationManager()
        conv = await mgr.create_conversation(session, pid, uid, tid)
        await session.commit()

    async with factory() as session:
        conv = await mgr.get_conversation(session, conv.id)
        await mgr.send_message(session, conv.id, "First question", uid)
        await session.commit()

    async with factory() as session:
        conv = await mgr.get_conversation(session, conv.id)
        await mgr.send_message(session, conv.id, "Follow up question", uid)
        await session.commit()

    async with factory() as session:
        conv = await mgr.get_conversation(session, conv.id)
        assert len(conv.messages) == 5  # system + 2*(user + assistant)
    await engine.dispose()


@pytest.mark.asyncio
async def test_send_message_not_found():
    engine, factory = await _setup_db()
    async with factory() as session:
        mgr = ConversationManager()
        with pytest.raises(ValueError, match="not found"):
            await mgr.send_message(session, "fake-id", "Hello", "user-1")
    await engine.dispose()


@pytest.mark.asyncio
async def test_send_message_archived_conversation():
    engine, factory = await _setup_db()
    async with factory() as session:
        pid, uid, tid = await _seed_project(session)
        mgr = ConversationManager()
        conv = await mgr.create_conversation(session, pid, uid, tid)
        await mgr.archive_conversation(session, conv.id)
        await session.commit()

    async with factory() as session:
        with pytest.raises(ValueError, match="archived"):
            await mgr.send_message(session, conv.id, "Hello", uid)
    await engine.dispose()


@pytest.mark.asyncio
async def test_send_message_wrong_user():
    engine, factory = await _setup_db()
    async with factory() as session:
        pid, uid, tid = await _seed_project(session)
        mgr = ConversationManager()
        conv = await mgr.create_conversation(session, pid, uid, tid)
        await session.commit()

    async with factory() as session:
        conv = await mgr.get_conversation(session, conv.id)
        with pytest.raises(PermissionError, match="Not your conversation"):
            await mgr.send_message(session, conv.id, "Hello", "different-user")
    await engine.dispose()


@pytest.mark.asyncio
async def test_send_message_updates_token_count():
    engine, factory = await _setup_db()
    async with factory() as session:
        pid, uid, tid = await _seed_project(session)
        mgr = ConversationManager()
        conv = await mgr.create_conversation(session, pid, uid, tid)
        initial_tokens = conv.total_tokens
        await session.commit()

    async with factory() as session:
        conv = await mgr.get_conversation(session, conv.id)
        _, updated = await mgr.send_message(session, conv.id, "Test message", uid)
        assert updated.total_tokens > initial_tokens
        await session.commit()
    await engine.dispose()


# ════════════════════════════════════════════════════════════════════
# 7. Archive / Delete tests
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_archive_conversation():
    engine, factory = await _setup_db()
    async with factory() as session:
        pid, uid, tid = await _seed_project(session)
        mgr = ConversationManager()
        conv = await mgr.create_conversation(session, pid, uid, tid)
        result = await mgr.archive_conversation(session, conv.id)
        assert result.status == "archived"
        await session.commit()
    await engine.dispose()


@pytest.mark.asyncio
async def test_archive_not_found():
    engine, factory = await _setup_db()
    async with factory() as session:
        mgr = ConversationManager()
        with pytest.raises(ValueError, match="not found"):
            await mgr.archive_conversation(session, "fake-id")
    await engine.dispose()


@pytest.mark.asyncio
async def test_delete_conversation():
    engine, factory = await _setup_db()
    async with factory() as session:
        pid, uid, tid = await _seed_project(session)
        mgr = ConversationManager()
        conv = await mgr.create_conversation(session, pid, uid, tid)
        result = await mgr.delete_conversation(session, conv.id)
        assert result.status == "deleted"
        await session.commit()
    await engine.dispose()


@pytest.mark.asyncio
async def test_delete_not_found():
    engine, factory = await _setup_db()
    async with factory() as session:
        mgr = ConversationManager()
        with pytest.raises(ValueError, match="not found"):
            await mgr.delete_conversation(session, "fake-id")
    await engine.dispose()


# ════════════════════════════════════════════════════════════════════
# 8. Cleanup stale tests
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_cleanup_stale_no_stale():
    engine, factory = await _setup_db()
    async with factory() as session:
        pid, uid, tid = await _seed_project(session)
        mgr = ConversationManager()
        await mgr.create_conversation(session, pid, uid, tid)
        await session.commit()

    async with factory() as session:
        count = await mgr.cleanup_stale(session, max_age_days=30)
        assert count == 0
        await session.commit()
    await engine.dispose()


@pytest.mark.asyncio
async def test_cleanup_stale_removes_old_archived():
    engine, factory = await _setup_db()
    async with factory() as session:
        pid, uid, tid = await _seed_project(session)
        mgr = ConversationManager()
        conv = await mgr.create_conversation(session, pid, uid, tid)
        await mgr.archive_conversation(session, conv.id)
        # Manually age the conversation
        old_date = datetime.now(timezone.utc) - timedelta(days=60)
        conv.updated_at = old_date
        await session.commit()

    async with factory() as session:
        count = await mgr.cleanup_stale(session, max_age_days=30)
        assert count == 1
        await session.commit()
    await engine.dispose()


@pytest.mark.asyncio
async def test_cleanup_stale_preserves_active():
    engine, factory = await _setup_db()
    async with factory() as session:
        pid, uid, tid = await _seed_project(session)
        mgr = ConversationManager()
        conv = await mgr.create_conversation(session, pid, uid, tid)
        # Age it but keep active
        old_date = datetime.now(timezone.utc) - timedelta(days=60)
        conv.updated_at = old_date
        await session.commit()

    async with factory() as session:
        count = await mgr.cleanup_stale(session, max_age_days=30)
        assert count == 0  # active conversations not cleaned
        await session.commit()
    await engine.dispose()


@pytest.mark.asyncio
async def test_cleanup_stale_custom_age():
    engine, factory = await _setup_db()
    async with factory() as session:
        pid, uid, tid = await _seed_project(session)
        mgr = ConversationManager()
        conv = await mgr.create_conversation(session, pid, uid, tid)
        await mgr.delete_conversation(session, conv.id)
        # Age it 10 days
        old_date = datetime.now(timezone.utc) - timedelta(days=10)
        conv.updated_at = old_date
        await session.commit()

    async with factory() as session:
        count = await mgr.cleanup_stale(session, max_age_days=5)
        assert count == 1
        await session.commit()
    await engine.dispose()


# ════════════════════════════════════════════════════════════════════
# 9. Route endpoint tests (TestClient, dev mode — no DB)
# ════════════════════════════════════════════════════════════════════


def test_route_create_conversation():
    r = client.post("/api/chat/new", json={"project_id": "proj-1"})
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["status"] == "active"
    assert data["model_name"] == "gpt-4o"


def test_route_create_conversation_with_title():
    r = client.post("/api/chat/new", json={"project_id": "proj-1", "title": "My Chat"})
    assert r.status_code == 201
    assert r.json()["title"] == "My Chat"


def test_route_create_conversation_missing_project():
    r = client.post("/api/chat/new", json={})
    assert r.status_code == 422


def test_route_list_conversations():
    r = client.get("/api/chat/conversations?project_id=proj-1")
    assert r.status_code == 200
    data = r.json()
    assert "conversations" in data
    assert isinstance(data["conversations"], list)


def test_route_list_conversations_missing_project():
    r = client.get("/api/chat/conversations")
    assert r.status_code == 422


def test_route_get_conversation():
    r = client.get("/api/chat/some-conv-id")
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert "messages" in data


def test_route_send_message():
    r = client.post(
        "/api/chat/some-conv-id/message",
        json={"content": "Hello AI, tell me about Azure"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "assistant_message" in data
    assert "conversation" in data
    assert data["assistant_message"]["role"] == "assistant"


def test_route_send_message_empty_content():
    r = client.post(
        "/api/chat/some-conv-id/message",
        json={"content": ""},
    )
    assert r.status_code == 422


def test_route_archive_conversation():
    r = client.post("/api/chat/some-conv-id/archive")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "archived"


def test_route_delete_conversation():
    r = client.delete("/api/chat/some-conv-id")
    assert r.status_code == 200
    data = r.json()
    assert data["deleted"] is True


def test_route_send_message_has_token_count():
    r = client.post(
        "/api/chat/some-conv-id/message",
        json={"content": "Hello there"},
    )
    data = r.json()
    assert data["assistant_message"]["token_count"] is not None


def test_route_send_message_dev_mode_response():
    """Dev mode returns a helpful mock response."""
    r = client.post(
        "/api/chat/some-conv-id/message",
        json={"content": "Tell me about compliance"},
    )
    data = r.json()
    assert "[Dev mode]" in data["assistant_message"]["content"]


# ════════════════════════════════════════════════════════════════════
# 10. Model import tests
# ════════════════════════════════════════════════════════════════════


def test_models_importable():
    from app.models import Conversation, ConversationMessage

    assert Conversation.__tablename__ == "conversations"
    assert ConversationMessage.__tablename__ == "conversation_messages"


def test_conversation_model_defaults():
    """Verify that a Conversation model has expected column definitions."""
    from app.models.conversation import Conversation

    # Column-level defaults are only applied at DB flush time, so check the column config
    table = Conversation.__table__
    assert table.c.status.default.arg == "active"
    assert table.c.model_name.default.arg == "gpt-4o"
    assert table.c.total_tokens.default.arg == 0


def test_conversation_message_roles():
    from app.models.conversation import MESSAGE_ROLES

    assert "system" in MESSAGE_ROLES
    assert "user" in MESSAGE_ROLES
    assert "assistant" in MESSAGE_ROLES


def test_conversation_statuses():
    from app.models.conversation import CONVERSATION_STATUSES

    assert "active" in CONVERSATION_STATUSES
    assert "archived" in CONVERSATION_STATUSES
    assert "deleted" in CONVERSATION_STATUSES


# ════════════════════════════════════════════════════════════════════
# 11. System prompt and constants tests
# ════════════════════════════════════════════════════════════════════


def test_system_prompt_not_empty():
    assert len(SYSTEM_PROMPT) > 0


def test_default_max_tokens():
    assert DEFAULT_MAX_TOKENS == 8000


def test_chars_per_token():
    assert CHARS_PER_TOKEN == 4


def test_conversation_manager_singleton():
    from app.services.conversation_manager import conversation_manager

    assert isinstance(conversation_manager, ConversationManager)


# ════════════════════════════════════════════════════════════════════
# 12. Additional edge case tests
# ════════════════════════════════════════════════════════════════════


def test_context_window_all_messages_fit():
    """When all messages fit, all are returned."""
    mgr = ConversationManager()
    msgs = [
        MagicMock(role="system", content="S", token_count=1),
        MagicMock(role="user", content="U1", token_count=1),
        MagicMock(role="assistant", content="A1", token_count=1),
        MagicMock(role="user", content="U2", token_count=1),
    ]
    result = mgr._build_context_window(msgs, max_tokens=100)
    assert len(result) == 4


def test_context_window_only_system_prompt_fits():
    """When only system prompt fits, return just system."""
    mgr = ConversationManager()
    msgs = [
        MagicMock(role="system", content="S", token_count=99),
        MagicMock(role="user", content="U", token_count=10),
    ]
    # System takes 99, user needs 10, only 1 left — user is dropped
    result = mgr._build_context_window(msgs, max_tokens=100)
    assert len(result) == 1  # only system fits


def test_generate_uuid_format():
    uid = generate_uuid()
    assert len(uid) == 36
    assert uid.count("-") == 4


@pytest.mark.asyncio
async def test_create_conversation_has_system_message():
    """Creating a conversation seeds it with a system prompt message."""
    engine, factory = await _setup_db()
    async with factory() as session:
        pid, uid, tid = await _seed_project(session)
        mgr = ConversationManager()
        conv = await mgr.create_conversation(session, pid, uid, tid)
        await session.commit()

    async with factory() as session:
        conv = await mgr.get_conversation(session, conv.id)
        system_msgs = [m for m in conv.messages if m.role == "system"]
        assert len(system_msgs) == 1
        assert "OnRamp AI" in system_msgs[0].content
    await engine.dispose()


@pytest.mark.asyncio
async def test_conversation_model_name():
    engine, factory = await _setup_db()
    async with factory() as session:
        pid, uid, tid = await _seed_project(session)
        mgr = ConversationManager()
        conv = await mgr.create_conversation(session, pid, uid, tid)
        assert conv.model_name is not None
        assert len(conv.model_name) > 0
        await session.commit()
    await engine.dispose()


def test_mock_response_contains_text():
    mgr = ConversationManager()
    msgs = [{"role": "user", "content": "What is Azure?"}]
    result = mgr._mock_ai_response(msgs)
    assert isinstance(result, str)
    assert len(result) > 10


def test_context_window_budget_exactly_zero():
    """When budget == tokens needed, messages still fit."""
    mgr = ConversationManager()
    msgs = [
        MagicMock(role="system", content="S", token_count=5),
        MagicMock(role="user", content="U", token_count=5),
    ]
    result = mgr._build_context_window(msgs, max_tokens=10)
    assert len(result) == 2
