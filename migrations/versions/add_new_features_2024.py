"""Add shop, analytics, and apartment management features

Revision ID: add_new_features_2024
Revises: ce219849935f
Create Date: 2024-10-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_new_features_2024'
down_revision = 'ce219849935f'
branch_labels = None
depends_on = None


def upgrade():
    # Create shops table
    op.create_table(
        'shops',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('address', sa.String(length=500), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=120), nullable=True),
        sa.Column('website', sa.String(length=200), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('operating_hours', sa.String(length=200), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create CTA events table
    op.create_table(
        'cta_events',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_context', sa.String(length=200), nullable=True),
        sa.Column('related_entity_id', sa.UUID(), nullable=True),
        sa.Column('related_entity_type', sa.String(length=50), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_cta_events_event_type', 'cta_events', ['event_type'])
    op.create_index('ix_cta_events_user_id', 'cta_events', ['user_id'])

    # Create apartments table
    op.create_table(
        'apartments',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('address', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('admin_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['admin_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_apartments_admin_id', 'apartments', ['admin_id'])

    # Create apartment_permitted_vehicles table
    op.create_table(
        'apartment_permitted_vehicles',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('apartment_id', sa.UUID(), nullable=False),
        sa.Column('vehicle_id', sa.UUID(), nullable=False),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('parking_spot', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['apartment_id'], ['apartments.id'], ),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('apartment_id', 'vehicle_id', name='uq_apartment_vehicle')
    )
    op.create_index('ix_apartment_permitted_vehicles_apartment_id', 'apartment_permitted_vehicles', ['apartment_id'])
    op.create_index('ix_apartment_permitted_vehicles_vehicle_id', 'apartment_permitted_vehicles', ['vehicle_id'])


def downgrade():
    # Drop tables in reverse order
    op.drop_index('ix_apartment_permitted_vehicles_vehicle_id', 'apartment_permitted_vehicles')
    op.drop_index('ix_apartment_permitted_vehicles_apartment_id', 'apartment_permitted_vehicles')
    op.drop_table('apartment_permitted_vehicles')
    
    op.drop_index('ix_apartments_admin_id', 'apartments')
    op.drop_table('apartments')
    
    op.drop_index('ix_cta_events_user_id', 'cta_events')
    op.drop_index('ix_cta_events_event_type', 'cta_events')
    op.drop_table('cta_events')
    
    op.drop_table('shops')
