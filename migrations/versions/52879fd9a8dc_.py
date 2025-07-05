"""empty message

Revision ID: 52879fd9a8dc
Revises:
Create Date: 2025-07-05 08:32:32.212631
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import core

# revision identifiers, used by Alembic.
revision: str = "52879fd9a8dc"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(sa.text("CREATE SEQUENCE report_number_seq START 1000"))


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(sa.text("DROP SEQUENCE IF EXISTS report_number_seq"))
