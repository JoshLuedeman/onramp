"""Cost management API routes — cost visibility, budgets, and anomalies."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db.session import get_db
from app.schemas.cost import (
    BudgetStatusResponse,
    CostAnomalyList,
    CostBudgetCreate,
    CostScanResponse,
    CostSummaryResponse,
    CostTrendResponse,
)
from app.services.cost_manager import cost_manager

router = APIRouter(prefix="/api/governance/cost", tags=["cost"])


# ── Cost summary ─────────────────────────────────────────────────────────────


@router.get("/summary/{project_id}", response_model=CostSummaryResponse)
async def get_cost_summary(
    project_id: str,
    subscription_id: str = Query("dev-subscription", description="Azure subscription ID"),
    time_range: str = Query("last_30_days", description="Time range for cost data"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get cost summary for a project — total, by service, by resource group."""
    result = await cost_manager.get_cost_summary(
        project_id, subscription_id, time_range
    )
    return result


# ── Cost trend ───────────────────────────────────────────────────────────────


@router.get("/trend/{project_id}", response_model=CostTrendResponse)
async def get_cost_trend(
    project_id: str,
    subscription_id: str = Query("dev-subscription", description="Azure subscription ID"),
    granularity: str = Query("daily", description="Data granularity: daily, weekly, monthly"),
    days: int = Query(30, description="Number of days of trend data", ge=1, le=365),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get cost trend data over time."""
    result = await cost_manager.get_cost_trend(
        project_id, subscription_id, granularity, days
    )
    return result


# ── Budget ───────────────────────────────────────────────────────────────────


@router.get("/budget/{project_id}", response_model=BudgetStatusResponse)
async def get_budget_status(
    project_id: str,
    subscription_id: str = Query("dev-subscription", description="Azure subscription ID"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get budget vs actual spend for a project."""
    if db is not None:
        from app.models.cost import CostBudget

        result = await db.execute(
            select(CostBudget)
            .where(CostBudget.project_id == project_id)
            .order_by(CostBudget.created_at.desc())
        )
        budget = result.scalar_one_or_none()
        if budget is not None:
            utilization = round(
                (budget.current_spend / budget.budget_amount) * 100, 1
            ) if budget.budget_amount > 0 else 0.0
            return BudgetStatusResponse(
                project_id=project_id,
                budget_name=budget.budget_name,
                budget_amount=budget.budget_amount,
                current_spend=budget.current_spend,
                currency=budget.currency,
                utilization_percentage=utilization,
                threshold_percentage=budget.threshold_percentage,
                alert_enabled=budget.alert_enabled,
                is_over_threshold=utilization >= budget.threshold_percentage,
                is_over_budget=utilization >= 100.0,
            )

    # Fallback to cost manager mock/API
    data = await cost_manager.get_budget_status(project_id, subscription_id)
    return data


@router.post("/budget", response_model=BudgetStatusResponse)
async def create_or_update_budget(
    payload: CostBudgetCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update a cost budget."""

    if db is None:
        # No DB — return a mock response
        utilization = round(
            (0.0 / payload.budget_amount) * 100, 1
        ) if payload.budget_amount > 0 else 0.0
        return BudgetStatusResponse(
            project_id=payload.project_id,
            budget_name=payload.budget_name,
            budget_amount=payload.budget_amount,
            current_spend=0.0,
            currency=payload.currency,
            utilization_percentage=utilization,
            threshold_percentage=payload.threshold_percentage,
            alert_enabled=payload.alert_enabled,
            is_over_threshold=False,
            is_over_budget=False,
        )

    from app.models.cost import CostBudget

    # Check for existing budget for this project
    result = await db.execute(
        select(CostBudget).where(CostBudget.project_id == payload.project_id)
    )
    existing = result.scalar_one_or_none()

    if existing is not None:
        existing.budget_name = payload.budget_name
        existing.budget_amount = payload.budget_amount
        existing.currency = payload.currency
        existing.threshold_percentage = payload.threshold_percentage
        existing.alert_enabled = payload.alert_enabled
        await db.flush()
        await db.refresh(existing)
        budget = existing
    else:
        budget = CostBudget(
            project_id=payload.project_id,
            budget_name=payload.budget_name,
            budget_amount=payload.budget_amount,
            currency=payload.currency,
            threshold_percentage=payload.threshold_percentage,
            alert_enabled=payload.alert_enabled,
        )
        db.add(budget)
        await db.flush()
        await db.refresh(budget)

    utilization = round(
        (budget.current_spend / budget.budget_amount) * 100, 1
    ) if budget.budget_amount > 0 else 0.0

    return BudgetStatusResponse(
        project_id=budget.project_id,
        budget_name=budget.budget_name,
        budget_amount=budget.budget_amount,
        current_spend=budget.current_spend,
        currency=budget.currency,
        utilization_percentage=utilization,
        threshold_percentage=budget.threshold_percentage,
        alert_enabled=budget.alert_enabled,
        is_over_threshold=utilization >= budget.threshold_percentage,
        is_over_budget=utilization >= 100.0,
    )


# ── Anomalies ────────────────────────────────────────────────────────────────


@router.get("/anomalies/{project_id}", response_model=CostAnomalyList)
async def list_anomalies(
    project_id: str,
    subscription_id: str = Query("dev-subscription", description="Azure subscription ID"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List cost anomalies for a project."""
    if db is not None:
        from app.models.cost import CostAnomaly

        result = await db.execute(
            select(CostAnomaly)
            .where(CostAnomaly.project_id == project_id)
            .order_by(CostAnomaly.detected_at.desc())
        )
        anomalies = result.scalars().all()
        return CostAnomalyList(anomalies=anomalies, total=len(anomalies))

    # Fallback to cost manager mock/API
    data = await cost_manager.check_cost_anomalies(project_id, subscription_id)
    return data


# ── Scan trigger ─────────────────────────────────────────────────────────────


@router.post("/scan/{project_id}", response_model=CostScanResponse)
async def trigger_cost_scan(
    project_id: str,
    subscription_id: str = Query("dev-subscription", description="Azure subscription ID"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a cost analysis scan for a project."""
    # Clear cached data to force fresh fetch
    cost_manager.clear_cache()

    scan_id = str(uuid.uuid4())

    # Run cost summary + anomaly check
    await cost_manager.get_cost_summary(project_id, subscription_id)
    anomaly_result = await cost_manager.check_cost_anomalies(
        project_id, subscription_id
    )

    anomaly_count = anomaly_result.get("total", 0)
    message = (
        f"Cost scan completed. Found {anomaly_count} anomalie(s)."
        if anomaly_count
        else "Cost scan completed. No anomalies detected."
    )

    return CostScanResponse(
        status="completed",
        message=message,
        project_id=project_id,
        scan_id=scan_id,
    )
