"""Initial schema.

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
        sa.Column("azure_tenant_id", sa.String(36), unique=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id")),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255)),
        sa.Column("role", sa.String(50), server_default="viewer"),
        sa.Column("azure_oid", sa.String(36)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Projects
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Question categories
    op.create_table(
        "question_categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("order", sa.Integer, server_default="0"),
    )

    # Questions
    op.create_table(
        "questions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("question_categories.id")),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("question_type", sa.String(50), nullable=False),
        sa.Column("options", sa.JSON),
        sa.Column("required", sa.Boolean, server_default="1"),
        sa.Column("order", sa.Integer, server_default="0"),
        sa.Column("conditions", sa.JSON),
    )

    # Questionnaire responses
    op.create_table(
        "questionnaire_responses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id")),
        sa.Column("answers", sa.JSON, nullable=False),
        sa.Column("completed", sa.Boolean, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Architectures
    op.create_table(
        "architectures",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id")),
        sa.Column("archetype", sa.String(50)),
        sa.Column("definition", sa.JSON, nullable=False),
        sa.Column("ai_generated", sa.Boolean, server_default="0"),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Deployments
    op.create_table(
        "deployments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id")),
        sa.Column("architecture_id", sa.String(36), sa.ForeignKey("architectures.id")),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("subscription_ids", sa.JSON),
        sa.Column("deployment_data", sa.JSON),
        sa.Column("started_at", sa.DateTime),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Compliance frameworks
    op.create_table(
        "compliance_frameworks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text),
        sa.Column("version", sa.String(20)),
    )

    # Compliance controls
    op.create_table(
        "compliance_controls",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("framework_id", sa.String(36), sa.ForeignKey("compliance_frameworks.id")),
        sa.Column("control_id", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("category", sa.String(100)),
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
