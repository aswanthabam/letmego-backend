"""update vehicle schema

Revision ID: ecca7a75d6f4
Revises: cc811b5fd36c
Create Date: 2025-07-03 10:26:52.562173

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import core


# revision identifiers, used by Alembic.
revision: str = "ecca7a75d6f4"
down_revision: Union[str, Sequence[str], None] = "cc811b5fd36c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the enum type first
    vehicletype_enum = sa.Enum(
        "CAR",
        "MOTORCYCLE",
        "TRUCK",
        "BUS",
        "VAN",
        "SUV",
        "PICKUP_TRUCK",
        "SCOOTER",
        "BICYCLE",
        "TRAILER",
        "RICKSHAW",
        "AUTO_RICKSHAW",
        "TRACTOR",
        "AMBULANCE",
        "FIRE_TRUCK",
        "POLICE_VEHICLE",
        "TAXI",
        "OTHER",
        name="vehicletype",
    )
    vehicletype_enum.create(op.get_bind())

    # Add columns
    op.add_column(
        "users", sa.Column("company_name", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "vehicles", sa.Column("vehicle_type", vehicletype_enum, nullable=True)
    )
    op.add_column("vehicles", sa.Column("brand", sa.String(length=50), nullable=True))
    op.add_column(
        "vehicles",
        sa.Column("image", core.storage.fields.S3ImageField(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop columns first
    op.drop_column("vehicles", "image")
    op.drop_column("vehicles", "brand")
    op.drop_column("vehicles", "vehicle_type")
    op.drop_column("users", "company_name")

    # Drop the enum type
    vehicletype_enum = sa.Enum(name="vehicletype")
    vehicletype_enum.drop(op.get_bind())
