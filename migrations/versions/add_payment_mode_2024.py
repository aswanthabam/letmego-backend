"""Add payment_mode to parking sessions and vehicle dues

Revision ID: add_payment_mode_2024
Revises: add_parking_mgmt_2024
Create Date: 2024-11-12 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_payment_mode_2024'
down_revision = 'add_parking_mgmt_2024'  # This references the previous migration
branch_labels = None
depends_on = None


def upgrade():
    """
    Add payment_mode column to track payment method (cash, upi, card, other)
    """
    
    # Step 1: Create the PaymentMode enum type
    op.execute("CREATE TYPE paymentmode AS ENUM ('cash', 'upi', 'card', 'other')")
    
    # Step 2: Add payment_mode column to parking_sessions table
    op.add_column('parking_sessions', 
        sa.Column('payment_mode', sa.String(20), nullable=True,
                  comment='Mode of payment: cash, upi, card, other')
    )
    
    # Step 3: Add payment_mode column to vehicle_dues table
    op.add_column('vehicle_dues',
        sa.Column('payment_mode', sa.String(20), nullable=True,
                  comment='Mode of payment: cash, upi, card, other')
    )
    
    print("✅ Successfully added payment_mode columns")


def downgrade():
    """
    Remove payment_mode columns if we need to rollback
    """
    
    # Remove columns in reverse order
    op.drop_column('vehicle_dues', 'payment_mode')
    op.drop_column('parking_sessions', 'payment_mode')
    
    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS paymentmode")
    
    print("✅ Successfully removed payment_mode columns")