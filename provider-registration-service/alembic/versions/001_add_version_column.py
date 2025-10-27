"""Add version column for optimistic locking

Revision ID: 001_add_version_column
Revises: 000_initial_schema
Create Date: 2025-01-15 11:00:00.000000

This migration adds the version column to support optimistic locking,
preventing race conditions during concurrent updates.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_add_version_column'
down_revision = '000_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add version column with default value of 1"""

    # Add version column
    op.add_column(
        'candidates',
        sa.Column('version', sa.Integer(), nullable=False, server_default='1')
    )

    # Create index for efficient version checking
    op.create_index(
        'idx_candidates_version',
        'candidates',
        ['id', 'version'],
        unique=False
    )

    # Add column comment for documentation
    op.execute("""
        COMMENT ON COLUMN candidates.version IS
        'Optimistic locking version - increments on each update to prevent race conditions'
    """)

    # Update the trigger function to also increment version
    op.execute("""
        CREATE OR REPLACE FUNCTION update_candidates_metadata()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            NEW.version = OLD.version + 1;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Drop and recreate trigger with new function name
    op.execute("DROP TRIGGER IF EXISTS update_candidates_updated_at ON candidates")
    op.execute("""
        CREATE TRIGGER update_candidates_metadata
        BEFORE UPDATE ON candidates
        FOR EACH ROW
        EXECUTE FUNCTION update_candidates_metadata();
    """)


def downgrade() -> None:
    """Remove version column and revert trigger changes"""

    # Restore original trigger function (only updates timestamp)
    op.execute("""
        CREATE OR REPLACE FUNCTION update_candidates_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Drop current trigger and recreate with original function
    op.execute("DROP TRIGGER IF EXISTS update_candidates_metadata ON candidates")
    op.execute("""
        CREATE TRIGGER update_candidates_updated_at
        BEFORE UPDATE ON candidates
        FOR EACH ROW
        EXECUTE FUNCTION update_candidates_updated_at();
    """)

    # Drop metadata function
    op.execute("DROP FUNCTION IF EXISTS update_candidates_metadata()")

    # Drop index
    op.drop_index('idx_candidates_version', table_name='candidates')

    # Drop column
    op.drop_column('candidates', 'version')
