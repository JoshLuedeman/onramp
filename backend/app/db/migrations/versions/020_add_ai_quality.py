"""Add AI quality infrastructure tables.

Revision ID: 020
Revises: 14ff8537f1ee
Create Date: 2026-04-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "020"
down_revision: str | None = "14ff8537f1ee"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # prompt_versions
    # ------------------------------------------------------------------
    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("template", sa.Text, nullable=False),
        sa.Column("metadata_json", sa.JSON, nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("1"),
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
        "ix_prompt_versions_name",
        "prompt_versions",
        ["name"],
    )

    # ------------------------------------------------------------------
    # ai_feedback
    # ------------------------------------------------------------------
    op.create_table(
        "ai_feedback",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("feature", sa.String(100), nullable=False),
        sa.Column("output_id", sa.String(255), nullable=False),
        sa.Column("rating", sa.String(20), nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("prompt_version", sa.String(100), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_ai_feedback_feature_created",
        "ai_feedback",
        ["feature", "created_at"],
    )
    op.create_index(
        "ix_ai_feedback_user_created",
        "ai_feedback",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_ai_feedback_tenant_feature",
        "ai_feedback",
        ["tenant_id", "feature"],
    )

    # ------------------------------------------------------------------
    # token_usage
    # ------------------------------------------------------------------
    op.create_table(
        "token_usage",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("feature", sa.String(100), nullable=False),
        sa.Column(
            "prompt_tokens",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "completion_tokens",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "total_tokens",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(100), nullable=False),
        sa.Column("cost_estimate", sa.Float, nullable=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_token_usage_feature_created",
        "token_usage",
        ["feature", "created_at"],
    )
    op.create_index(
        "ix_token_usage_user_created",
        "token_usage",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_token_usage_tenant_feature",
        "token_usage",
        ["tenant_id", "feature"],
    )


def downgrade() -> None:
    op.drop_index("ix_token_usage_tenant_feature", table_name="token_usage")
    op.drop_index("ix_token_usage_user_created", table_name="token_usage")
    op.drop_index("ix_token_usage_feature_created", table_name="token_usage")
    op.drop_table("token_usage")

    op.drop_index("ix_ai_feedback_tenant_feature", table_name="ai_feedback")
    op.drop_index("ix_ai_feedback_user_created", table_name="ai_feedback")
    op.drop_index("ix_ai_feedback_feature_created", table_name="ai_feedback")
    op.drop_table("ai_feedback")

    op.drop_index("ix_prompt_versions_name", table_name="prompt_versions")
    op.drop_table("prompt_versions")
