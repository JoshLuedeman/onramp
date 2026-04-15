"""Add workload mapping fields.

Revision ID: 006
Revises: 005
Create Date: 2026-07-21
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "workloads",
        sa.Column("target_subscription_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "workloads",
        sa.Column("mapping_reasoning", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workloads", "mapping_reasoning")
    op.drop_column("workloads", "target_subscription_id")
