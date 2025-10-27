# Migration Quick Reference

Quick reference card for common Alembic migration tasks.

## Daily Operations

### Check Current Status
```bash
# Show current database version
alembic current

# Show all migrations
alembic history --verbose

# Show pending migrations
alembic history --verbose | grep -A 5 "(current)"
```

### Apply Migrations
```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade 001_add_version_column

# Apply one migration at a time
alembic upgrade +1
```

### Rollback Migrations
```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade 001_add_version_column

# Rollback all migrations
alembic downgrade base
```

## Creating New Migrations

### Auto-generate (Recommended)
```bash
# 1. Update src/models/orm.py with schema changes
# 2. Generate migration
alembic revision --autogenerate -m "add new_field to candidates"

# 3. Review generated file in alembic/versions/
# 4. Test migration
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

### Manual Migration
```bash
# Create empty migration
alembic revision -m "custom data migration"

# Edit alembic/versions/xxx_custom_data_migration.py
# Implement upgrade() and downgrade()

# Test
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

## Preview Changes

```bash
# Preview SQL for upgrade
alembic upgrade head --sql > upgrade.sql

# Preview SQL for downgrade
alembic downgrade -1 --sql > downgrade.sql

# Review the SQL files before running
cat upgrade.sql
```

## Troubleshooting

### Migration Stuck or Failed
```bash
# Check current version
alembic current

# Check database version table
psql provider_registration -c "SELECT * FROM alembic_version;"

# If stuck, manually stamp version (DANGEROUS - backup first!)
alembic stamp head
```

### Reset Everything (Development Only)
```bash
# WARNING: This deletes all data!

# Downgrade to base
alembic downgrade base

# Or drop and recreate database
dropdb provider_registration
createdb provider_registration

# Apply all migrations
alembic upgrade head
```

### Test Migrations
```bash
# Run automated test suite
python test_migrations.py

# Manual testing
alembic upgrade head      # Apply all
alembic downgrade base    # Remove all
alembic upgrade head      # Reapply all
```

## Production Workflow

```bash
# 1. BACKUP DATABASE FIRST!
pg_dump provider_registration > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Preview changes
alembic upgrade head --sql > migration_preview.sql
cat migration_preview.sql

# 3. Apply migrations
alembic upgrade head

# 4. Verify application works
curl http://localhost:5004/health

# 5. If issues, rollback
alembic downgrade -1
```

## Migration File Template

```python
"""Brief description of changes

Revision ID: xxx
Revises: yyy
Create Date: 2025-01-15

"""
from alembic import op
import sqlalchemy as sa

revision = 'xxx'
down_revision = 'yyy'

def upgrade() -> None:
    # Add your upgrade operations here
    op.add_column('candidates',
        sa.Column('new_field', sa.String(100), nullable=True)
    )

def downgrade() -> None:
    # Add your downgrade operations here
    op.drop_column('candidates', 'new_field')
```

## Common Operations

### Add Column
```python
def upgrade():
    op.add_column('candidates',
        sa.Column('new_field', sa.String(100), nullable=True)
    )

def downgrade():
    op.drop_column('candidates', 'new_field')
```

### Add Index
```python
def upgrade():
    op.create_index('idx_candidates_new_field', 'candidates', ['new_field'])

def downgrade():
    op.drop_index('idx_candidates_new_field', table_name='candidates')
```

### Modify Column
```python
def upgrade():
    op.alter_column('candidates', 'status',
        type_=sa.String(50),
        existing_type=sa.String(20)
    )

def downgrade():
    op.alter_column('candidates', 'status',
        type_=sa.String(20),
        existing_type=sa.String(50)
    )
```

### Add Constraint
```python
def upgrade():
    op.create_check_constraint(
        'value_positive',
        'candidates',
        'value > 0'
    )

def downgrade():
    op.drop_constraint('value_positive', 'candidates', type_='check')
```

## Environment Variables

```bash
# Override database URL
export DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
alembic upgrade head

# Use different config file
alembic -c alembic_staging.ini upgrade head
```

## See Also

- Full documentation: [MIGRATIONS.md](MIGRATIONS.md)
- Alembic docs: https://alembic.sqlalchemy.org/
- SQLAlchemy docs: https://docs.sqlalchemy.org/
