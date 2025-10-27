"""Performance indexes optimization

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 10:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance optimization indexes."""
    # Additional composite indexes for containers_registered
    op.create_index(
        'idx_containers_unit_weight', 
        'containers_registered', 
        ['unit', 'weight']
    )
    
    # Additional composite indexes for transactions
    op.create_index(
        'idx_transactions_datetime_direction', 
        'transactions', 
        ['datetime', 'direction']
    )
    
    op.create_index(
        'idx_transactions_truck_datetime', 
        'transactions', 
        ['truck', 'datetime']
    )
    
    # Covering index for common query patterns
    op.create_index(
        'idx_transactions_session_covering', 
        'transactions', 
        ['session_id', 'direction', 'datetime', 'bruto']
    )
    
    # Index for produce-based filtering
    op.create_index(
        'idx_transactions_produce', 
        'transactions', 
        ['produce']
    )
    
    # Index for net weight calculations
    op.create_index(
        'idx_transactions_neto', 
        'transactions', 
        ['neto']
    )


def downgrade() -> None:
    """Remove performance optimization indexes."""
    op.drop_index('idx_transactions_neto', table_name='transactions')
    op.drop_index('idx_transactions_produce', table_name='transactions')
    op.drop_index('idx_transactions_session_covering', table_name='transactions')
    op.drop_index('idx_transactions_truck_datetime', table_name='transactions')
    op.drop_index('idx_transactions_datetime_direction', table_name='transactions')
    op.drop_index('idx_containers_unit_weight', table_name='containers_registered')