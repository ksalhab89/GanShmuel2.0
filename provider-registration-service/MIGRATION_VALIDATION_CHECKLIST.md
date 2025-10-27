# Migration Validation Checklist

Use this checklist to validate the Alembic migration system setup and ensure everything is working correctly.

## Pre-Flight Checks

### 1. Dependencies Installed
```bash
# Check if alembic is installed
python -c "import alembic; print(f'Alembic version: {alembic.__version__}')"

# Expected output: Alembic version: 1.13.x or higher
```
- [ ] Alembic is installed and accessible

### 2. Database Connection
```bash
# Verify DATABASE_URL is set
echo $DATABASE_URL

# Test database connection
psql $DATABASE_URL -c "SELECT version();"
```
- [ ] Database connection string is configured
- [ ] Can connect to PostgreSQL database

### 3. File Structure
```bash
# Check all migration files exist
ls -la alembic/versions/

# Expected files:
# - 000_initial_schema.py
# - 001_add_version_column.py
# - 002_add_rejection_reason.py
```
- [ ] All migration files are present
- [ ] alembic.ini exists
- [ ] alembic/env.py exists
- [ ] alembic/script.py.mako exists

## Migration Tests

### Test 1: Clean State
```bash
# Start from clean slate
alembic downgrade base

# Verify no candidates table
psql $DATABASE_URL -c "\d candidates"
# Expected: relation "candidates" does not exist
```
- [ ] Can downgrade to base
- [ ] Candidates table is removed

### Test 2: Initial Schema
```bash
# Apply initial migration
alembic upgrade 000_initial_schema

# Verify table exists
psql $DATABASE_URL -c "\d candidates"

# Check columns (should NOT have version or rejection_reason yet)
psql $DATABASE_URL -c "SELECT column_name FROM information_schema.columns WHERE table_name='candidates';"
```
- [ ] Initial schema creates candidates table
- [ ] Base columns exist (id, company_name, contact_email, etc.)
- [ ] Version column does NOT exist yet
- [ ] Rejection_reason column does NOT exist yet
- [ ] Indexes created (idx_candidates_status, idx_candidates_created_at, idx_candidates_products)
- [ ] Trigger created (update_candidates_updated_at)

### Test 3: Version Column Migration
```bash
# Apply version column migration
alembic upgrade 001_add_version_column

# Verify version column exists
psql $DATABASE_URL -c "\d candidates" | grep version

# Check version index
psql $DATABASE_URL -c "\di idx_candidates_version"
```
- [ ] Version column added
- [ ] Version column default is 1
- [ ] Version index created (idx_candidates_version)
- [ ] Trigger updated to update_candidates_metadata

### Test 4: Rejection Reason Migration
```bash
# Apply rejection reason migration
alembic upgrade 002_add_rejection_reason

# Verify rejection_reason column exists
psql $DATABASE_URL -c "\d candidates" | grep rejection_reason
```
- [ ] Rejection_reason column added
- [ ] Rejection_reason is nullable (TEXT type)

### Test 5: Rollback Rejection Reason
```bash
# Rollback to version column only
alembic downgrade 001_add_version_column

# Verify rejection_reason is gone
psql $DATABASE_URL -c "\d candidates" | grep rejection_reason
# Expected: no output

# Verify version still exists
psql $DATABASE_URL -c "\d candidates" | grep version
# Expected: version column shown
```
- [ ] Can downgrade rejection_reason migration
- [ ] Rejection_reason column removed
- [ ] Version column still exists

### Test 6: Rollback Version Column
```bash
# Rollback to initial schema
alembic downgrade 000_initial_schema

# Verify version is gone
psql $DATABASE_URL -c "\d candidates" | grep version
# Expected: no version column

# Verify trigger reverted
psql $DATABASE_URL -c "\df update_candidates_updated_at"
```
- [ ] Can downgrade version column migration
- [ ] Version column removed
- [ ] Version index removed
- [ ] Trigger reverted to update_candidates_updated_at

### Test 7: Upgrade to Head
```bash
# Upgrade to latest
alembic upgrade head

# Verify current revision
alembic current

# Verify all columns exist
psql $DATABASE_URL -c "\d candidates"
```
- [ ] Can upgrade to head
- [ ] Current revision is 002_add_rejection_reason
- [ ] All columns exist (including version and rejection_reason)

### Test 8: Full Cycle Test
```bash
# Full downgrade
alembic downgrade base

# Full upgrade
alembic upgrade head

# Verify final state
alembic current
```
- [ ] Full downgrade successful
- [ ] Full upgrade successful
- [ ] Database in correct final state

## Data Preservation Tests

