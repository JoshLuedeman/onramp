"""Add notification tables.

Revision ID: 010
Revises: 007
Create Date: 2025-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: str | None = ("008", "009")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=True
        ),
        sa.Column(
            "project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=True
        ),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("notification_type", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("message", sa.String(2000), nullable=False),
        sa.Column(
            "severity", sa.String(20), nullable=False, server_default="info"
        ),
        sa.Column(
            "channel", sa.String(20), nullable=False, server_default="in_app"
        ),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="pending"
        ),
        sa.Column("delivery_metadata", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("delivered_at", sa.DateTime, nullable=True),
        sa.Column("read_at", sa.DateTime, nullable=True),
    )
    op.create_index(
        "ix_notifications_user_status_created",
        "notifications",
        ["user_id", "status", "created_at"],
    )
    op.create_index(
        "ix_notifications_tenant_type",
        "notifications",
        ["tenant_id", "notification_type"],
    )

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=True
        ),
        sa.Column("notification_type", sa.String(100), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column(
            "enabled", sa.Boolean, nullable=False, server_default=sa.text("1")
        ),
        sa.Column("config", sa.JSON, nullable=True),
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
        sa.UniqueConstraint(
            "user_id",
            "notification_type",
            "channel",
            name="uq_user_notif_type_channel",
        ),
    )


def downgrade() -> None:
    op.drop_table("notification_preferences")
    op.drop_index(
        "ix_notifications_tenant_type", table_name="notifications"
    )
    op.drop_index(
        "ix_notifications_user_status_created", table_name="notifications"
    )
    op.drop_table("notifications")
