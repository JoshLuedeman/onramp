"""Add Phase 20 enterprise tables

Revision ID: 022
Revises: aa1cfc956e67
Create Date: 2026-04-16 22:15:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "022"
down_revision: str = "aa1cfc956e67"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Architecture versions
    op.create_table(
        "architecture_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("architecture_id", sa.String(36), sa.ForeignKey("architectures.id")),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("architecture_json", sa.Text, nullable=False),
        sa.Column("change_summary", sa.String(500), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_table(
        "templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("tags", sa.Text, nullable=True),
        sa.Column("architecture_json", sa.Text, nullable=False),
        sa.Column("author_tenant_id", sa.String(36), nullable=True),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="private"),
        sa.Column("download_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("rating_up", sa.Integer, nullable=False, server_default="0"),
        sa.Column("rating_down", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Project members
    op.create_table(
        "project_members",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id")),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("invited_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("accepted_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "user_id"),
    )

    # Comments
    op.create_table(
        "comments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id")),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("component_ref", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Architecture reviews
    op.create_table(
        "architecture_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "architecture_id", sa.String(36), sa.ForeignKey("architectures.id")
        ),
        sa.Column("reviewer_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("comments", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Review configurations
    op.create_table(
        "review_configurations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id")),
        sa.Column(
            "required_approvals", sa.Integer, nullable=False, server_default="1"
        ),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Enterprise audit events
    op.create_table(
        "enterprise_audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("tenant_id", sa.String(36), nullable=True),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("details", sa.Text, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("timestamp", sa.DateTime, server_default=sa.func.now()),
    )

    # Add review_status to architectures
    op.add_column(
        "architectures",
        sa.Column("review_status", sa.String(20), server_default="draft"),
    )


def downgrade() -> None:
    op.drop_column("architectures", "review_status")
    op.drop_table("enterprise_audit_events")
    op.drop_table("review_configurations")
    op.drop_table("architecture_reviews")
    op.drop_table("comments")
    op.drop_table("project_members")
    op.drop_table("templates")
    op.drop_table("architecture_versions")
