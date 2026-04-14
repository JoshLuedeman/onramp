"""Initial schema — aligned with SQLAlchemy models.

Revision ID: 001
Revises: None
Create Date: 2026-02-12
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Tenants
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("azure_tenant_id", sa.String(36), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("1"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime, server_default=sa.func.now(),
            onupdate=sa.func.now(), nullable=False,
        ),
    )

    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entra_object_id", sa.String(36), unique=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), server_default="viewer"),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("1"), nullable=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime, server_default=sa.func.now(),
            onupdate=sa.func.now(), nullable=False,
        ),
    )

    # Projects
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime, server_default=sa.func.now(),
            onupdate=sa.func.now(), nullable=False,
        ),
    )

    # Question categories
    op.create_table(
        "question_categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("caf_design_area", sa.String(100), nullable=False),
        sa.Column("display_order", sa.Integer, server_default="0"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime, server_default=sa.func.now(),
            onupdate=sa.func.now(), nullable=False,
        ),
    )

    # Questions
    op.create_table(
        "questions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("help_text", sa.Text, nullable=True),
        sa.Column("question_type", sa.String(50), nullable=False),
        sa.Column("options", sa.JSON, nullable=True),
        sa.Column("display_order", sa.Integer, server_default="0"),
        sa.Column("is_required", sa.Boolean, server_default=sa.text("1"), nullable=True),
        sa.Column(
            "category_id", sa.String(36),
            sa.ForeignKey("question_categories.id"), nullable=False,
        ),
        sa.Column(
            "depends_on_question_id", sa.String(36),
            sa.ForeignKey("questions.id"), nullable=True,
        ),
        sa.Column("depends_on_answer", sa.String(255), nullable=True),
        sa.Column("min_org_size", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime, server_default=sa.func.now(),
            onupdate=sa.func.now(), nullable=False,
        ),
    )

    # Questionnaire responses
    op.create_table(
        "questionnaire_responses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("answer_value", sa.Text, nullable=False),
        sa.Column("answer_data", sa.JSON, nullable=True),
        sa.Column(
            "project_id", sa.String(36),
            sa.ForeignKey("projects.id"), nullable=False,
        ),
        sa.Column(
            "question_id", sa.String(36),
            sa.ForeignKey("questions.id"), nullable=False,
        ),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime, server_default=sa.func.now(),
            onupdate=sa.func.now(), nullable=False,
        ),
    )

    # Architectures
    op.create_table(
        "architectures",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("architecture_data", sa.JSON, nullable=False),
        sa.Column("management_groups", sa.JSON, nullable=True),
        sa.Column("subscriptions", sa.JSON, nullable=True),
        sa.Column("network_topology", sa.JSON, nullable=True),
        sa.Column("policies", sa.JSON, nullable=True),
        sa.Column("compliance_frameworks", sa.JSON, nullable=True),
        sa.Column("ai_reasoning", sa.Text, nullable=True),
        sa.Column(
            "project_id", sa.String(36),
            sa.ForeignKey("projects.id"), unique=True, nullable=False,
        ),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime, server_default=sa.func.now(),
            onupdate=sa.func.now(), nullable=False,
        ),
    )

    # Deployments
    op.create_table(
        "deployments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("target_subscription_id", sa.String(36), nullable=False),
        sa.Column("target_subscription_name", sa.String(255), nullable=True),
        sa.Column("bicep_templates", sa.JSON, nullable=True),
        sa.Column("azure_deployment_id", sa.String(255), nullable=True),
        sa.Column("azure_deployment_url", sa.Text, nullable=True),
        sa.Column("deployed_resources", sa.JSON, nullable=True),
        sa.Column("error_details", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column(
            "project_id", sa.String(36),
            sa.ForeignKey("projects.id"), nullable=False,
        ),
        sa.Column(
            "initiated_by", sa.String(36),
            sa.ForeignKey("users.id"), nullable=False,
        ),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime, server_default=sa.func.now(),
            onupdate=sa.func.now(), nullable=False,
        ),
    )

    # Compliance frameworks
    op.create_table(
        "compliance_frameworks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("short_name", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("version", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("1"), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime, server_default=sa.func.now(),
            onupdate=sa.func.now(), nullable=False,
        ),
    )

    # Compliance controls
    op.create_table(
        "compliance_controls",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("control_id", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(255), nullable=True),
        sa.Column("severity", sa.String(50), server_default="medium"),
        sa.Column("azure_policy_definitions", sa.JSON, nullable=True),
        sa.Column(
            "framework_id", sa.String(36),
            sa.ForeignKey("compliance_frameworks.id"), nullable=False,
        ),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime, server_default=sa.func.now(),
            onupdate=sa.func.now(), nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("compliance_controls")
    op.drop_table("compliance_frameworks")
    op.drop_table("deployments")
    op.drop_table("architectures")
    op.drop_table("questionnaire_responses")
    op.drop_table("questions")
    op.drop_table("question_categories")
    op.drop_table("projects")
    op.drop_table("users")
    op.drop_table("tenants")
