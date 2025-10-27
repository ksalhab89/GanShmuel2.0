"""Initial tables: containers_registered and transactions

Revision ID: 001
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial tables."""
    # Create containers_registered table
    op.create_table(
        'containers_registered',
        sa.Column('container_id', sa.String(15), nullable=False),
        sa.Column('weight', sa.Integer(), nullable=True),
        sa.Column('unit', sa.String(3), nullable=False, server_default='kg'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('container_id'),
        sa.Index('idx_containers_weight', 'weight'),
        sa.Index('idx_containers_created_at', 'created_at'),
    )
    
    # Create transactions table
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('datetime', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('direction', sa.String(4), nullable=False),
        sa.Column('truck', sa.String(20), nullable=True),
        sa.Column('containers', sa.Text(), nullable=False),
        sa.Column('bruto', sa.Integer(), nullable=False),
        sa.Column('truck_tara', sa.Integer(), nullable=True),
        sa.Column('neto', sa.Integer(), nullable=True),
        sa.Column('produce', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_session_direction', 'session_id', 'direction'),
        sa.Index('idx_datetime', 'datetime'),
        sa.Index('idx_direction', 'direction'),
        sa.Index('idx_truck', 'truck'),
        sa.Index('ix_transactions_session_id', 'session_id'),
    )


def downgrade() -> None:
    """Drop initial tables."""
    op.drop_table('transactions')
    op.drop_table('containers_registered')