### Test 9: Data Survives Migrations
```bash
# Start fresh
alembic upgrade head

# Insert test data
psql $DATABASE_URL << EOF
INSERT INTO candidates (company_name, contact_email, products, truck_count, capacity_tons_per_day)
VALUES ('Test Company', 'test@example.com', '["apples"]', 5, 100);
EOF

# Check data
psql $DATABASE_URL -c "SELECT company_name, version FROM candidates WHERE contact_email='test@example.com';"

# Downgrade one step
alembic downgrade -1

# Verify data still exists (rejection_reason should be gone)
psql $DATABASE_URL -c "SELECT company_name, version FROM candidates WHERE contact_email='test@example.com';"

# Upgrade again
alembic upgrade head

# Verify data preserved
psql $DATABASE_URL -c "SELECT company_name, version, rejection_reason FROM candidates WHERE contact_email='test@example.com';"

# Cleanup
psql $DATABASE_URL -c "DELETE FROM candidates WHERE contact_email='test@example.com';"
```
- [ ] Data survives downgrade
- [ ] Data survives upgrade
- [ ] Version column maintained correctly
- [ ] No data corruption

## Automated Test Suite

### Test 10: Run Automated Tests
```bash
# Run test suite
python test_migrations.py

# Expected output: ALL TESTS PASSED
```
- [ ] Automated test suite passes
- [ ] No errors in test output
- [ ] All verifications pass

## Application Integration

### Test 11: Application Compatibility
```bash
# Start application
uv run uvicorn src.main:app --reload --port 5004 &
APP_PID=$!

# Wait for startup
sleep 3

# Test health endpoint
curl http://localhost:5004/health

# Test API
curl -X POST http://localhost:5004/candidates \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Integration Test",
    "contact_email": "integration@test.com",
    "phone": "555-0100",
    "products": ["apples"],
    "truck_count": 3,
    "capacity_tons_per_day": 50,
    "location": "Test Location"
  }'

# Cleanup
kill $APP_PID
psql $DATABASE_URL -c "DELETE FROM candidates WHERE contact_email='integration@test.com';"
```
- [ ] Application starts successfully with migrated schema
- [ ] Health check passes
- [ ] Can create candidates
- [ ] Version column works with application

## Documentation Checks

### Test 12: Documentation Complete
- [ ] MIGRATIONS.md exists and is comprehensive
- [ ] MIGRATION_QUICK_REFERENCE.md exists
- [ ] ALEMBIC_SETUP_SUMMARY.md exists
- [ ] README.md updated with migration instructions
- [ ] All documentation is clear and accurate

## Final Validation

### Test 13: Production Readiness
- [ ] All migrations are reversible
- [ ] No data loss in any migration
- [ ] Migrations are idempotent
- [ ] Database constraints preserved
- [ ] Indexes maintained correctly
- [ ] Triggers work correctly
- [ ] All tests pass
- [ ] Documentation complete

## Sign-off Checklist

Before marking Task 3.2 as complete:

- [ ] All pre-flight checks pass
- [ ] All migration tests pass (1-8)
- [ ] Data preservation tests pass (9)
- [ ] Automated test suite passes (10)
- [ ] Application integration works (11)
- [ ] Documentation complete (12)
- [ ] Production ready (13)

## Validation Commands Summary

```bash
# Quick validation script
echo "=== Alembic Migration Validation ==="

# 1. Check files
echo "✓ Checking files..."
test -f alembic.ini && echo "  alembic.ini found"
test -f alembic/env.py && echo "  alembic/env.py found"
test -f alembic/versions/000_initial_schema.py && echo "  000_initial_schema.py found"
test -f alembic/versions/001_add_version_column.py && echo "  001_add_version_column.py found"
test -f alembic/versions/002_add_rejection_reason.py && echo "  002_add_rejection_reason.py found"

# 2. Test migrations
echo "✓ Testing migrations..."
alembic downgrade base
alembic upgrade head
alembic current

# 3. Run test suite
echo "✓ Running test suite..."
python test_migrations.py

echo "=== Validation Complete ==="
```

## Troubleshooting

### Common Issues

**Issue: "Can't locate revision"**
- Check that all migration files are in alembic/versions/
- Verify revision IDs match in migration files
- Check alembic_version table in database

**Issue: "Target database is not up to date"**
- Run `alembic upgrade head`
- Check `alembic current` for current state

**Issue: "Constraint already exists"**
- May indicate migration ran twice
- Check database state manually
- Use `alembic downgrade -1` and retry

**Issue: "Connection refused"**
- Verify DATABASE_URL is correct
- Check PostgreSQL is running
- Test with `psql $DATABASE_URL`

## Post-Validation

After all checks pass:

1. Commit migration files:
   ```bash
   git add alembic/ *.md pyproject.toml src/models/orm.py
   git commit -m "Phase 3 - Task 3.2: Add Alembic migration system"
   ```

2. Update project documentation

3. Notify team of new migration system

4. Share MIGRATION_QUICK_REFERENCE.md with developers

---

**Status:** Ready for validation
**Task:** Phase 3 - Task 3.2: Alembic Migration System
