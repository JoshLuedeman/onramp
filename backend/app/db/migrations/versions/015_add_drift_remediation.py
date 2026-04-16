"""Add drift remediation table.

Revision ID: 015
Revises: 014
Create Date: 2025-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "015"
down_revision: str | None = "014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "drift_remediations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "finding_id",
            sa.String(36),
            sa.ForeignKey("drift_events.id"),
            nullable=False,
        ),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("justification", sa.Text, nullable=True),
        sa.Column("expiration_days", sa.Integer, nullable=True),
        sa.Column("result_details", sa.JSON, nullable=False, server_default="{}"),
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
        "ix_drift_remediations_finding", "drift_remediations", ["finding_id"]
    )
    op.create_index(
        "ix_drift_remediations_status", "drift_remediations", ["status"]
    )
    op.create_index(
        "ix_drift_remediations_actor_created",
        "drift_remediations",
        ["actor", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_drift_remediations_actor_created", table_name="drift_remediations")
    op.drop_index("ix_drift_remediations_status", table_name="drift_remediations")
    op.drop_index("ix_drift_remediations_finding", table_name="drift_remediations")
    op.drop_table("drift_remediations")
