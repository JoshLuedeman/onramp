"""Tenant CRUD + lifecycle service layer."""

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate
from app.schemas.tenant_lifecycle import (
    ResourceLimits,
    TenantOffboardResponse,
    TenantProvisionRequest,
    TenantSettingsResponse,
    TenantSettingsUpdate,
)

logger = logging.getLogger(__name__)


class TenantService:
    """Service encapsulating all tenant CRUD operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_tenant(self, data: TenantCreate) -> Tenant:
        """Create a new tenant.

        Args:
            data: Validated tenant creation payload.

        Returns:
            The newly created :class:`Tenant` instance.
        """
        tenant = Tenant(
            name=data.name,
            azure_tenant_id=data.azure_tenant_id,
            is_active=True,
        )
        self.db.add(tenant)
        await self.db.flush()
        logger.info("Created tenant '%s' (id=%s)", tenant.name, tenant.id)
        return tenant

    async def get_tenant(self, tenant_id: str) -> Tenant | None:
        """Fetch a single tenant by primary key.

        Args:
            tenant_id: UUID of the tenant.

        Returns:
            The :class:`Tenant` instance, or ``None`` if not found.
        """
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def list_tenants(
        self, skip: int = 0, limit: int = 50
    ) -> tuple[list[Tenant], int]:
        """List tenants with pagination.

        Args:
            skip: Number of rows to skip.
            limit: Maximum rows to return.

        Returns:
            A tuple of ``(tenants, total_count)``.
        """
        count_result = await self.db.execute(select(func.count(Tenant.id)))
        total = count_result.scalar() or 0

        result = await self.db.execute(
            select(Tenant).offset(skip).limit(limit).order_by(Tenant.created_at)
        )
        tenants = list(result.scalars().all())
        return tenants, total

    async def update_tenant(
        self, tenant_id: str, data: TenantUpdate
    ) -> Tenant | None:
        """Update a tenant's mutable fields.

        Args:
            tenant_id: UUID of the tenant to update.
            data: Validated update payload (only set fields are applied).

        Returns:
            The updated :class:`Tenant`, or ``None`` if the tenant was not
            found.
        """
        tenant = await self.get_tenant(tenant_id)
        if tenant is None:
            return None

        if data.name is not None:
            tenant.name = data.name
        if data.is_active is not None:
            tenant.is_active = data.is_active

        await self.db.flush()
        await self.db.refresh(tenant)
        logger.info("Updated tenant '%s' (id=%s)", tenant.name, tenant.id)
        return tenant

    async def deactivate_tenant(self, tenant_id: str) -> Tenant | None:
        """Soft-delete a tenant by setting ``is_active`` to ``False``.

        Args:
            tenant_id: UUID of the tenant to deactivate.

        Returns:
            The deactivated :class:`Tenant`, or ``None`` if not found.
        """
        tenant = await self.get_tenant(tenant_id)
        if tenant is None:
            return None

        tenant.is_active = False
        await self.db.flush()
        await self.db.refresh(tenant)
        logger.info("Deactivated tenant '%s' (id=%s)", tenant.name, tenant.id)
        return tenant

    async def get_or_create_default(self) -> Tenant:
        """Return the default tenant, creating it if it does not exist.

        This is used in dev mode so that routes always have a valid tenant
        context.

        Returns:
            The default :class:`Tenant` instance.
        """
        result = await self.db.execute(
            select(Tenant).where(Tenant.name == "Default")
        )
        tenant = result.scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(name="Default", is_active=True)
            self.db.add(tenant)
            await self.db.flush()
            logger.info("Auto-created default tenant (id=%s)", tenant.id)
        return tenant

    # ------------------------------------------------------------------
    # Lifecycle operations
    # ------------------------------------------------------------------

    # In-memory store for settings/limits (until dedicated table exists)
    _settings_store: dict[str, dict] = {}

    async def provision_tenant(
        self, data: TenantProvisionRequest,
    ) -> TenantSettingsResponse:
        """Provision a new tenant with resource limits and admin invite."""
        tenant = Tenant(name=data.name, is_active=True)
        self.db.add(tenant)
        await self.db.flush()

        limits = data.resource_limits
        self.__class__._settings_store[tenant.id] = {
            "resource_limits": limits.model_dump(),
            "feature_flags": {},
            "admin_email": data.admin_email,
        }

        logger.info(
            "Provisioned tenant '%s' (id=%s) for %s",
            tenant.name, tenant.id, data.admin_email,
        )

        return TenantSettingsResponse(
            tenant_id=tenant.id,
            name=tenant.name,
            is_active=tenant.is_active,
            resource_limits=limits,
            feature_flags={},
            created_at=tenant.created_at or datetime.now(timezone.utc),
        )

    async def get_tenant_settings(
        self, tenant_id: str,
    ) -> TenantSettingsResponse | None:
        """Return tenant settings including resource limits."""
        tenant = await self.get_tenant(tenant_id)
        if tenant is None:
            return None

        stored = self.__class__._settings_store.get(tenant_id, {})
        limits_data = stored.get(
            "resource_limits",
            ResourceLimits().model_dump(),
        )
        flags = stored.get("feature_flags", {})

        return TenantSettingsResponse(
            tenant_id=tenant.id,
            name=tenant.name,
            is_active=tenant.is_active,
            resource_limits=ResourceLimits(**limits_data),
            feature_flags=flags,
            created_at=tenant.created_at or datetime.now(timezone.utc),
        )

    async def update_tenant_settings(
        self,
        tenant_id: str,
        data: TenantSettingsUpdate,
    ) -> TenantSettingsResponse | None:
        """Update resource limits and/or feature flags."""
        tenant = await self.get_tenant(tenant_id)
        if tenant is None:
            return None

        stored = self.__class__._settings_store.setdefault(
            tenant_id, {
                "resource_limits": ResourceLimits().model_dump(),
                "feature_flags": {},
            },
        )

        if data.resource_limits is not None:
            stored["resource_limits"] = data.resource_limits.model_dump()
        if data.feature_flags is not None:
            stored["feature_flags"] = data.feature_flags

        await self.db.flush()
        await self.db.refresh(tenant)

        return TenantSettingsResponse(
            tenant_id=tenant.id,
            name=tenant.name,
            is_active=tenant.is_active,
            resource_limits=ResourceLimits(**stored["resource_limits"]),
            feature_flags=stored["feature_flags"],
            created_at=tenant.created_at or datetime.now(timezone.utc),
        )

    async def offboard_tenant(
        self,
        tenant_id: str,
        *,
        archive: bool = True,
        retention_days: int = 90,
    ) -> TenantOffboardResponse | None:
        """Deactivate a tenant and mark for archival."""
        tenant = await self.get_tenant(tenant_id)
        if tenant is None:
            return None

        tenant.is_active = False
        await self.db.flush()
        await self.db.refresh(tenant)

        logger.info(
            "Offboarded tenant '%s' (id=%s, archive=%s, retention=%dd)",
            tenant.name, tenant.id, archive, retention_days,
        )

        return TenantOffboardResponse(
            tenant_id=tenant.id,
            is_active=tenant.is_active,
            archive=archive,
            retention_days=retention_days,
            message=(
                f"Tenant '{tenant.name}' deactivated. "
                f"Data {'will be' if archive else 'will NOT be'} archived "
                f"with {retention_days}-day retention."
            ),
        )
