# Database Migrations Guide

This document provides comprehensive guidance for managing database schema migrations using Alembic in the Provider Registration Service.

## Table of Contents

- [Overview](#overview)
- [Setup](#setup)
- [Common Commands](#common-commands)
- [Migration History](#migration-history)
- [Creating New Migrations](#creating-new-migrations)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

The Provider Registration Service uses Alembic for database schema migrations with async PostgreSQL support. Alembic provides version control for your database schema, allowing you to:

- Track schema changes over time
- Apply changes incrementally
- Roll back changes if needed
- Share schema changes across development and production environments

### Key Features

- **Async Support**: Configured for asyncpg driver
- **Automatic Metadata**: Uses SQLAlchemy models for schema detection
- **Reversible Migrations**: All migrations support upgrade and downgrade
- **Version Control**: Sequential versioning with descriptive names

## Setup

### Prerequisites

1. PostgreSQL database running (version 12+)
2. Python 3.11+
3. Alembic installed (included in project dependencies)

### Database Connection

Alembic uses the `DATABASE_URL` environment variable from your configuration:

```bash
# Default connection string
DATABASE_URL=postgresql+asyncpg://provider_user:provider_pass@localhost:5432/provider_registration
```

You can override this in:
- `.env` file
- Environment variables
- `alembic.ini` (not recommended for production)

## Common Commands

### View Migration History

Show all migrations and their status:

```bash
alembic history --verbose
```

Show current database version:

```bash
alembic current
```

### Apply Migrations

Upgrade to the latest version:

```bash
alembic upgrade head
```

Upgrade to a specific version:

```bash
alembic upgrade 001_add_version_column
```

Upgrade one version at a time:

```bash
alembic upgrade +1
```

### Rollback Migrations

Downgrade to a specific version:

```bash
alembic downgrade 001_add_version_column
```

Downgrade one version:

```bash
alembic downgrade -1
```

Downgrade all migrations:

```bash
alembic downgrade base
```

### Generate New Migrations

Auto-generate migration from model changes:

```bash
alembic revision --autogenerate -m "description of changes"
```

Create empty migration template:

```bash
alembic revision -m "description of changes"
```

### Show SQL Without Executing

Preview SQL for upgrade:

```bash
alembic upgrade head --sql
```

Preview SQL for downgrade:

```bash
alembic downgrade -1 --sql
```

## Migration History

### 000_initial_schema

**Created**: 2025-01-15
**Description**: Initial database schema for candidates table

**Changes**:
- Creates `candidates` table with base columns
- Adds unique constraint on `contact_email`
- Adds check constraints for positive values
- Creates indexes for status, created_at, and products (GIN)
- Creates trigger for auto-updating `updated_at` timestamp

**Columns**:
- `id`: UUID primary key (auto-generated)
- `company_name`: VARCHAR(255), required
- `contact_email`: VARCHAR(255), required, unique
- `phone`: VARCHAR(50), optional
- `products`: JSONB, optional
- `truck_count`: INTEGER, must be > 0
- `capacity_tons_per_day`: INTEGER, must be > 0
- `location`: VARCHAR(255), optional
- `status`: VARCHAR(20), default 'pending', must be in ('pending', 'approved', 'rejected')
- `created_at`: TIMESTAMP, auto-set on creation
- `updated_at`: TIMESTAMP, auto-updated on changes
- `provider_id`: INTEGER, optional (reference to billing service)

### 001_add_version_column

**Created**: 2025-01-15
**Description**: Adds optimistic locking support (Phase 1 - Security)

**Changes**:
- Adds `version` column (INTEGER, default 1)
- Creates composite index on (id, version)
- Updates trigger to auto-increment version on updates
- Prevents race conditions during concurrent updates

**Use Case**:
```python
# Optimistic locking prevents concurrent modifications
candidate = await service.get_candidate(id)
# User A and User B both fetch candidate with version=1

# User A updates (version=1 -> 2)
await service.approve_candidate(id, provider_id, expected_version=1)  # Success

# User B tries to update (still expects version=1, but now it's 2)
await service.approve_candidate(id, provider_id, expected_version=1)  # Fails!
```

### 002_add_rejection_reason

**Created**: 2025-01-15
**Description**: Adds rejection tracking (Phase 3 - Data Architecture)

**Changes**:
- Adds `rejection_reason` column (TEXT, nullable)
- Allows storing detailed explanation for rejections
- Improves audit trail and transparency

**Use Case**:
```python
# When rejecting a candidate, provide a reason
await service.reject_candidate(
    candidate_id=id,
    reason="Insufficient truck capacity for current demand"
)
```

## Creating New Migrations

### Method 1: Auto-generate (Recommended)

1. **Update SQLAlchemy models** in `src/models/orm.py`:

```python
# Example: Add new column
class Candidate(Base):
    # ... existing columns ...
    new_field = Column(String(100), nullable=True)
```

2. **Generate migration**:

```bash
alembic revision --autogenerate -m "add new_field to candidates"
```

3. **Review generated migration** in `alembic/versions/`:
   - Check upgrade() and downgrade() functions
   - Verify SQL statements are correct
   - Add any custom logic needed

4. **Test migration**:

```bash
# Test upgrade
alembic upgrade head

# Verify schema
psql -d provider_registration -c "\d candidates"

# Test downgrade
alembic downgrade -1

# Re-apply
alembic upgrade head
```

### Method 2: Manual Migration

1. **Create migration template**:

```bash
alembic revision -m "custom data migration"
```

2. **Edit migration file**:

```python
def upgrade() -> None:
    # Add custom SQL or operations
    op.execute("""
        UPDATE candidates
        SET some_field = 'value'
        WHERE condition
    """)

def downgrade() -> None:
    # Reverse the operation
    op.execute("""
        UPDATE candidates
        SET some_field = NULL
        WHERE condition
    """)
```

3. **Test thoroughly** before applying to production

## Best Practices

### Migration Design

1. **Make migrations reversible**: Always implement downgrade()
2. **One change per migration**: Keep migrations focused and atomic
3. **Test both directions**: Verify upgrade and downgrade work correctly
4. **Use transactions**: Alembic wraps migrations in transactions by default
5. **Handle data carefully**: Be cautious with data migrations on large tables

### Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/new-field

# 2. Update models
# Edit src/models/orm.py

# 3. Generate migration
alembic revision --autogenerate -m "add new field"

# 4. Review and test migration
alembic upgrade head
# Test your application
alembic downgrade -1
alembic upgrade head

# 5. Commit migration with code changes
git add alembic/versions/*.py src/models/orm.py
git commit -m "Add new field with migration"
```

### Production Deployment

1. **Backup database** before applying migrations
2. **Test migrations** on staging environment first
3. **Use SQL preview** to review changes:
   ```bash
   alembic upgrade head --sql > migration.sql
   # Review migration.sql
   ```
4. **Monitor application** during migration
5. **Have rollback plan** ready

### Naming Conventions

- Use descriptive migration names: `add_rejection_reason` not `update_table`
- Include action verb: add, remove, modify, create, drop
- Include affected object: table name, column name
- Keep names concise but clear

### Column Modifications

When modifying existing columns:

```python
# Good: Explicit type and constraints
op.alter_column('candidates', 'status',
    type_=sa.String(50),  # Explicit new type
    existing_type=sa.String(20),  # Document old type
    nullable=False
)

# Bad: Ambiguous change
op.alter_column('candidates', 'status', type_=sa.String(50))
```

### Index Management

Always name indexes explicitly:

```python
# Good: Named index
op.create_index('idx_candidates_email', 'candidates', ['contact_email'])

# Bad: Auto-generated name
op.create_index(None, 'candidates', ['contact_email'])
```

### Data Migrations

For data transformations:

```python
def upgrade() -> None:
    # Use Core for data operations, not ORM
    from sqlalchemy import table, column, select, update

    candidates = table('candidates',
        column('id'),
        column('old_field'),
        column('new_field')
    )

    # Batch update
    op.execute(
        update(candidates)
        .where(candidates.c.old_field.isnot(None))
        .values(new_field=candidates.c.old_field)
    )
```

## Troubleshooting

### Common Issues

#### "Target database is not up to date"

```bash
# Check current version
alembic current

# Check migration history
alembic history

# Upgrade to head
alembic upgrade head
```

#### "Can't locate revision identified by 'xyz'"

```bash
# Ensure all migration files are present
ls -la alembic/versions/

# Check alembic_version table
psql -d provider_registration -c "SELECT * FROM alembic_version;"

# If table is out of sync, stamp current version
alembic stamp head
```

#### "Constraint already exists"

This usually happens when migration runs twice:

```bash
# Check what migrations were applied
alembic history --verbose

# Downgrade and re-run
alembic downgrade -1
alembic upgrade head
```

#### "Async connection issues"

Ensure you're using the asyncpg driver:

```bash
# Correct format
postgresql+asyncpg://user:pass@host:port/db

# Incorrect (sync driver)
postgresql://user:pass@host:port/db
```

### Manual Intervention

If migrations are stuck:

```bash
# 1. Backup database
pg_dump provider_registration > backup.sql

# 2. Check alembic_version table
psql provider_registration

SELECT * FROM alembic_version;

# 3. Manually set version if needed (DANGEROUS!)
UPDATE alembic_version SET version_num = 'desired_revision_id';

# 4. Verify with alembic
alembic current
```

### Recovery from Failed Migration

```bash
# 1. Check error message carefully
alembic upgrade head

# 2. If migration partially applied, manually fix database
psql provider_registration
# Fix any partial changes

# 3. Mark migration as failed
alembic downgrade -1

# 4. Fix migration code
# Edit alembic/versions/xxx_migration.py

# 5. Re-run migration
alembic upgrade head
```

## Testing Migrations

### Unit Testing

```python
# tests/test_migrations.py
import pytest
from alembic import command
from alembic.config import Config

@pytest.fixture
def alembic_config():
    config = Config("alembic.ini")
    return config

def test_upgrade_downgrade(alembic_config):
    """Test that migrations can upgrade and downgrade"""
    # Upgrade to head
    command.upgrade(alembic_config, "head")

    # Downgrade one step
    command.downgrade(alembic_config, "-1")

    # Upgrade again
    command.upgrade(alembic_config, "head")
```

### Integration Testing

```bash
#!/bin/bash
# scripts/test_migrations.sh

# Test fresh database
dropdb provider_registration_test
createdb provider_registration_test

# Run all migrations
alembic upgrade head

# Verify schema
psql provider_registration_test -c "\d candidates"

# Test downgrade
alembic downgrade base

# Test upgrade again
alembic upgrade head
```

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## Support

For issues or questions:
1. Check this documentation
2. Review migration code in `alembic/versions/`
3. Check Alembic logs
4. Consult team lead or DevOps
