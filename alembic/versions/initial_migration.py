"""initial migration

Revision ID: initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create enum type for delivery status
    delivery_status = postgresql.ENUM('pending', 'success', 'failed', 'retrying', name='deliverystatus')
    delivery_status.create(op.get_bind())

    # Create subscriptions table with PostgreSQL-specific features
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('target_url', sa.String(), nullable=False),
        sa.Column('secret_key', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_subscriptions_name', 'subscriptions', [sa.text('lower(name)')])
    op.create_index('ix_subscriptions_created_at', 'subscriptions', ['created_at'])

    # Create webhook_deliveries table with PostgreSQL-specific features
    op.create_table(
        'webhook_deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'success', 'failed', 'retrying', name='deliverystatus'), nullable=False),
        sa.Column('attempt_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_webhook_deliveries_status', 'webhook_deliveries', ['status'])
    op.create_index('ix_webhook_deliveries_created_at', 'webhook_deliveries', ['created_at'])
    op.create_index('ix_webhook_deliveries_subscription_id', 'webhook_deliveries', ['subscription_id'])
    op.create_index('ix_webhook_deliveries_next_retry_at', 'webhook_deliveries', ['next_retry_at'])

    # Create delivery_attempts table with PostgreSQL-specific features
    op.create_table(
        'delivery_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('delivery_id', sa.Integer(), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.String(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['delivery_id'], ['webhook_deliveries.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_delivery_attempts_delivery_id', 'delivery_attempts', ['delivery_id'])
    op.create_index('ix_delivery_attempts_created_at', 'delivery_attempts', ['created_at'])
    op.create_index('ix_delivery_attempts_status_code', 'delivery_attempts', ['status_code'])

def downgrade() -> None:
    op.drop_index('ix_delivery_attempts_status_code', table_name='delivery_attempts')
    op.drop_index('ix_delivery_attempts_created_at', table_name='delivery_attempts')
    op.drop_index('ix_delivery_attempts_delivery_id', table_name='delivery_attempts')
    op.drop_table('delivery_attempts')
    
    op.drop_index('ix_webhook_deliveries_next_retry_at', table_name='webhook_deliveries')
    op.drop_index('ix_webhook_deliveries_subscription_id', table_name='webhook_deliveries')
    op.drop_index('ix_webhook_deliveries_created_at', table_name='webhook_deliveries')
    op.drop_index('ix_webhook_deliveries_status', table_name='webhook_deliveries')
    op.drop_table('webhook_deliveries')
    
    op.drop_index('ix_subscriptions_created_at', table_name='subscriptions')
    op.drop_index('ix_subscriptions_name', table_name='subscriptions')
    op.drop_table('subscriptions')
    
    # Drop enum type
    delivery_status = postgresql.ENUM('pending', 'success', 'failed', 'retrying', name='deliverystatus')
    delivery_status.drop(op.get_bind()) 