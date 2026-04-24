"""Replace single unique on entra_object_id with compound (tenant_id, entra_object_id)

Revision ID: 023
Revises: 022
Create Date: 2025-07-25 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "023"
down_revision: str = "022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Use naming_convention so batch mode can locate the auto-generated
    # unique constraint created by column-level unique=True in SQLite.
    naming = {"uq": "%(table_name)s_%(column_0_name)s_key"}
    with op.batch_alter_table(
        "users", schema=None, naming_convention=naming
    ) as batch_op:
        batch_op.drop_constraint(
            "users_entra_object_id_key", type_="unique"
        )
        batch_op.create_unique_constraint(
            "uq_user_tenant_entra", ["tenant_id", "entra_object_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint("uq_user_tenant_entra", type_="unique")
        batch_op.create_unique_constraint(
            "users_entra_object_id_key", ["entra_object_id"]
        )
