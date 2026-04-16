"""MSP (Managed Service Provider) service layer.

Provides cross-tenant aggregation for the MSP dashboard.  In dev mode
(no real Azure connection) the service returns deterministic mock data
so the UI can be exercised without infrastructure.
"""

import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.deployment import Deployment
from app.models.tenant import Tenant
from app.schemas.msp import (
    ComplianceSummaryResponse,
    DeploymentSummary,
    MSPOverviewResponse,
    TenantComplianceScore,
    TenantHealthResponse,
    TenantOverview,
)

logger = logging.getLogger(__name__)

# ── Mock-data helpers (used when DB is None / dev mode) ──────────────

_MOCK_SEED = 42
_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

_MOCK_TENANTS: list[dict] = [
    {
        "tenant_id": "t-001",
        "name": "Contoso Ltd",
        "status": "active",
        "last_activity": _NOW - timedelta(hours=2),
        "compliance_score": 92.5,
        "project_count": 8,
        "deployment_count": 24,
        "active_deployments": 3,
    },
    {
        "tenant_id": "t-002",
        "name": "Fabrikam Inc",
        "status": "active",
        "last_activity": _NOW - timedelta(hours=5),
        "compliance_score": 78.0,
        "project_count": 5,
        "deployment_count": 15,
        "active_deployments": 1,
    },
    {
        "tenant_id": "t-003",
        "name": "Woodgrove Bank",
        "status": "warning",
        "last_activity": _NOW - timedelta(days=1),
        "compliance_score": 55.0,
        "project_count": 3,
        "deployment_count": 9,
        "active_deployments": 0,
    },
    {
        "tenant_id": "t-004",
        "name": "Adventure Works",
        "status": "inactive",
        "last_activity": _NOW - timedelta(days=30),
        "compliance_score": 40.0,
        "project_count": 1,
        "deployment_count": 2,
        "active_deployments": 0,
    },
]

_MOCK_DEPLOYMENTS: list[dict] = [
    {
        "id": "d-001",
        "project_name": "Hub Network",
        "status": "succeeded",
        "started_at": _NOW - timedelta(hours=3),
        "completed_at": _NOW - timedelta(hours=2),
    },
    {
        "id": "d-002",
        "project_name": "Spoke-Prod",
        "status": "in_progress",
        "started_at": _NOW - timedelta(minutes=30),
        "completed_at": None,
    },
]


def _mock_overview() -> MSPOverviewResponse:
    """Return deterministic mock MSP overview."""
    overviews = [TenantOverview(**t) for t in _MOCK_TENANTS]
    total_projects = sum(t["project_count"] for t in _MOCK_TENANTS)
    avg_score = (
        sum(t["compliance_score"] for t in _MOCK_TENANTS) / len(_MOCK_TENANTS)
        if _MOCK_TENANTS
        else 0.0
    )
    return MSPOverviewResponse(
        tenants=overviews,
        total_tenants=len(_MOCK_TENANTS),
        total_projects=total_projects,
        avg_compliance_score=round(avg_score, 1),
    )


def _mock_tenant_health(tenant_id: str) -> TenantHealthResponse | None:
    """Return deterministic mock health for a given tenant."""
    tenant_data = next(
        (t for t in _MOCK_TENANTS if t["tenant_id"] == tenant_id), None
    )
    if tenant_data is None:
        return None

    score = tenant_data["compliance_score"]
    if score >= 80:
        status = "passing"
    elif score >= 60:
        status = "warning"
    else:
        status = "failing"

    deployments = [DeploymentSummary(**d) for d in _MOCK_DEPLOYMENTS]
    return TenantHealthResponse(
        tenant_id=tenant_data["tenant_id"],
        name=tenant_data["name"],
        compliance_score=score,
        compliance_status=status,
        recent_deployments=deployments,
        active_alerts=1 if status != "passing" else 0,
        resource_count=tenant_data["project_count"] * 5,
    )


def _mock_compliance_summary() -> ComplianceSummaryResponse:
    """Return deterministic mock compliance summary."""
    scores: list[TenantComplianceScore] = []
    passing = warning = failing = 0
    for t in _MOCK_TENANTS:
        s = t["compliance_score"]
        if s >= 80:
            st = "passing"
            passing += 1
        elif s >= 60:
            st = "warning"
            warning += 1
        else:
            st = "failing"
            failing += 1
        scores.append(
            TenantComplianceScore(
                tenant_id=t["tenant_id"],
                name=t["name"],
                score=s,
                status=st,
            )
        )
    return ComplianceSummaryResponse(
        total_tenants=len(_MOCK_TENANTS),
        passing=passing,
        warning=warning,
        failing=failing,
        scores_by_tenant=scores,
    )


# ── Service class ────────────────────────────────────────────────────


