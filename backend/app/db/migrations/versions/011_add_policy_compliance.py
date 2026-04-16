"""Add policy compliance monitoring tables.

Revision ID: 011
Revises: 010
Create Date: 2025-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "policy_compliance_results",
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
        sa.Column("scan_timestamp", sa.DateTime, nullable=False),
        sa.Column(
            "total_resources", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column(
            "compliant_count", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column(
            "non_compliant_count",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="completed",
        ),
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
            nullable=False,
        ),
    )
    op.create_index(
        "ix_policy_compliance_results_project_scan",
        "policy_compliance_results",
        ["project_id", "scan_timestamp"],
    )

    op.create_table(
        "policy_violations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "compliance_result_id",
            sa.String(36),
            sa.ForeignKey("policy_compliance_results.id"),
            nullable=False,
        ),
        sa.Column("resource_id", sa.String(500), nullable=False),
        sa.Column("resource_type", sa.String(255), nullable=False),
        sa.Column("policy_name", sa.String(255), nullable=False),
        sa.Column("policy_description", sa.Text, nullable=True),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column(
            "framework_control_id",
            sa.String(36),
            sa.ForeignKey("compliance_controls.id"),
            nullable=True,
        ),
        sa.Column("remediation_suggestion", sa.Text, nullable=True),
        sa.Column("detected_at", sa.DateTime, nullable=False),
    )
    op.create_index(
        "ix_policy_violations_result_severity",
        "policy_violations",
        ["compliance_result_id", "severity"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_policy_violations_result_severity",
        table_name="policy_violations",
    )
    op.drop_table("policy_violations")
    op.drop_index(
        "ix_policy_compliance_results_project_scan",
        table_name="policy_compliance_results",
    )
    op.drop_table("policy_compliance_results")
