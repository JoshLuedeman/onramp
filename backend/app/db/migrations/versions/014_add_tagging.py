"""Add tagging compliance tables.

Revision ID: 014
Revises: 010
Create Date: 2025-07-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "014"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tagging_policies",
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
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("required_tags", sa.JSON, nullable=False),
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
        "ix_tagging_policies_project",
        "tagging_policies",
        ["project_id"],
    )

    op.create_table(
        "tagging_scan_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column(
            "policy_id",
            sa.String(36),
            sa.ForeignKey("tagging_policies.id"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id"),
            nullable=True,
        ),
        sa.Column(
            "total_resources",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "compliant_count",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "non_compliant_count",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "compliance_percentage",
            sa.Float,
            nullable=False,
            server_default=sa.text("0.0"),
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
    )
    op.create_index(
        "ix_tagging_scan_results_project_timestamp",
        "tagging_scan_results",
        ["project_id", "scan_timestamp"],
    )

    op.create_table(
        "tagging_violations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "scan_result_id",
            sa.String(36),
            sa.ForeignKey("tagging_scan_results.id"),
            nullable=False,
        ),
        sa.Column("resource_id", sa.Text, nullable=False),
        sa.Column("resource_type", sa.String(255), nullable=False),
        sa.Column("resource_name", sa.String(255), nullable=True),
        sa.Column("violation_type", sa.String(50), nullable=False),
        sa.Column("tag_name", sa.String(255), nullable=False),
        sa.Column("expected_value", sa.Text, nullable=True),
        sa.Column("actual_value", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_tagging_violations_scan_result",
        "tagging_violations",
        ["scan_result_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tagging_violations_scan_result",
        table_name="tagging_violations",
    )
    op.drop_table("tagging_violations")
    op.drop_index(
        "ix_tagging_scan_results_project_timestamp",
        table_name="tagging_scan_results",
    )
    op.drop_table("tagging_scan_results")
    op.drop_index(
        "ix_tagging_policies_project",
        table_name="tagging_policies",
    )
    op.drop_table("tagging_policies")
