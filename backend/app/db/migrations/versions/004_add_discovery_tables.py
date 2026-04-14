"""Add discovery_scans and discovered_resources tables.

Revision ID: 004
Revises: 003
Create Date: 2026-07-21
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discovery_scans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id", sa.String(36),
            sa.ForeignKey("projects.id"), nullable=False,
        ),
        sa.Column(
            "tenant_id", sa.String(36),
            sa.ForeignKey("tenants.id"), nullable=False,
        ),
        sa.Column("subscription_id", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), default="pending"),
        sa.Column("scan_config", sa.JSON, nullable=True),
        sa.Column("results", sa.JSON, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime,
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime,
            server_default=sa.func.now(), nullable=False,
        ),
    )

    op.create_table(
        "discovered_resources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "scan_id", sa.String(36),
            sa.ForeignKey("discovery_scans.id"), nullable=False,
        ),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(255), nullable=False),
        sa.Column("resource_id", sa.Text, nullable=False),
        sa.Column("resource_group", sa.String(255), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("properties", sa.JSON, nullable=True),
        sa.Column(
            "created_at", sa.DateTime,
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime,
            server_default=sa.func.now(), nullable=False,
        ),
    )

    op.create_index(
        "ix_discovery_scans_project",
        "discovery_scans",
        ["project_id", "created_at"],
    )
    op.create_index(
        "ix_discovered_resources_scan",
        "discovered_resources",
        ["scan_id", "category"],
    )


def downgrade() -> None:
    op.drop_index("ix_discovered_resources_scan", table_name="discovered_resources")
    op.drop_index("ix_discovery_scans_project", table_name="discovery_scans")
    op.drop_table("discovered_resources")
    op.drop_table("discovery_scans")
