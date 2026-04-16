"""Collaboration service — manages project members, comments, and activity.

Provides a singleton service with async methods for all collaboration
operations including member management, commenting, and activity feeds.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.base import generate_uuid

logger = logging.getLogger(__name__)

# Role hierarchy: owner > editor > viewer
ROLE_HIERARCHY = {"owner": 3, "editor": 2, "viewer": 1}


class CollaborationService:
    """Singleton service for project collaboration features."""

    # ──────────────────────────────────────────────────────────────────
    # Members
    # ──────────────────────────────────────────────────────────────────

    async def add_member(
        self,
        db: Any | None,
        project_id: str,
        email: str,
        role: str = "viewer",
    ) -> dict:
        """Invite a user to a project by email."""
        now = datetime.now(timezone.utc)

        if role not in ROLE_HIERARCHY:
            raise ValueError(f"Invalid role: {role}")

        if db is not None:
            from sqlalchemy import select

            from app.models.comment import Comment  # noqa: F401
            from app.models.project_member import ProjectMember
            from app.models.user import User

            # Find user by email
            result = await db.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            if user is None:
                raise ValueError(f"User not found: {email}")

            # Check for duplicate membership
            existing = await db.execute(
                select(ProjectMember).where(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user.id,
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise ValueError(
                    f"User {email} is already a member of this project"
                )

            member = ProjectMember(
                id=generate_uuid(),
                project_id=project_id,
                user_id=user.id,
                role=role,
                invited_at=now,
            )
            db.add(member)
            await db.flush()
            await db.refresh(member)

            logger.info(
                "Member added: project=%s user=%s role=%s",
                project_id, user.id, role,
            )
            return {
                "id": member.id,
                "user_id": member.user_id,
                "email": user.email,
                "display_name": user.display_name,
                "role": member.role,
                "invited_at": member.invited_at,
                "accepted_at": member.accepted_at,
            }

        # Dev mode — return mock data
        mock_id = generate_uuid()
        logger.info(
            "Member added (mock): project=%s email=%s role=%s",
            project_id, email, role,
        )
        return {
            "id": mock_id,
            "user_id": generate_uuid(),
            "email": email,
            "display_name": email.split("@")[0],
            "role": role,
            "invited_at": now,
            "accepted_at": None,
        }

    async def list_members(
        self,
        db: Any | None,
        project_id: str,
    ) -> dict:
        """List all members of a project."""
        if db is not None:
            from sqlalchemy import select
            from sqlalchemy.orm import joinedload

            from app.models.project_member import ProjectMember

            result = await db.execute(
                select(ProjectMember)
                .options(joinedload(ProjectMember.user))
                .where(ProjectMember.project_id == project_id)
                .order_by(ProjectMember.invited_at)
            )
            rows = result.unique().scalars().all()
            members = [
                {
                    "id": m.id,
                    "user_id": m.user_id,
                    "email": m.user.email if m.user else "",
                    "display_name": (
                        m.user.display_name if m.user else ""
                    ),
                    "role": m.role,
                    "invited_at": m.invited_at,
                    "accepted_at": m.accepted_at,
                }
                for m in rows
            ]
            return {"members": members, "total": len(members)}

        return {"members": [], "total": 0}

    async def remove_member(
        self,
        db: Any | None,
        project_id: str,
        user_id: str,
    ) -> bool:
        """Remove a member from a project."""
        if db is not None:
            from sqlalchemy import select

            from app.models.project_member import ProjectMember

            result = await db.execute(
                select(ProjectMember).where(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user_id,
                )
            )
            member = result.scalar_one_or_none()
            if member is None:
                return False

            await db.delete(member)
            await db.flush()
            logger.info(
                "Member removed: project=%s user=%s",
                project_id, user_id,
            )
            return True

        logger.info(
            "Member removed (mock): project=%s user=%s",
            project_id, user_id,
        )
        return True

    async def check_project_access(
        self,
        db: Any | None,
        project_id: str,
        user_id: str,
        required_role: str = "viewer",
    ) -> bool:
        """Check if a user has at least the required role on a project."""
        required_level = ROLE_HIERARCHY.get(required_role, 0)

        if db is not None:
            from sqlalchemy import select

            from app.models.project import Project
            from app.models.project_member import ProjectMember

            # Project creator always has owner-level access
            proj_result = await db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = proj_result.scalar_one_or_none()
            if project and project.created_by == user_id:
                return True

            result = await db.execute(
                select(ProjectMember).where(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user_id,
                )
            )
            member = result.scalar_one_or_none()
            if member is None:
                return False

            user_level = ROLE_HIERARCHY.get(member.role, 0)
            return user_level >= required_level

        # Dev mode — always allow
        return True

    # ──────────────────────────────────────────────────────────────────
    # Comments
    # ──────────────────────────────────────────────────────────────────

    async def add_comment(
        self,
        db: Any | None,
        project_id: str,
        user_id: str,
        content: str,
        component_ref: str | None = None,
    ) -> dict:
        """Add a comment to a project."""
        now = datetime.now(timezone.utc)

        if db is not None:
            from app.models.comment import Comment

            comment = Comment(
                id=generate_uuid(),
                project_id=project_id,
                user_id=user_id,
                content=content,
                component_ref=component_ref,
            )
            db.add(comment)
            await db.flush()
            await db.refresh(comment)

            logger.info(
                "Comment added: project=%s user=%s",
                project_id, user_id,
            )
            return {
                "id": comment.id,
                "content": comment.content,
                "component_ref": comment.component_ref,
                "user_id": comment.user_id,
                "display_name": "",
                "created_at": comment.created_at,
            }

        # Dev mode mock
        mock_id = generate_uuid()
        return {
            "id": mock_id,
            "content": content,
            "component_ref": component_ref,
            "user_id": user_id,
            "display_name": "Dev User",
            "created_at": now,
        }

    async def list_comments(
        self,
        db: Any | None,
        project_id: str,
        component_ref: str | None = None,
    ) -> dict:
        """List comments for a project, optionally filtered by component."""
        if db is not None:
            from sqlalchemy import select
            from sqlalchemy.orm import joinedload

            from app.models.comment import Comment

            stmt = (
                select(Comment)
                .options(joinedload(Comment.user))
                .where(Comment.project_id == project_id)
                .order_by(Comment.created_at.desc())
            )
            if component_ref is not None:
                stmt = stmt.where(
                    Comment.component_ref == component_ref
                )

            result = await db.execute(stmt)
            rows = result.unique().scalars().all()
            comments = [
                {
                    "id": c.id,
                    "content": c.content,
                    "component_ref": c.component_ref,
                    "user_id": c.user_id,
                    "display_name": (
                        c.user.display_name if c.user else ""
                    ),
                    "created_at": c.created_at,
                }
                for c in rows
            ]
            return {"comments": comments, "total": len(comments)}

        return {"comments": [], "total": 0}

    # ──────────────────────────────────────────────────────────────────
    # Activity Feed
    # ──────────────────────────────────────────────────────────────────

    async def get_activity_feed(
        self,
        db: Any | None,
        project_id: str,
        limit: int = 50,
    ) -> dict:
        """Build an activity feed from members and comments."""
        activities: list[dict] = []

        if db is not None:
            from sqlalchemy import select
            from sqlalchemy.orm import joinedload

            from app.models.comment import Comment
            from app.models.project_member import ProjectMember

            # Gather member join events
            members_result = await db.execute(
                select(ProjectMember)
                .options(joinedload(ProjectMember.user))
                .where(ProjectMember.project_id == project_id)
                .order_by(ProjectMember.invited_at.desc())
                .limit(limit)
            )
            for m in members_result.unique().scalars().all():
                name = m.user.display_name if m.user else "Unknown"
                activities.append({
                    "type": "member_joined",
                    "user_id": m.user_id,
                    "description": (
                        f"{name} joined as {m.role}"
                    ),
                    "timestamp": m.invited_at,
                })

            # Gather comment events
            comments_result = await db.execute(
                select(Comment)
                .options(joinedload(Comment.user))
                .where(Comment.project_id == project_id)
                .order_by(Comment.created_at.desc())
                .limit(limit)
            )
            for c in comments_result.unique().scalars().all():
                name = c.user.display_name if c.user else "Unknown"
                ref_text = (
                    f" on {c.component_ref}" if c.component_ref else ""
                )
                activities.append({
                    "type": "comment_added",
                    "user_id": c.user_id,
                    "description": (
                        f"{name} commented{ref_text}"
                    ),
                    "timestamp": c.created_at,
                })

        # Sort by timestamp descending and limit
        activities.sort(key=lambda a: a["timestamp"], reverse=True)
        return {"activities": activities[:limit]}


# Singleton
collaboration_service = CollaborationService()
