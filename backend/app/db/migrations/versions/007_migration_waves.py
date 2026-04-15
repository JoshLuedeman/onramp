"""Add migration wave planning tables.

Revision ID: 007
Revises: 006
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "migration_plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column(
            "name", sa.String(255), nullable=False, server_default="Migration Plan"
        ),
        sa.Column(
            "strategy", sa.String(50), nullable=False, server_default="complexity_first"
        ),
        sa.Column("max_wave_size", sa.Integer, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("notes", sa.Text, nullable=True),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_migration_plans_project_id", "migration_plans", ["project_id"])

    op.create_table(
        "migration_waves",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "plan_id",
            sa.String(36),
            sa.ForeignKey("migration_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("order", sa.Integer, nullable=False),
        sa.Column(
            "status", sa.String(50), nullable=False, server_default="planned"
        ),
        sa.Column("notes", sa.Text, nullable=True),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_migration_waves_plan_id", "migration_waves", ["plan_id"])

    op.create_table(
        "wave_workloads",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "wave_id",
            sa.String(36),
            sa.ForeignKey("migration_waves.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workload_id",
            sa.String(36),
            sa.ForeignKey("workloads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "plan_id",
            sa.String(36),
            sa.ForeignKey("migration_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.UniqueConstraint("workload_id", "plan_id", name="uq_workload_per_plan"),
    )
    op.create_index("ix_wave_workloads_wave_id", "wave_workloads", ["wave_id"])


def downgrade() -> None:
    op.drop_index("ix_wave_workloads_wave_id", table_name="wave_workloads")
    op.drop_table("wave_workloads")
    op.drop_index("ix_migration_waves_plan_id", table_name="migration_waves")
    op.drop_table("migration_waves")
    op.drop_index("ix_migration_plans_project_id", table_name="migration_plans")
    op.drop_table("migration_plans")
