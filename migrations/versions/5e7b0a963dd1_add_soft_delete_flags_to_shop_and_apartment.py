"""Add soft delete flags to new domain tables

Revision ID: 5e7b0a963dd1
Revises: add_new_features_2024
Create Date: 2025-10-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5e7b0a963dd1"
down_revision: Union[str, Sequence[str], None] = "add_new_features_2024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_soft_delete_columns(table_name: str) -> None:
    op.add_column(
        table_name,
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(op.f(f"ix_{table_name}_is_deleted"), table_name, ["is_deleted"], unique=False)
    op.alter_column(
        table_name,
        "is_deleted",
        server_default=None,
        existing_type=sa.Boolean(),
    )


def _drop_soft_delete_columns(table_name: str) -> None:
    op.drop_index(op.f(f"ix_{table_name}_is_deleted"), table_name=table_name)
    op.drop_column(table_name, "is_deleted")


def upgrade() -> None:
    """Add the missing soft delete boolean flag for new feature tables."""
    for table in ("shops", "apartments", "apartment_permitted_vehicles"):
        _add_soft_delete_columns(table)


def downgrade() -> None:
    """Revert the soft delete flag additions."""
    for table in ("apartment_permitted_vehicles", "apartments", "shops"):
        _drop_soft_delete_columns(table)
