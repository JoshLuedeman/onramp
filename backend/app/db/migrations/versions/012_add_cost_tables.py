"""Add cost management tables.

Revision ID: 012
Revises: 010
Create Date: 2025-07-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "012"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cost_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id"),
            nullable=True,
        ),
        sa.Column("subscription_id", sa.String(255), nullable=False),
        sa.Column("period_start", sa.DateTime, nullable=False),
        sa.Column("period_end", sa.DateTime, nullable=False),
        sa.Column("total_cost", sa.Float, nullable=False),
        sa.Column(
            "currency", sa.String(10), nullable=False, server_default="USD"
        ),
        sa.Column("cost_by_service", sa.JSON, nullable=True),
        sa.Column("cost_by_resource_group", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_cost_snapshots_project_created",
        "cost_snapshots",
        ["project_id", "created_at"],
    )

    op.create_table(
        "cost_budgets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id"),
            nullable=True,
        ),
        sa.Column("budget_name", sa.String(255), nullable=False),
        sa.Column("budget_amount", sa.Float, nullable=False),
        sa.Column(
            "current_spend", sa.Float, nullable=False, server_default=sa.text("0.0")
        ),
        sa.Column(
            "currency", sa.String(10), nullable=False, server_default="USD"
        ),
        sa.Column(
            "threshold_percentage",
            sa.Float,
            nullable=False,
            server_default=sa.text("80.0"),
        ),
        sa.Column(
            "alert_enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_cost_budgets_project_created",
        "cost_budgets",
        ["project_id", "created_at"],
    )

    op.create_table(
        "cost_anomalies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column(
            "cost_snapshot_id",
            sa.String(36),
            sa.ForeignKey("cost_snapshots.id"),
            nullable=False,
        ),
        sa.Column("anomaly_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("previous_cost", sa.Float, nullable=False),
        sa.Column("current_cost", sa.Float, nullable=False),
        sa.Column("percentage_change", sa.Float, nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("detected_at", sa.DateTime, nullable=False),
    )
    op.create_index(
        "ix_cost_anomalies_project_detected",
        "cost_anomalies",
        ["project_id", "detected_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cost_anomalies_project_detected", table_name="cost_anomalies"
    )
    op.drop_table("cost_anomalies")
    op.drop_index(
        "ix_cost_budgets_project_created", table_name="cost_budgets"
    )
    op.drop_table("cost_budgets")
    op.drop_index(
        "ix_cost_snapshots_project_created", table_name="cost_snapshots"
    )
    op.drop_table("cost_snapshots")
