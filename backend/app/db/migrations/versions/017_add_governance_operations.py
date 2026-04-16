"""Add governance operations tables (approvals, audit trail).

Revision ID: 017
Revises: 013
Create Date: 2025-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "017"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Approval requests table ──────────────────────────────────────
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("request_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.Text, nullable=False),
        sa.Column("requested_by", sa.String(255), nullable=False),
        sa.Column("requested_at", sa.DateTime, nullable=False),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("reviewer", sa.String(255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("review_reason", sa.Text, nullable=True),
        sa.Column("details", sa.JSON, nullable=True),
        sa.Column("tenant_id", sa.String(36), nullable=True),
        sa.Column("project_id", sa.String(36), nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=True),
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
        "ix_approval_requests_status_project",
        "approval_requests",
        ["status", "project_id"],
    )
    op.create_index(
        "ix_approval_requests_tenant_status",
        "approval_requests",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_approval_requests_expires",
        "approval_requests",
        ["expires_at"],
    )

    # ── Governance audit entries table ────────────────────────────────
    op.create_table(
        "governance_audit_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(255), nullable=True),
        sa.Column("resource_id", sa.Text, nullable=True),
        sa.Column("actor", sa.String(255), nullable=True),
        sa.Column("details", sa.JSON, nullable=True),
        sa.Column("tenant_id", sa.String(36), nullable=True),
        sa.Column("project_id", sa.String(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_gov_audit_event_type_created",
        "governance_audit_entries",
        ["event_type", "created_at"],
    )
    op.create_index(
        "ix_gov_audit_project_created",
        "governance_audit_entries",
        ["project_id", "created_at"],
    )
    op.create_index(
        "ix_gov_audit_tenant_created",
        "governance_audit_entries",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_gov_audit_actor",
        "governance_audit_entries",
        ["actor"],
    )


def downgrade() -> None:
    # Drop audit entries
    op.drop_index(
        "ix_gov_audit_actor",
        table_name="governance_audit_entries",
    )
    op.drop_index(
        "ix_gov_audit_tenant_created",
        table_name="governance_audit_entries",
    )
    op.drop_index(
        "ix_gov_audit_project_created",
        table_name="governance_audit_entries",
    )
    op.drop_index(
        "ix_gov_audit_event_type_created",
        table_name="governance_audit_entries",
    )
    op.drop_table("governance_audit_entries")

    # Drop approval requests
    op.drop_index(
        "ix_approval_requests_expires",
        table_name="approval_requests",
    )
    op.drop_index(
        "ix_approval_requests_tenant_status",
        table_name="approval_requests",
    )
    op.drop_index(
        "ix_approval_requests_status_project",
        table_name="approval_requests",
    )
    op.drop_table("approval_requests")
