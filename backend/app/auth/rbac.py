"""Role-based access control middleware."""


from fastapi import Depends, HTTPException, status

from app.auth.entra import get_current_user


class RoleChecker:
    """Dependency that checks if the user has the required role."""

    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    async def __call__(self, user: dict = Depends(get_current_user)) -> dict:
        if not user.get("roles"):
            user["roles"] = ["viewer"]

        if not any(role in self.allowed_roles for role in user.get("roles", [])):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {self.allowed_roles}",
            )
        return user


# Pre-configured role checkers
require_admin = RoleChecker(["admin"])
require_architect = RoleChecker(["admin", "architect"])
require_viewer = RoleChecker(["admin", "architect", "viewer"])
require_msp_admin = RoleChecker(["admin", "msp_admin"])
