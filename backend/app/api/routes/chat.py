"""Chat API routes for multi-turn AI conversations."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_db
from app.schemas.conversation import (
    ConversationCreate,
    SendMessageRequest,
)

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


@router.post("/new")
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
