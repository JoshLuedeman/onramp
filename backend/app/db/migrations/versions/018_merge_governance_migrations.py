"""Merge governance migrations

Revision ID: 14ff8537f1ee
Revises: 015, 016, 017
Create Date: 2026-04-16 13:54:04.103527
"""
from collections.abc import Sequence

# revision identifiers
revision: str = '14ff8537f1ee'
down_revision: tuple[str, ...] = ('015', '016', '017')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
