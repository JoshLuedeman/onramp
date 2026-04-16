"""Project-level RBAC service — combines global and project membership roles."""

import logging
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.entra import get_current_user
from app.db.session import get_db
from app.models.project_member import ProjectMember
from app.models.user import User

logger = logging.getLogger(__name__)

# Highest index = most privileged.  admin is a global-only role.
ROLE_HIERARCHY: dict[str, int] = {
    "viewer": 0,
    "contributor": 1,
    "reviewer": 2,
    "editor": 3,       # legacy synonym kept for back-compat
    "owner": 4,
    "admin": 5,
}


class ProjectRBACService:
    """Singleton service for project-level permission checks."""

    # ------------------------------------------------------------------
    # Core helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _role_rank(role: str) -> int:
        return ROLE_HIERARCHY.get(role, -1)

    async def get_effective_role(
        self,
        db: AsyncSession,
        project_id: str,
        user_id: str,
    ) -> str | None:
        """Return the highest role a user holds on a project.

        Precedence: global admin > project-level membership role.
        Returns ``None`` when the user has no access at all.
        """
        # 1. Check the global role on the User row
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user_row = result.scalar_one_or_none()
        global_role = user_row.role if user_row else None

        if global_role == "admin":
            return "admin"

        # 2. Check project-level membership
        result = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        membership = result.scalar_one_or_none()
        project_role = membership.role if membership else None

        # Return whichever role ranks higher
        if global_role and project_role:
            if self._role_rank(global_role) >= self._role_rank(project_role):
                return global_role
            return project_role
        return project_role or global_role

    async def check_project_permission(
        self,
        db: AsyncSession,
        project_id: str,
        user_id: str,
        required_role: str,
    ) -> bool:
        """Return True when the user meets or exceeds *required_role*."""
        effective = await self.get_effective_role(db, project_id, user_id)
        if effective is None:
            return False
        return self._role_rank(effective) >= self._role_rank(required_role)

    # ------------------------------------------------------------------
    # FastAPI dependency factory
    # ------------------------------------------------------------------

    @staticmethod
    def require_project_role(required_role: str) -> Callable:
        """Return a FastAPI dependency that enforces *required_role*.

        Usage::

            @router.get("/projects/{project_id}/secret")
            async def secret(
                project_id: str,
                user=Depends(project_rbac.require_project_role("owner")),
            ):
                ...
        """

        async def _checker(
            project_id: str,
            user: dict = Depends(get_current_user),
            db: AsyncSession = Depends(get_db),
        ) -> dict:
            if db is None:
                # Dev mode — allow everything
                return user

            user_id = user.get("sub", "")
            svc = ProjectRBACService()
            allowed = await svc.check_project_permission(
                db, project_id, user_id, required_role,
            )
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"Project role '{required_role}' or higher required"
                    ),
                )
            return user

        return _checker


# Module-level singleton
project_rbac = ProjectRBACService()
