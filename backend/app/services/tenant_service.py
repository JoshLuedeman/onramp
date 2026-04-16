"""Tenant CRUD service layer."""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate

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
