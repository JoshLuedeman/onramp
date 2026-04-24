"""Chat API routes for multi-turn AI conversations."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_db
from app.schemas.conversation import (
    ConversationCreate,
    SendMessageRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _mock_conversation(project_id: str, title: str | None = None) -> dict:
    """Return a mock conversation dict for dev mode without DB."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(uuid.uuid4()),
        "title": title or "New conversation",
        "status": "active",
        "model_name": "gpt-4o",
        "total_tokens": 0,
        "project_id": project_id,
        "created_at": now,
        "updated_at": now,
        "message_count": 0,
    }


def _serialize_conversation(conv, message_count: int = 0) -> dict:
    """Serialize a Conversation ORM object to a response dict."""
    return {
        "id": conv.id,
        "title": conv.title,
        "status": conv.status,
        "model_name": conv.model_name,
        "total_tokens": conv.total_tokens,
        "project_id": conv.project_id,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        "message_count": message_count,
    }


def _serialize_message(msg) -> dict:
    """Serialize a ConversationMessage ORM object to a response dict."""
    return {
        "id": msg.id,
        "role": msg.role,
        "content": msg.content,
        "token_count": msg.token_count,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


@router.post("/new", status_code=201)
async def create_conversation(
    body: ConversationCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation."""
    if db is None:
        return _mock_conversation(body.project_id, body.title)

    try:
        from app.services.conversation_manager import conversation_manager

        user_id = user.get("sub", "dev-user-id")
        tenant_id = user.get("tid", user.get("tenant_id", "dev-tenant"))

        conv = await conversation_manager.create_conversation(
            db=db,
            project_id=body.project_id,
            user_id=user_id,
            tenant_id=tenant_id,
            title=body.title,
        )
        return _serialize_conversation(conv, message_count=1)  # system prompt
    except Exception:
        logger.exception("Unexpected error in chat route")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/conversations")
async def list_conversations(
    project_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all conversations for a project."""
    if db is None:
        return {"conversations": []}

    try:
        from app.services.conversation_manager import conversation_manager

        user_id = user.get("sub", "dev-user-id")

        rows = await conversation_manager.list_conversations(
            db=db,
            project_id=project_id,
            user_id=user_id,
        )
        return {
            "conversations": [
                _serialize_conversation(row["conversation"], row["message_count"])
                for row in rows
            ]
        }
    except Exception:
        logger.exception("Unexpected error in chat route")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a conversation with full message history."""
    if db is None:
        return {
            **_mock_conversation("dev-project"),
            "id": conversation_id,
            "messages": [],
        }

    try:
        from app.services.conversation_manager import conversation_manager

        conv = await conversation_manager.get_conversation(db, conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

        result = _serialize_conversation(conv, len(conv.messages))
        result["messages"] = [_serialize_message(m) for m in conv.messages]
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error in chat route")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{conversation_id}/message")
async def send_message(
    conversation_id: str,
    body: SendMessageRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message and get an AI response."""
    if db is None:
        # Dev mode mock response
        now = datetime.now(timezone.utc).isoformat()
        return {
            "assistant_message": {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": (
                    f"[Dev mode] I received your message: '{body.content[:100]}'. "
                    "This is a mock response since no database is configured."
                ),
                "token_count": 30,
                "created_at": now,
            },
            "conversation": {
                **_mock_conversation("dev-project"),
                "id": conversation_id,
            },
        }

    try:
        from app.services.conversation_manager import conversation_manager

        user_id = user.get("sub", "dev-user-id")

        assistant_msg, conv = await conversation_manager.send_message(
            db=db,
            conversation_id=conversation_id,
            content=body.content,
            user_id=user_id,
        )
        return {
            "assistant_message": _serialize_message(assistant_msg),
            "conversation": _serialize_conversation(conv, len(conv.messages)),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception:
        logger.exception("Unexpected error in chat route")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{conversation_id}/archive")
async def archive_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Archive a conversation."""
    if db is None:
        return {"id": conversation_id, "status": "archived"}

    try:
        from app.services.conversation_manager import conversation_manager

        conv = await conversation_manager.archive_conversation(db, conversation_id)
        return _serialize_conversation(conv)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception("Unexpected error in chat route")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a conversation."""
    if db is None:
        return {"id": conversation_id, "deleted": True}

    try:
        from app.services.conversation_manager import conversation_manager

        conv = await conversation_manager.delete_conversation(db, conversation_id)
        return {"id": conv.id, "deleted": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception("Unexpected error in chat route")
        raise HTTPException(status_code=500, detail="Internal server error")


async def _mock_stream_tokens(content: str):
    """Yield typed SSE events with small delays for dev mode streaming.

    Event types:
    - ``event: status``  – streaming state changes (started, processing)
    - ``event: data``    – content chunk
    - ``event: error``   – error with code and message
    - ``event: done``    – stream complete, includes full response text
    """
    import json as _json

    yield f"event: status\ndata: {_json.dumps({'status': 'started'})}\n\n"
    await asyncio.sleep(0.02)

    words = content.split()
    for i, word in enumerate(words):
        token = word if i == len(words) - 1 else word + " "
        yield f"event: data\ndata: {_json.dumps({'token': token})}\n\n"
        await asyncio.sleep(0.05)

    yield f"event: done\ndata: {_json.dumps({'full_text': content})}\n\n"


@router.post("/{conversation_id}/stream")
async def stream_message(
    conversation_id: str,
    body: SendMessageRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream an AI response token-by-token via SSE.

    Sends Server-Sent Events where each ``data:`` frame contains a token.
    The final frame is ``data: [DONE]`` to signal completion.
    """
    import json as _json

    if db is None:
        # Dev mode: stream a mock response
        mock_content = (
            f"[Dev mode] I received your message: '{body.content[:100]}'. "
            "Here is a **streaming** mock response with some architectural advice:\n\n"
            "- Consider using **Azure Front Door** for global load balancing\n"
            "- Enable `Azure Policy` for governance guardrails\n"
            "- Use **managed identities** instead of service principal secrets"
        )
        return StreamingResponse(
            _mock_stream_tokens(mock_content),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    try:
        from app.models.base import generate_uuid
        from app.models.conversation import ConversationMessage
        from app.services.ai_foundry import ai_client
        from app.services.conversation_manager import conversation_manager, estimate_tokens
        from app.services.prompts import CHAT_SYSTEM_PROMPT

        # Verify conversation exists and belongs to user
        conv = await conversation_manager.get_conversation(db, conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Store the user message
        user_msg = ConversationMessage(
            id=generate_uuid(),
            conversation_id=conversation_id,
            role="user",
            content=body.content,
            token_count=estimate_tokens(body.content),
        )
        db.add(user_msg)
        await db.flush()

        # Build context for the AI
        context_messages = []
        for msg in conv.messages:
            context_messages.append({"role": msg.role, "content": msg.content})
        context_messages.append({"role": "user", "content": body.content})

        # Build user prompt from context
        user_prompt = "\n".join(
            f"[{m['role']}]: {m['content']}" for m in context_messages if m["role"] != "system"
        )

        async def generate():
            full_response: list[str] = []
            try:
                # Signal that streaming has started
                yield f"event: status\ndata: {_json.dumps({'status': 'started'})}\n\n"

                async for token in ai_client.stream_completion(
                    system_prompt=CHAT_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                ):
                    full_response.append(token)
                    yield f"event: data\ndata: {_json.dumps({'token': token})}\n\n"
            except Exception as e:
                # Send typed error event with code and retry hint
                is_transient = "timeout" in str(e).lower() or "connection" in str(e).lower()
                error_payload = _json.dumps({
                    "code": "STREAM_ERROR",
                    "message": "An error occurred during streaming",
                    "retryable": is_transient,
                })
                logger.exception("Streaming error in conversation %s", conversation_id)
                yield f"event: error\ndata: {error_payload}\n\n"

            # Store the assistant response
            assistant_content = "".join(full_response)
            assistant_msg = ConversationMessage(
                id=generate_uuid(),
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_content,
                token_count=estimate_tokens(assistant_content),
            )
            db.add(assistant_msg)

            # Update conversation token totals
            conv.total_tokens += user_msg.token_count + assistant_msg.token_count
            await db.commit()

            yield f"event: done\ndata: {_json.dumps({'full_text': assistant_content})}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error in chat route")
        raise HTTPException(status_code=500, detail="Internal server error")
