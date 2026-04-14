"""Add audit_entries table for tracking changes and deployment events.

Revision ID: 003
Revises: 002
Create Date: 2026-07-14
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "tenant_id", sa.String(36),
            sa.ForeignKey("tenants.id"), nullable=True,
        ),
        sa.Column(
            "project_id", sa.String(36),
            sa.ForeignKey("projects.id"), nullable=True,
        ),
        sa.Column("deployment_id", sa.String(36), nullable=True),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column(
            "actor_user_id", sa.String(36),
            sa.ForeignKey("users.id"), nullable=True,
        ),
        sa.Column("actor_identifier", sa.String(255), nullable=True),
        sa.Column("details", sa.JSON, nullable=True),
        sa.Column("old_values", sa.JSON, nullable=True),
        sa.Column("new_values", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    op.create_index(
        "ix_audit_entity_time",
        "audit_entries",
        ["entity_type", "entity_id", "created_at"],
    )
    op.create_index(
        "ix_audit_project_time",
        "audit_entries",
        ["project_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_project_time", table_name="audit_entries")
    op.drop_index("ix_audit_entity_time", table_name="audit_entries")
    op.drop_table("audit_entries")
