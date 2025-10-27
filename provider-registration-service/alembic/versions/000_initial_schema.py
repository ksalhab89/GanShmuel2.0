"""Initial schema for candidates table

Revision ID: 000_initial_schema
Revises:
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '000_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create candidates table with base schema"""

    # Create candidates table
    op.create_table(
        'candidates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('contact_email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('products', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('truck_count', sa.Integer(), nullable=True),
        sa.Column('capacity_tons_per_day', sa.Integer(), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('provider_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('contact_email'),
        sa.CheckConstraint('truck_count > 0', name='truck_count_positive'),
        sa.CheckConstraint('capacity_tons_per_day > 0', name='capacity_positive'),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name='status_check'),
    )

    # Create indexes
    op.create_index('idx_candidates_status', 'candidates', ['status'], unique=False)
    op.create_index('idx_candidates_created_at', 'candidates', ['created_at'], unique=False)
    op.create_index('idx_candidates_products', 'candidates', ['products'], unique=False, postgresql_using='gin')

    # Create trigger function for updating updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_candidates_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Create trigger
    op.execute("""
        CREATE TRIGGER update_candidates_updated_at
        BEFORE UPDATE ON candidates
        FOR EACH ROW
        EXECUTE FUNCTION update_candidates_updated_at();
    """)


def downgrade() -> None:
    """Drop candidates table and related objects"""

    # Drop trigger first
    op.execute("DROP TRIGGER IF EXISTS update_candidates_updated_at ON candidates")

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS update_candidates_updated_at()")

    # Drop indexes
    op.drop_index('idx_candidates_products', table_name='candidates')
    op.drop_index('idx_candidates_created_at', table_name='candidates')
    op.drop_index('idx_candidates_status', table_name='candidates')

    # Drop table
    op.drop_table('candidates')
