"""update device unique constraint

Revision ID: 0004012a6927
Revises: fefbf485f3dc
Create Date: 2025-07-26 18:25:08.015694

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import core


# revision identifiers, used by Alembic.
revision: str = "0004012a6927"
down_revision: Union[str, Sequence[str], None] = "fefbf485f3dc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_devices_device_token"), table_name="devices")
    op.create_unique_constraint(
        "uq_device_token_user_id", "devices", ["device_token", "user_id"]
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint("uq_device_token_user_id", "devices", type_="unique")
    op.create_index(
        op.f("ix_devices_device_token"), "devices", ["device_token"], unique=True
    )
    # ### end Alembic commands ###