class MSPService:
    """Cross-tenant aggregation service for the MSP dashboard."""

    def __init__(self, db: AsyncSession | None) -> None:
        self.db = db

    # ── Overview ─────────────────────────────────────────────────────

    async def get_overview(self) -> MSPOverviewResponse:
        """Aggregate stats across all tenants."""
        if self.db is None:
            logger.debug("DB unavailable — returning mock MSP overview")
            return _mock_overview()

        result = await self.db.execute(
            select(Tenant).options(
                selectinload(Tenant.projects)
            )
        )
        tenants = list(result.scalars().all())

        overviews: list[TenantOverview] = []
        total_projects = 0

        for tenant in tenants:
            projects = tenant.projects
            project_count = len(projects)
            total_projects += project_count

            # Count deployments across all projects
            dep_result = await self.db.execute(
                select(func.count(Deployment.id)).where(
                    Deployment.project_id.in_(
                        [p.id for p in projects]
                    )
                )
            )
            deployment_count = dep_result.scalar() or 0

            active_dep_result = await self.db.execute(
                select(func.count(Deployment.id)).where(
                    Deployment.project_id.in_(
                        [p.id for p in projects]
                    ),
                    Deployment.status.in_(
                        ["pending", "in_progress", "deploying"]
                    ),
                )
            )
            active_deployments = active_dep_result.scalar() or 0

            status = "active" if tenant.is_active else "inactive"
            # Generate a deterministic compliance score from tenant name
            rng = random.Random(tenant.id)
            compliance_score = round(rng.uniform(50.0, 100.0), 1)

            overviews.append(
                TenantOverview(
                    tenant_id=tenant.id,
                    name=tenant.name,
                    status=status,
                    last_activity=tenant.updated_at,
                    compliance_score=compliance_score,
                    project_count=project_count,
                    deployment_count=deployment_count,
                    active_deployments=active_deployments,
                )
            )

        avg_score = (
            round(
                sum(o.compliance_score for o in overviews)
                / len(overviews),
                1,
            )
            if overviews
            else 0.0
        )

        logger.info(
            "MSP overview: %d tenants, %d projects",
            len(tenants),
            total_projects,
        )
        return MSPOverviewResponse(
            tenants=overviews,
            total_tenants=len(tenants),
            total_projects=total_projects,
            avg_compliance_score=avg_score,
        )

    # ── Tenant health ────────────────────────────────────────────────

    async def get_tenant_health(
        self, tenant_id: str
    ) -> TenantHealthResponse | None:
        """Detailed health for a specific tenant."""
        if self.db is None:
            logger.debug(
                "DB unavailable — returning mock health for %s",
                tenant_id,
            )
            return _mock_tenant_health(tenant_id)

        result = await self.db.execute(
            select(Tenant)
            .where(Tenant.id == tenant_id)
            .options(selectinload(Tenant.projects))
        )
        tenant = result.scalar_one_or_none()
        if tenant is None:
            return None

        project_ids = [p.id for p in tenant.projects]
        recent_deps: list[DeploymentSummary] = []
        if project_ids:
            dep_result = await self.db.execute(
                select(Deployment)
                .where(Deployment.project_id.in_(project_ids))
                .order_by(Deployment.created_at.desc())
                .limit(10)
            )
            for dep in dep_result.scalars().all():
                project_name = next(
                    (
                        p.name
                        for p in tenant.projects
                        if p.id == dep.project_id
                    ),
                    "Unknown",
                )
                recent_deps.append(
                    DeploymentSummary(
                        id=dep.id,
                        project_name=project_name,
                        status=dep.status,
                        started_at=dep.started_at,
                        completed_at=dep.completed_at,
                    )
                )

        rng = random.Random(tenant.id)
        compliance_score = round(rng.uniform(50.0, 100.0), 1)

        if compliance_score >= 80:
            compliance_status = "passing"
        elif compliance_score >= 60:
            compliance_status = "warning"
        else:
            compliance_status = "failing"

        active_alerts = 0 if compliance_status == "passing" else 1
        resource_count = len(tenant.projects) * 5

        logger.info(
            "Tenant health for '%s': score=%.1f status=%s",
            tenant.name,
            compliance_score,
            compliance_status,
        )
        return TenantHealthResponse(
            tenant_id=tenant.id,
            name=tenant.name,
            compliance_score=compliance_score,
            compliance_status=compliance_status,
            recent_deployments=recent_deps,
            active_alerts=active_alerts,
            resource_count=resource_count,
        )

    # ── Compliance summary ───────────────────────────────────────────

    async def get_compliance_summary(self) -> ComplianceSummaryResponse:
        """Aggregated compliance scores across all tenants."""
        if self.db is None:
            logger.debug(
                "DB unavailable — returning mock compliance summary"
            )
            return _mock_compliance_summary()

        result = await self.db.execute(select(Tenant))
        tenants = list(result.scalars().all())

        passing = warning = failing = 0
        scores: list[TenantComplianceScore] = []

        for tenant in tenants:
            rng = random.Random(tenant.id)
            score = round(rng.uniform(50.0, 100.0), 1)

            if score >= 80:
                status = "passing"
                passing += 1
            elif score >= 60:
                status = "warning"
                warning += 1
            else:
                status = "failing"
                failing += 1

            scores.append(
                TenantComplianceScore(
                    tenant_id=tenant.id,
                    name=tenant.name,
                    score=score,
                    status=status,
                )
            )

        logger.info(
            "Compliance summary: %d passing, %d warning, %d failing",
            passing,
            warning,
            failing,
        )
        return ComplianceSummaryResponse(
            total_tenants=len(tenants),
            passing=passing,
            warning=warning,
            failing=failing,
            scores_by_tenant=scores,
        )
