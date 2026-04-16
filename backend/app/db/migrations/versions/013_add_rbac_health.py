"""Add RBAC health monitoring tables.

Revision ID: 013
Revises: 011
Create Date: 2025-07-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: str | None = ("011", "012", "014")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rbac_scan_results",
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
        sa.Column("health_score", sa.Float, nullable=False, server_default="100.0"),
        sa.Column(
            "total_assignments",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "finding_count",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("scan_timestamp", sa.DateTime, nullable=False),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="completed",
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
        "ix_rbac_scan_results_project_scan",
        "rbac_scan_results",
        ["project_id", "scan_timestamp"],
    )

    op.create_table(
        "rbac_findings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "scan_result_id",
            sa.String(36),
            sa.ForeignKey("rbac_scan_results.id"),
            nullable=False,
        ),
        sa.Column("finding_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("principal_id", sa.String(255), nullable=False),
        sa.Column("principal_name", sa.String(255), nullable=True),
        sa.Column("role_name", sa.String(255), nullable=False),
        sa.Column("scope", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("remediation", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_rbac_findings_result_severity",
        "rbac_findings",
        ["scan_result_id", "severity"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rbac_findings_result_severity",
        table_name="rbac_findings",
    )
    op.drop_table("rbac_findings")
    op.drop_index(
        "ix_rbac_scan_results_project_scan",
        table_name="rbac_scan_results",
    )
    op.drop_table("rbac_scan_results")
