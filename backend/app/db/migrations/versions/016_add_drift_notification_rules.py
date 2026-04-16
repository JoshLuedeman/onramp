"""Add drift notification rules table.

Revision ID: 016
Revises: 014
Create Date: 2025-07-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "016"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "drift_notification_rules",
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
        sa.Column(
            "severity_threshold",
            sa.String(20),
            nullable=False,
            server_default="high",
        ),
        sa.Column("channels", sa.JSON, nullable=False),
        sa.Column("recipients", sa.JSON, nullable=False),
        sa.Column(
            "enabled",
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_drift_notif_rules_project",
        "drift_notification_rules",
        ["project_id"],
    )
    op.create_index(
        "ix_drift_notif_rules_tenant",
        "drift_notification_rules",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_drift_notif_rules_tenant",
        table_name="drift_notification_rules",
    )
    op.drop_index(
        "ix_drift_notif_rules_project",
        table_name="drift_notification_rules",
    )
    op.drop_table("drift_notification_rules")
