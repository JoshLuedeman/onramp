"""Tests for full-page AI architect chat — streaming endpoint, conversation
CRUD via routes, and chat system prompt integration.

Covers: streaming SSE endpoint (dev mock + real mode), conversation creation,
listing, get, archive, delete, message send, and CHAT_SYSTEM_PROMPT.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.conversation import SendMessageRequest
from app.services.prompts import CHAT_SYSTEM_PROMPT

client = TestClient(app)


# ════════════════════════════════════════════════════════════════════
# 1. CHAT_SYSTEM_PROMPT tests
# ════════════════════════════════════════════════════════════════════


class TestChatSystemPrompt:
    """Validate the chat system prompt content."""

    def test_prompt_exists(self):
        assert CHAT_SYSTEM_PROMPT is not None
        assert len(CHAT_SYSTEM_PROMPT) > 100

    def test_prompt_mentions_azure(self):
        assert "Azure" in CHAT_SYSTEM_PROMPT

    def test_prompt_mentions_caf(self):
        assert "CAF" in CHAT_SYSTEM_PROMPT or "Cloud Adoption Framework" in CHAT_SYSTEM_PROMPT

    def test_prompt_mentions_markdown(self):
        assert "markdown" in CHAT_SYSTEM_PROMPT.lower()

    def test_prompt_mentions_compliance(self):
        assert "compliance" in CHAT_SYSTEM_PROMPT.lower() or "HIPAA" in CHAT_SYSTEM_PROMPT


# ════════════════════════════════════════════════════════════════════
# 2. Streaming endpoint (dev mode — no DB)
# ════════════════════════════════════════════════════════════════════


class TestStreamEndpointDevMode:
    """Test POST /api/chat/{id}/stream in dev mode (db=None)."""

    def test_stream_returns_sse_content_type(self):
        conv_id = str(uuid.uuid4())
        response = client.post(
            f"/api/chat/{conv_id}/stream",
            json={"content": "Hello architect"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

    def test_stream_contains_data_frames(self):
        conv_id = str(uuid.uuid4())
        response = client.post(
            f"/api/chat/{conv_id}/stream",
            json={"content": "Add disaster recovery"},
        )
        body = response.text
        assert "event: data" in body

    def test_stream_ends_with_done(self):
        conv_id = str(uuid.uuid4())
        response = client.post(
            f"/api/chat/{conv_id}/stream",
            json={"content": "Optimize for cost"},
        )
        body = response.text
        assert "event: done" in body

    def test_stream_echoes_user_content(self):
        conv_id = str(uuid.uuid4())
        msg = "Compare hub-spoke vs mesh"
        response = client.post(
            f"/api/chat/{conv_id}/stream",
            json={"content": msg},
        )
        body = response.text
        # The mock stream should reference the user's message
        assert "Compare" in body or "hub-spoke" in body

    def test_stream_mock_includes_architectural_advice(self):
        conv_id = str(uuid.uuid4())
        response = client.post(
            f"/api/chat/{conv_id}/stream",
            json={"content": "Help me with security"},
        )
        body = response.text
        # Mock response includes Azure architectural terms
        assert "Azure" in body or "Policy" in body or "managed" in body

    def test_stream_rejects_empty_content(self):
        conv_id = str(uuid.uuid4())
        response = client.post(
            f"/api/chat/{conv_id}/stream",
            json={"content": ""},
        )
        assert response.status_code == 422

    def test_stream_multiple_data_frames(self):
        conv_id = str(uuid.uuid4())
        response = client.post(
            f"/api/chat/{conv_id}/stream",
            json={"content": "Right-size my VMs"},
        )
        body = response.text
        data_count = body.count("event: data")
        # Should have multiple tokens
        assert data_count >= 3

    def test_stream_starts_with_status_event(self):
        conv_id = str(uuid.uuid4())
        response = client.post(
            f"/api/chat/{conv_id}/stream",
            json={"content": "Test status event"},
        )
        body = response.text
        assert "event: status" in body
        assert '"started"' in body

    def test_stream_done_contains_full_text(self):
        conv_id = str(uuid.uuid4())
        response = client.post(
            f"/api/chat/{conv_id}/stream",
            json={"content": "Full text test"},
        )
        body = response.text
        assert "event: done" in body
        assert "full_text" in body


# ════════════════════════════════════════════════════════════════════
# 3. Conversation CRUD endpoints (dev mode)
# ════════════════════════════════════════════════════════════════════


class TestConversationCreateDevMode:
    """Test POST /api/chat/new in dev mode."""

    def test_create_returns_conversation(self):
        response = client.post(
            "/api/chat/new",
            json={"project_id": "test-project"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] == "active"
        assert data["project_id"] == "test-project"

    def test_create_with_title(self):
        response = client.post(
            "/api/chat/new",
            json={"project_id": "proj-1", "title": "Security Chat"},
        )
        data = response.json()
        assert data["title"] == "Security Chat"

    def test_create_default_title(self):
        response = client.post(
            "/api/chat/new",
            json={"project_id": "proj-1"},
        )
        data = response.json()
        assert data["title"] == "New conversation"


class TestConversationListDevMode:
    """Test GET /api/chat/conversations in dev mode."""

    def test_list_returns_empty(self):
        response = client.get("/api/chat/conversations?project_id=test-project")
        assert response.status_code == 200
        data = response.json()
        assert data["conversations"] == []


class TestConversationGetDevMode:
    """Test GET /api/chat/{id} in dev mode."""

    def test_get_returns_conversation(self):
        conv_id = str(uuid.uuid4())
        response = client.get(f"/api/chat/{conv_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conv_id
        assert data["messages"] == []


class TestSendMessageDevMode:
    """Test POST /api/chat/{id}/message in dev mode."""

    def test_send_returns_assistant_message(self):
        conv_id = str(uuid.uuid4())
        response = client.post(
            f"/api/chat/{conv_id}/message",
            json={"content": "Add HIPAA compliance"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "assistant_message" in data
        assert data["assistant_message"]["role"] == "assistant"

    def test_send_message_dev_mode_content(self):
        conv_id = str(uuid.uuid4())
        response = client.post(
            f"/api/chat/{conv_id}/message",
            json={"content": "Hello from test"},
        )
        data = response.json()
        assert "Dev mode" in data["assistant_message"]["content"]


class TestArchiveDeleteDevMode:
    """Test archive and delete in dev mode."""

    def test_archive_returns_archived(self):
        conv_id = str(uuid.uuid4())
        response = client.post(f"/api/chat/{conv_id}/archive")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "archived"

    def test_delete_returns_deleted(self):
        conv_id = str(uuid.uuid4())
        response = client.delete(f"/api/chat/{conv_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True


# ════════════════════════════════════════════════════════════════════
# 4. _mock_stream_tokens unit test
# ════════════════════════════════════════════════════════════════════


class TestMockStreamTokens:
    """Test the internal _mock_stream_tokens helper."""

    @pytest.mark.asyncio
    async def test_mock_stream_yields_tokens(self):
        from app.api.routes.chat import _mock_stream_tokens

        tokens = []
        async for token in _mock_stream_tokens("hello world test"):
            tokens.append(token)

        # Should have status + word tokens + done
        assert len(tokens) >= 5  # status + 3 words + done
        assert "event: done" in tokens[-1]

    @pytest.mark.asyncio
    async def test_mock_stream_data_format(self):
        from app.api.routes.chat import _mock_stream_tokens

        tokens = []
        async for token in _mock_stream_tokens("a b"):
            tokens.append(token)

        # First event is status
        assert tokens[0].startswith("event: status")
        # Data events contain token
        assert "event: data" in tokens[1]
        assert tokens[1].endswith("\n\n")

    @pytest.mark.asyncio
    async def test_mock_stream_starts_with_status(self):
        from app.api.routes.chat import _mock_stream_tokens

        tokens = []
        async for token in _mock_stream_tokens("test"):
            tokens.append(token)
        assert "event: status" in tokens[0]
        assert '"started"' in tokens[0]

    @pytest.mark.asyncio
    async def test_mock_stream_done_has_full_text(self):
        from app.api.routes.chat import _mock_stream_tokens

        tokens = []
        async for token in _mock_stream_tokens("hello world"):
            tokens.append(token)
        last = tokens[-1]
        assert "event: done" in last
        assert "full_text" in last


# ════════════════════════════════════════════════════════════════════
# 5. SendMessageRequest validation
# ════════════════════════════════════════════════════════════════════


class TestSendMessageRequestValidation:
    """Test the request schema validation."""

    def test_valid_message(self):
        req = SendMessageRequest(content="Hello")
        assert req.content == "Hello"

    def test_empty_content_rejected(self):
        with pytest.raises(Exception):
            SendMessageRequest(content="")

    def test_max_length_boundary(self):
        long_msg = "x" * 32_000
        req = SendMessageRequest(content=long_msg)
        assert len(req.content) == 32_000

    def test_over_max_length_rejected(self):
        with pytest.raises(Exception):
            SendMessageRequest(content="x" * 32_001)
