"""merge heads

Revision ID: 9ef76bfb9c9c
Revises: 5e7b0a963dd1, c232349b0ad4
Create Date: 2025-10-20 11:17:09.567358

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from avcfastapi.core.database.sqlalchamey import core


# revision identifiers, used by Alembic.
revision: str = "9ef76bfb9c9c"
down_revision: Union[str, Sequence[str], None] = ("5e7b0a963dd1", "c232349b0ad4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
