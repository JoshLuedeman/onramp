"""Conversation manager — multi-turn AI chat state management."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.base import generate_uuid

logger = logging.getLogger(__name__)

# Rough token estimation: ~4 chars per token for English text
CHARS_PER_TOKEN = 4
DEFAULT_MAX_TOKENS = 8000
SYSTEM_PROMPT = (
    "You are OnRamp AI, an Azure landing-zone architect assistant. "
    "Help users design, evaluate, and deploy secure cloud infrastructure. "
    "Be concise, specific, and reference Azure best practices."
)


def estimate_tokens(text: str) -> int:
    """Rough token estimate based on character count."""
    return max(1, len(text) // CHARS_PER_TOKEN)


class ConversationManager:
    """Manages persistent conversation state for multi-turn AI chat."""

    # ── Create ───────────────────────────────────────────────────────

    async def create_conversation(
        self,
        db: AsyncSession,
        project_id: str,
        user_id: str,
        tenant_id: str,
        title: str | None = None,
    ):
        """Create a new conversation and seed it with a system prompt."""
        from app.models.conversation import Conversation, ConversationMessage

        model_name = settings.ai_foundry_model if hasattr(settings, "ai_foundry_model") else "gpt-4o"

        conversation = Conversation(
            id=generate_uuid(),
            title=title or "New conversation",
            project_id=project_id,
            user_id=user_id,
            tenant_id=tenant_id,
            status="active",
            model_name=model_name,
            total_tokens=0,
        )
        db.add(conversation)
        await db.flush()

        # Seed with system prompt
        system_msg = ConversationMessage(
            id=generate_uuid(),
            conversation_id=conversation.id,
            role="system",
            content=SYSTEM_PROMPT,
            token_count=estimate_tokens(SYSTEM_PROMPT),
        )
        db.add(system_msg)
        conversation.total_tokens = system_msg.token_count
        await db.flush()

        return conversation

    # ── Read ─────────────────────────────────────────────────────────

    async def get_conversation(self, db: AsyncSession, conversation_id: str):
        """Get a conversation with all its messages."""
        from app.models.conversation import Conversation

        result = await db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
            .where(Conversation.status != "deleted")
        )
        return result.scalars().first()

    async def list_conversations(
        self,
        db: AsyncSession,
        project_id: str,
        user_id: str,
    ) -> list:
        """List non-deleted conversations for a project/user pair."""
        from app.models.conversation import Conversation, ConversationMessage

        # Subquery for message counts
        msg_count = (
            select(
                ConversationMessage.conversation_id,
                func.count(ConversationMessage.id).label("message_count"),
            )
            .group_by(ConversationMessage.conversation_id)
            .subquery()
        )

        result = await db.execute(
            select(Conversation, msg_count.c.message_count)
            .outerjoin(msg_count, Conversation.id == msg_count.c.conversation_id)
            .where(Conversation.project_id == project_id)
            .where(Conversation.user_id == user_id)
            .where(Conversation.status != "deleted")
            .order_by(Conversation.created_at.desc())
        )
        rows = result.all()
        return [
            {"conversation": row[0], "message_count": row[1] or 0}
            for row in rows
        ]

    # ── Send Message (core multi-turn logic) ─────────────────────────

    async def send_message(
        self,
        db: AsyncSession,
        conversation_id: str,
        content: str,
        user_id: str,
    ):
        """Send a user message and get an AI response.

        1. Load conversation + history
        2. Content safety check (prompt injection defense)
        3. Rate limit check
        4. Append user message
        5. Apply context window management
        6. Call AI (or mock in dev mode)
        7. Store assistant response
        8. Update token totals
        """
        from app.models.conversation import ConversationMessage

        # 1. Load conversation
        conversation = await self.get_conversation(db, conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")
        if conversation.status != "active":
            raise ValueError(f"Conversation {conversation_id} is {conversation.status}")
        if conversation.user_id != user_id:
            raise PermissionError("Not your conversation")

        # 2. Content safety — check for prompt injection
        from app.services.content_safety import content_safety_service

        safety_result = content_safety_service.check_input(content)
        if not safety_result.safe:
            content_safety_service.log_security_event(
                "chat_input_blocked",
                user_id=user_id,
                details={
                    "conversation_id": conversation_id,
                    "patterns": safety_result.flagged_patterns,
                    "risk_level": safety_result.risk_level,
                },
            )
            # Store user message so context isn't lost, but return safety msg
            user_tokens = estimate_tokens(content)
            user_msg = ConversationMessage(
                id=generate_uuid(),
                conversation_id=conversation_id,
                role="user",
                content=content,
                token_count=user_tokens,
            )
            db.add(user_msg)

            safety_text = (
                "I'm unable to process that request because it was flagged "
                "by our content safety system. Please rephrase your question "
                "about Azure architecture or cloud infrastructure."
            )
            assistant_msg = ConversationMessage(
                id=generate_uuid(),
                conversation_id=conversation_id,
                role="assistant",
                content=safety_text,
                token_count=estimate_tokens(safety_text),
            )
            db.add(assistant_msg)
            conversation.total_tokens += user_tokens + assistant_msg.token_count
            await db.flush()
            return assistant_msg, conversation

        # 3. Rate limit check
        tenant_id = getattr(conversation, "tenant_id", None)
        if not content_safety_service.check_rate_limit(user_id, tenant_id):
            raise ValueError("AI rate limit exceeded. Please try again later.")

        # 4. Store user message
        user_tokens = estimate_tokens(content)
        user_msg = ConversationMessage(
            id=generate_uuid(),
            conversation_id=conversation_id,
            role="user",
            content=content,
            token_count=user_tokens,
        )
        db.add(user_msg)
        await db.flush()

        # 5. Build context-managed message history
        messages = self._build_context_window(conversation.messages + [user_msg])

        # 6. Get AI response
        assistant_content = await self._get_ai_response(messages)
        assistant_tokens = estimate_tokens(assistant_content)

        # 7. Store assistant response
        assistant_msg = ConversationMessage(
            id=generate_uuid(),
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
            token_count=assistant_tokens,
        )
        db.add(assistant_msg)

        # 8. Update token totals
        conversation.total_tokens += user_tokens + assistant_tokens
        await db.flush()

        return assistant_msg, conversation

    # ── Archive / Delete ─────────────────────────────────────────────

    async def archive_conversation(self, db: AsyncSession, conversation_id: str):
        """Mark a conversation as archived."""
        from app.models.conversation import Conversation

        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalars().first()
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")
        conversation.status = "archived"
        await db.flush()
        return conversation

    async def delete_conversation(self, db: AsyncSession, conversation_id: str):
        """Soft-delete a conversation."""
        from app.models.conversation import Conversation

        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalars().first()
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")
        conversation.status = "deleted"
        await db.flush()
        return conversation

    # ── Cleanup ──────────────────────────────────────────────────────

    async def cleanup_stale(self, db: AsyncSession, max_age_days: int = 30) -> int:
        """Delete conversations older than max_age_days that are archived or deleted."""
        from app.models.conversation import Conversation, ConversationMessage

        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

        # Find stale conversation IDs
        result = await db.execute(
            select(Conversation.id).where(
                Conversation.updated_at < cutoff,
                Conversation.status.in_(["archived", "deleted"]),
            )
        )
        stale_ids = [row[0] for row in result.all()]

        if not stale_ids:
            return 0

        # Delete messages first (FK constraint)
        await db.execute(
            delete(ConversationMessage).where(
                ConversationMessage.conversation_id.in_(stale_ids)
            )
        )
        # Delete conversations
        await db.execute(
            delete(Conversation).where(Conversation.id.in_(stale_ids))
        )
        await db.flush()

        logger.info(f"Cleaned up {len(stale_ids)} stale conversations")
        return len(stale_ids)

    # ── Context Window Management ────────────────────────────────────

    def _build_context_window(
        self, messages, max_tokens: int = DEFAULT_MAX_TOKENS
    ) -> list[dict]:
        """Build a message list that fits within the token budget.

        Strategy:
        - Always keep the system prompt (first message)
        - Keep the latest user message (last message)
        - Fill remaining budget from most recent to oldest
        - If history is too long, drop oldest non-system messages
        """
        if not messages:
            return []

        formatted = []
        for msg in messages:
            role = msg.role if hasattr(msg, "role") else msg.get("role", "user")
            content = msg.content if hasattr(msg, "content") else msg.get("content", "")
            token_count = (
                msg.token_count
                if hasattr(msg, "token_count") and msg.token_count
                else estimate_tokens(content)
            )
            formatted.append(
                {"role": role, "content": content, "tokens": token_count}
            )

        # Always include system prompt if present
        system_msgs = [m for m in formatted if m["role"] == "system"]
        non_system = [m for m in formatted if m["role"] != "system"]

        budget = max_tokens
        result = []

        # Reserve tokens for system prompt
        for sm in system_msgs:
            budget -= sm["tokens"]
            result.append({"role": sm["role"], "content": sm["content"]})

        # Fill from most recent backwards
        selected = []
        for msg in reversed(non_system):
            if budget - msg["tokens"] >= 0:
                budget -= msg["tokens"]
                selected.append({"role": msg["role"], "content": msg["content"]})
            else:
                break  # No more room

        # Restore chronological order
        selected.reverse()
        result.extend(selected)

        return result

    # ── AI Integration ───────────────────────────────────────────────

    async def _get_ai_response(self, messages: list[dict]) -> str:
        """Get AI response for the conversation history.

        Uses the real AI client when configured, otherwise returns mock responses.
        """
        from app.services.ai_foundry import ai_client

        if not ai_client.is_configured:
            return self._mock_ai_response(messages)

        try:
            # Extract system and user content for the existing generate_completion_async API
            system_content = ""
            user_content = ""
            for msg in messages:
                if msg["role"] == "system":
                    system_content = msg["content"]
                elif msg["role"] == "user":
                    user_content = msg["content"]

            # For multi-turn, combine full history into the user prompt
            # so the AI has conversational context
            history_parts = []
            for msg in messages:
                if msg["role"] != "system":
                    history_parts.append(f"{msg['role'].upper()}: {msg['content']}")
            combined_user = "\n\n".join(history_parts) if history_parts else user_content

            response = await ai_client.generate_completion_async(
                system_prompt=system_content or SYSTEM_PROMPT,
                user_prompt=combined_user,
                temperature=0.7,
                max_tokens=2048,
            )
            return response
        except Exception as e:
            logger.error(f"AI response failed, using mock: {e}")
            return self._mock_ai_response(messages)

    def _mock_ai_response(self, messages: list[dict]) -> str:
        """Generate a mock AI response for dev mode."""
        # Find the last user message
        user_content = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_content = msg["content"]
                break

        user_lower = user_content.lower()

        if "architecture" in user_lower or "landing zone" in user_lower:
            return (
                "For your Azure landing zone, I recommend a hub-spoke network topology "
                "with centralized security controls. Key components include: "
                "1) Hub VNet with Azure Firewall and Bastion, "
                "2) Spoke VNets for workloads with NSGs, "
                "3) Azure Policy for governance, and "
                "4) Microsoft Defender for Cloud for security monitoring."
            )
        if "compliance" in user_lower or "security" in user_lower:
            return (
                "To ensure compliance, consider implementing: "
                "1) Azure Policy for resource governance, "
                "2) Microsoft Defender for Cloud for security posture management, "
                "3) Azure Monitor for logging and alerting, and "
                "4) Regular compliance assessments against CIS benchmarks."
            )
        if "cost" in user_lower or "budget" in user_lower:
            return (
                "For cost optimization, I recommend: "
                "1) Right-sizing VMs based on actual utilization, "
                "2) Using Reserved Instances for predictable workloads, "
                "3) Setting up Azure Cost Management budgets and alerts, and "
                "4) Implementing auto-scaling for variable workloads."
            )
        if "deploy" in user_lower or "bicep" in user_lower:
            return (
                "For deployment, I recommend using Bicep templates with: "
                "1) Modular template structure (main.bicep + modules/), "
                "2) Parameter files per environment, "
                "3) CI/CD pipeline with what-if validation, and "
                "4) Staged rollout across environments."
            )

        return (
            f"I understand you're asking about: {user_content[:100]}. "
            "As your Azure landing zone assistant, I can help with architecture design, "
            "compliance evaluation, cost optimization, and deployment planning. "
            "Could you provide more details about your specific requirements?"
        )


# Singleton
conversation_manager = ConversationManager()
