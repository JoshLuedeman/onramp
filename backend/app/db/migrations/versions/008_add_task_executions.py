"""Add task_executions table for governance background tasks.

Revision ID: 008
Revises: 007
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "task_executions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "task_type", sa.String(100), nullable=False
        ),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id"),
            nullable=True,
        ),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("result_summary", sa.JSON, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
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
        "ix_task_executions_task_type",
        "task_executions",
        ["task_type"],
    )
    op.create_index(
        "ix_task_executions_tenant_id",
        "task_executions",
        ["tenant_id"],
    )
    op.create_index(
        "ix_task_executions_project_id",
        "task_executions",
        ["project_id"],
    )
    op.create_index(
        "ix_task_executions_status",
        "task_executions",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_task_executions_status",
        table_name="task_executions",
    )
    op.drop_index(
        "ix_task_executions_project_id",
        table_name="task_executions",
    )
    op.drop_index(
        "ix_task_executions_tenant_id",
        table_name="task_executions",
    )
    op.drop_index(
        "ix_task_executions_task_type",
        table_name="task_executions",
    )
    op.drop_table("task_executions")
