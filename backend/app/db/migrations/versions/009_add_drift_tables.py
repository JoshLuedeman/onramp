"""Add drift detection tables.

Revision ID: 009
Revises: 007
Create Date: 2026-07-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "drift_baselines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column("architecture_version", sa.Integer, nullable=True),
        sa.Column("baseline_data", sa.JSON, nullable=False),
        sa.Column(
            "status", sa.String(50), nullable=False, server_default="active"
        ),
        sa.Column("captured_by", sa.String(255), nullable=True),
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
        "ix_drift_baselines_project_status",
        "drift_baselines",
        ["project_id", "status"],
    )

    op.create_table(
        "drift_scan_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "baseline_id",
            sa.String(36),
            sa.ForeignKey("drift_baselines.id"),
            nullable=False,
        ),
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
        sa.Column("scan_started_at", sa.DateTime, nullable=False),
        sa.Column("scan_completed_at", sa.DateTime, nullable=True),
        sa.Column(
            "total_resources_scanned",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "drifted_count",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "new_count",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "removed_count",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "status", sa.String(50), nullable=False, server_default="running"
        ),
        sa.Column("error_message", sa.Text, nullable=True),
    )
    op.create_index(
        "ix_drift_scan_results_project_started",
        "drift_scan_results",
        ["project_id", "scan_started_at"],
    )

    op.create_table(
        "drift_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "baseline_id",
            sa.String(36),
            sa.ForeignKey("drift_baselines.id"),
            nullable=False,
        ),
        sa.Column(
            "scan_result_id",
            sa.String(36),
            sa.ForeignKey("drift_scan_results.id"),
            nullable=True,
        ),
        sa.Column("resource_type", sa.String(255), nullable=False),
        sa.Column("resource_id", sa.Text, nullable=False),
        sa.Column("drift_type", sa.String(50), nullable=False),
        sa.Column("expected_value", sa.JSON, nullable=True),
        sa.Column("actual_value", sa.JSON, nullable=True),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("detected_at", sa.DateTime, nullable=False),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
        sa.Column("resolution_type", sa.String(100), nullable=True),
    )
    op.create_index(
        "ix_drift_events_baseline_severity",
        "drift_events",
        ["baseline_id", "severity"],
    )
    op.create_index(
        "ix_drift_events_resource_detected",
        "drift_events",
        ["resource_type", "detected_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_drift_events_resource_detected", table_name="drift_events"
    )
    op.drop_index(
        "ix_drift_events_baseline_severity", table_name="drift_events"
    )
    op.drop_table("drift_events")
    op.drop_index(
        "ix_drift_scan_results_project_started",
        table_name="drift_scan_results",
    )
    op.drop_table("drift_scan_results")
    op.drop_index(
        "ix_drift_baselines_project_status", table_name="drift_baselines"
    )
    op.drop_table("drift_baselines")
