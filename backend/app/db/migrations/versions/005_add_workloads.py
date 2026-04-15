"""Add workloads table.

Revision ID: 005
Revises: 004
Create Date: 2026-07-21
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workloads",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), nullable=False, server_default="other"),
        sa.Column("source_platform", sa.String(50), nullable=False, server_default="other"),
        sa.Column("cpu_cores", sa.Integer, nullable=True),
        sa.Column("memory_gb", sa.Float, nullable=True),
        sa.Column("storage_gb", sa.Float, nullable=True),
        sa.Column("os_type", sa.String(100), nullable=True),
        sa.Column("os_version", sa.String(100), nullable=True),
        sa.Column("criticality", sa.String(50), nullable=False, server_default="standard"),
        sa.Column("compliance_requirements", sa.JSON, nullable=True),
        sa.Column("dependencies", sa.JSON, nullable=True),
        sa.Column("migration_strategy", sa.String(50), nullable=False, server_default="unknown"),
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
    op.create_index("ix_workloads_project_id", "workloads", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_workloads_project_id", table_name="workloads")
    op.drop_table("workloads")
