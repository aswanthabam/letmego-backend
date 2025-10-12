"""Merge add_new_features_2024 and vehicle location heads.

Revision ID: c232349b0ad4
Revises: 7a1c02aafb60, add_new_features_2024
Create Date: 2025-10-12 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "c232349b0ad4"
down_revision: Union[str, Sequence[str], None] = ("7a1c02aafb60", "add_new_features_2024")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op merge upgrade."""
    pass


def downgrade() -> None:
    """No-op merge downgrade."""
    pass

