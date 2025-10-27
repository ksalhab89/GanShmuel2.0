"""Add rejection_reason column for tracking rejection details

Revision ID: 002_add_rejection_reason
Revises: 001_add_version_column
Create Date: 2025-01-15 12:00:00.000000

This migration adds the rejection_reason column to store optional
explanations when a candidate is rejected.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_rejection_reason'
down_revision = '001_add_version_column'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add rejection_reason column"""

    # Add rejection_reason column (nullable TEXT field)
    op.add_column(
        'candidates',
        sa.Column('rejection_reason', sa.Text(), nullable=True)
    )

    # Add column comment for documentation
    op.execute("""
        COMMENT ON COLUMN candidates.rejection_reason IS
        'Optional explanation provided when a candidate application is rejected'
    """)


def downgrade() -> None:
    """Remove rejection_reason column"""

    # Drop column
    op.drop_column('candidates', 'rejection_reason')
