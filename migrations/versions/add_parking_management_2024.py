"""Add parking management system

Revision ID: add_parking_mgmt_2024
Revises: 9ef76bfb9c9c
Create Date: 2024-11-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_parking_mgmt_2024'
down_revision = '9ef76bfb9c9c'
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types first
    op.execute("CREATE TYPE pricingmodel AS ENUM ('free', 'fixed', 'hourly')")
    op.execute("CREATE TYPE paymenttiming AS ENUM ('upfront', 'on_exit')")
    op.execute("CREATE TYPE slotstatus AS ENUM ('pending_verification', 'active', 'inactive', 'rejected')")
    op.execute("CREATE TYPE staffrole AS ENUM ('owner', 'staff', 'volunteer')")
    op.execute("CREATE TYPE sessionstatus AS ENUM ('checked_in', 'checked_out', 'escaped')")
    op.execute("CREATE TYPE paymentstatus AS ENUM ('pending', 'paid', 'partial')")
    op.execute("CREATE TYPE duestatus AS ENUM ('pending', 'paid', 'written_off')")
    op.execute("CREATE TYPE parkingvehicletype AS ENUM ('car', 'bike', 'truck')")

    # Create parking_slots table
    op.create_table(
        'parking_slots',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('location', sa.String(length=500), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('capacity', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Vehicle type capacity mapping'),
        sa.Column('pricing_model', sa.String(length=20), nullable=False, server_default='free'),
        sa.Column('pricing_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Pricing configuration based on pricing_model'),
        sa.Column('payment_timing', sa.String(length=20), nullable=False, server_default='on_exit'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='pending_verification'),
        sa.Column('verified_by', sa.UUID(), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.String(length=500), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_parking_slots_owner_id', 'parking_slots', ['owner_id'])
    op.create_index('ix_parking_slots_status', 'parking_slots', ['status'])
    op.create_index('ix_parking_slots_is_deleted', 'parking_slots', ['is_deleted'])

    # Create parking_slot_staff table
    op.create_table(
        'parking_slot_staff',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('slot_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False, server_default='staff'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['slot_id'], ['parking_slots.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slot_id', 'user_id', name='uq_slot_staff')
    )
    op.create_index('ix_parking_slot_staff_slot_id', 'parking_slot_staff', ['slot_id'])
    op.create_index('ix_parking_slot_staff_user_id', 'parking_slot_staff', ['user_id'])

    # Create parking_sessions table
    op.create_table(
        'parking_sessions',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('slot_id', sa.UUID(), nullable=False),
        sa.Column('vehicle_number', sa.String(length=20), nullable=False, comment='Vehicle registration number'),
        sa.Column('vehicle_type', sa.String(length=20), nullable=False),
        sa.Column('checked_in_by', sa.UUID(), nullable=False),
        sa.Column('checked_out_by', sa.UUID(), nullable=True),
        sa.Column('check_in_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('check_out_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='checked_in'),
        sa.Column('calculated_fee', sa.Numeric(10, 2), nullable=False, server_default='0', comment='Calculated parking fee based on duration'),
        sa.Column('collected_fee', sa.Numeric(10, 2), nullable=True, comment='Actual amount collected from customer'),
        sa.Column('payment_status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['slot_id'], ['parking_slots.id']),
        sa.ForeignKeyConstraint(['checked_in_by'], ['users.id']),
        sa.ForeignKeyConstraint(['checked_out_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_parking_sessions_slot_id', 'parking_sessions', ['slot_id'])
    op.create_index('ix_parking_sessions_vehicle_number', 'parking_sessions', ['vehicle_number'])
    op.create_index('ix_parking_sessions_status', 'parking_sessions', ['status'])
    op.create_index('ix_parking_sessions_check_in_time', 'parking_sessions', ['check_in_time'])
    op.create_index('ix_parking_sessions_slot_status', 'parking_sessions', ['slot_id', 'status'])

    # Create vehicle_dues table
    op.create_table(
        'vehicle_dues',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('vehicle_number', sa.String(length=20), nullable=False, comment='Vehicle registration number with unpaid dues'),
        sa.Column('slot_owner_id', sa.UUID(), nullable=False, comment='Owner of parking slot (for cross-slot tracking)'),
        sa.Column('session_id', sa.UUID(), nullable=False, comment='Original escaped session'),
        sa.Column('due_amount', sa.Numeric(10, 2), nullable=False, comment='Original unpaid amount'),
        sa.Column('paid_amount', sa.Numeric(10, 2), nullable=False, server_default='0', comment='Amount paid towards this due'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_by_staff', sa.UUID(), nullable=True, comment='Staff who collected the payment'),
        sa.Column('payment_session_id', sa.UUID(), nullable=True, comment='Session during which due was paid'),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['slot_owner_id'], ['users.id']),
        sa.ForeignKeyConstraint(['session_id'], ['parking_sessions.id']),
        sa.ForeignKeyConstraint(['paid_by_staff'], ['users.id']),
        sa.ForeignKeyConstraint(['payment_session_id'], ['parking_sessions.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', name='uq_due_session')
    )
    op.create_index('ix_vehicle_dues_vehicle_number', 'vehicle_dues', ['vehicle_number'])
    op.create_index('ix_vehicle_dues_slot_owner_id', 'vehicle_dues', ['slot_owner_id'])
    op.create_index('ix_vehicle_dues_status', 'vehicle_dues', ['status'])
    op.create_index('ix_vehicle_dues_vehicle_owner', 'vehicle_dues', ['vehicle_number', 'slot_owner_id'])


def downgrade():
    # Drop tables in reverse order
    op.drop_index('ix_vehicle_dues_vehicle_owner', 'vehicle_dues')
    op.drop_index('ix_vehicle_dues_status', 'vehicle_dues')
    op.drop_index('ix_vehicle_dues_slot_owner_id', 'vehicle_dues')
    op.drop_index('ix_vehicle_dues_vehicle_number', 'vehicle_dues')
    op.drop_table('vehicle_dues')
    
    op.drop_index('ix_parking_sessions_slot_status', 'parking_sessions')
    op.drop_index('ix_parking_sessions_check_in_time', 'parking_sessions')
    op.drop_index('ix_parking_sessions_status', 'parking_sessions')
    op.drop_index('ix_parking_sessions_vehicle_number', 'parking_sessions')
    op.drop_index('ix_parking_sessions_slot_id', 'parking_sessions')
    op.drop_table('parking_sessions')
    
    op.drop_index('ix_parking_slot_staff_user_id', 'parking_slot_staff')
    op.drop_index('ix_parking_slot_staff_slot_id', 'parking_slot_staff')
    op.drop_table('parking_slot_staff')
    
    op.drop_index('ix_parking_slots_is_deleted', 'parking_slots')
    op.drop_index('ix_parking_slots_status', 'parking_slots')
    op.drop_index('ix_parking_slots_owner_id', 'parking_slots')
    op.drop_table('parking_slots')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS parkingvehicletype")
    op.execute("DROP TYPE IF EXISTS duestatus")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
    op.execute("DROP TYPE IF EXISTS sessionstatus")
    op.execute("DROP TYPE IF EXISTS staffrole")
    op.execute("DROP TYPE IF EXISTS slotstatus")
    op.execute("DROP TYPE IF EXISTS paymenttiming")
    op.execute("DROP TYPE IF EXISTS pricingmodel")