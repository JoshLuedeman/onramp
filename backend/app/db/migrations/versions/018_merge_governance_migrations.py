"""Merge governance migrations

Revision ID: 14ff8537f1ee
Revises: 015, 016, 017
Create Date: 2026-04-16 13:54:04.103527
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers
revision: str = '14ff8537f1ee'
down_revision: Union[str, None] = ('015', '016', '017')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
