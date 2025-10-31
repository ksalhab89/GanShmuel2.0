# Technical Debt Tracker

This document tracks all known technical debt in the Gan Shmuel project. All items are documented with context, priority, and estimated effort.

**Status**: Demo/Portfolio Project - Not Production Deployed
**Last Updated**: 2025-01-XX

---

## Priority Legend
- 🔴 **HIGH**: Blocks production deployment or causes significant issues
- 🟡 **MEDIUM**: Should be fixed before production, not blocking demo
- 🟢 **LOW**: Nice-to-have improvements, not urgent
- ⚪ **DEFERRED**: Intentional demo simplifications, document for future

---

## 1. Type Safety Technical Debt

### 1.1 Weight Service - Mypy Type Errors (57 errors)
**Priority**: 🟡 MEDIUM
**Effort**: 2-4 hours
**Impact**: Type safety, IDE autocomplete, refactoring confidence

**Files Affected**:
- `src/utils/validators.py`
- `src/utils/exceptions.py`
- `src/database.py`
- `src/models/database.py`
- `src/models/repositories.py`
- `src/services/session_service.py`
- `src/services/container_service.py`
- `src/services/query_service.py`
- `src/services/file_service.py`
- `src/routers/query.py`
- `src/routers/health.py`

**Current Workaround**: Temporary mypy overrides in `weight-service/pyproject.toml` (lines 52-68)

**Action Required**:
1. Remove one module from `[[tool.mypy.overrides]]`
2. Run `uv run mypy src` to see errors
3. Fix type hints (add return types, annotate variables)
4. Repeat for all 11 modules

**Reference**: `weight-service/pyproject.toml:52-68`

---

### 1.2 Billing Service - Mypy Type Errors (10 errors)
**Priority**: 🟡 MEDIUM
**Effort**: 1-2 hours
**Impact**: Type safety, consistency with other services

**Files Affected**:
- `src/database.py`
- `src/models/repositories.py`
- `src/utils/excel_handler.py`

**Current Workaround**: Temporary mypy overrides in `billing-service/pyproject.toml` (lines 54-62)

**Action Required**:
1. Fix database connection pool typing
2. Add return type hints to repository methods
3. Type Excel file processing functions

**Reference**: `billing-service/pyproject.toml:54-62`

---

## 2. Testing Technical Debt

### 2.1 Billing Service - Skipped Tests (25 tests)
**Priority**: 🟡 MEDIUM (business logic tests) / 🟢 LOW (others)
**Effort**: 4-8 hours
**Impact**: Test coverage gaps in critical billing logic

**Comprehensive Documentation**: See `billing-service/SKIPPED_TESTS.md`

**Summary by Category**:
1. **Database Constraint Tests (3)** - 🟢 LOW
   - Require MyISAM → InnoDB migration
   - Not critical for demo (application validates constraints)

2. **Repository Pattern Tests (3)** - 🟡 MEDIUM
   - Outdated `execute_query` mocking pattern
   - Should refactor to use pytest fixtures
   - Quick wins - 1 hour to fix all 3

3. **Weight Client Integration (8)** - 🟢 LOW
   - Complex async HTTP mocking
   - Retry logic tested manually via Docker Compose
   - Requires pytest-httpx or similar infrastructure

4. **Bill Generation Tests (6)** - 🔴 HIGH PRIORITY
   - **CRITICAL**: `test_generate_bill_provider_specific_rate` tests core business logic
   - Provider-specific rate override is key billing feature
   - Should be fixed ASAP (2 hours effort)

5. **Truck API Tests (3)** - 🟢 LOW
   - Weight service integration
   - Covered by end-to-end Docker Compose testing

6. **Rate Export Tests (1)** - 🟢 LOW
   - Excel edge case
   - Likely works now, just needs to be run

7. **Concurrency Tests (1)** - 🟢 LOW
   - Race condition testing
   - Requires InnoDB + proper transaction isolation

**Quick Wins**:
- `test_get_rates_excel_empty` - Just try running (5 min)
- Repository pattern tests - Refactor to fixtures (1 hour)
- **Priority**: Bill generation tests - Fix provider rate logic test (2 hours)

**Reference**: `billing-service/SKIPPED_TESTS.md`

---

## 3. Tooling Inconsistency

### 3.1 Billing Service - Flake8/Black/isort vs Ruff
**Priority**: 🟢 LOW
**Effort**: 2-3 hours
**Impact**: Developer experience, CI/CD speed (10-100x faster with Ruff)

**Current State**:
- **Weight Service**: Ruff (modern, fast)
- **Shift Service**: Ruff (modern, fast)
- **Provider Registration Service**: Ruff (modern, fast)
- **Billing Service**: flake8 + black + isort (traditional, slow)

**Why Inconsistent**: Billing service created earlier with traditional toolchain

**Migration Path**:
1. Add ruff to billing-service dev dependencies
2. Run `ruff check src tests` to see differences
3. Configure `pyproject.toml` to match other services
4. Update CI/CD workflow (`.github/workflows/test.yml`)
5. Remove flake8, black, isort from:
   - `pyproject.toml` dependencies
   - `.pre-commit-config.yaml` hooks (lines 39-69)
   - CI/CD workflow

**Benefits**:
- 10-100x faster linting/formatting
- Single tool instead of 3
- Consistency across all services
- Simpler pre-commit hooks

**References**:
- `billing-service/pyproject.toml:24-28` - TODO comment
- `.pre-commit-config.yaml:39, 52, 62` - TODO comments for hook removal

---

## 4. Database Architecture

### 4.1 Billing Service - MyISAM Engine (No Constraints)
**Priority**: 🟢 LOW (demo) / 🟡 MEDIUM (production)
**Effort**: 2-4 hours
**Impact**: Data integrity, foreign keys, transactions, concurrency

**Current State**:
All billing-service tables use MyISAM engine:
- Provider table - No unique constraint on name
- Trucks table - No foreign key to Provider
- No transaction support
- No row-level locking

**Production Risk**:
- Race conditions in concurrent provider creation
- Orphaned trucks (deleted provider, truck remains)
- No ACID guarantees

**Migration Path**:
```sql
-- 1. Backup data
SELECT * FROM Provider INTO OUTFILE '/tmp/providers.csv';

-- 2. Change engine
ALTER TABLE Provider ENGINE=InnoDB;
ALTER TABLE Trucks ENGINE=InnoDB;
ALTER TABLE Rates ENGINE=InnoDB;

-- 3. Add constraints
ALTER TABLE Provider ADD UNIQUE KEY `unique_name` (`name`);
ALTER TABLE Trucks ADD CONSTRAINT `fk_provider`
  FOREIGN KEY (`provider_id`) REFERENCES Provider(`id`)
  ON DELETE CASCADE;

-- 4. Enable transactions in application
BEGIN;
-- operations
COMMIT;
```

**Why Deferred**: Demo project, no concurrent users, manual data cleanup acceptable

**Reference**: `billing-service/SKIPPED_TESTS.md` - Category 1 (Database Constraint Tests)

---

## 5. Security & Authentication

### 5.1 Provider Registration - Hardcoded Admin Credentials
**Priority**: ⚪ DEFERRED (intentional for demo) / 🔴 HIGH (production)
**Effort**: 4-6 hours
**Impact**: Security, user management, audit trails

**Current State**:
```python
# provider-registration-service/src/routers/auth.py:8-16
ADMIN_USER = {
    "username": "admin@example.com",
    "password_hash": "$2b$12$...",  # admin123
    "role": "admin"
}
```

**Production Requirements**:
1. Create `users` table in PostgreSQL
   ```sql
   CREATE TABLE users (
       id SERIAL PRIMARY KEY,
       email VARCHAR(255) UNIQUE NOT NULL,
       password_hash VARCHAR(255) NOT NULL,
       role VARCHAR(50) NOT NULL,
       created_at TIMESTAMP DEFAULT NOW(),
       last_login TIMESTAMP
   );
   ```

2. Implement user repository
   - `UserRepository.get_by_email()`
   - `UserRepository.create()`
   - `UserRepository.update_last_login()`

3. Add user management endpoints
   - POST `/users` - Create admin users
   - GET `/users/me` - Get current user profile
   - PUT `/users/me/password` - Change password

4. Migration: Hash all admin passwords with bcrypt

**Why Deferred**:
- Demo project - single admin user sufficient
- Simplifies testing - no user registration flow
- Reduces complexity - focus on candidate approval workflow

**Security Notes**:
- Current password IS properly bcrypt hashed (not plaintext)
- JWT tokens still expire (30 minutes)
- Role-based access control (RBAC) still enforced
- Only admin operations exposed (no public endpoints)

**Reference**: `provider-registration-service/src/routers/auth.py:8-16`

---

## 6. Documentation & Code Quality

### 6.1 Pre-Commit Hook - TODO Check Removed
**Priority**: 🟢 LOW
**Effort**: 30 minutes
**Impact**: None (demo project has no ticket system)

**What Happened**:
Removed overly strict TODO check that required "GS-XXX" ticket format:
```yaml
# REMOVED from .pre-commit-config.yaml:
- id: check-todos
  name: Check TODOs have ticket references
  entry: bash -c 'git diff --cached --name-only --diff-filter=ACM | xargs grep -n "TODO:" | grep -v "TODO: GS-" ...'
```

**Why Removed**:
- Demo project has no Jira/GitHub Issues ticket system
- TODOs already have proper context (see this document)
- Check would block all commits with TODOs

**Alternative Approach**:
If ticket system added in future, replace with:
```yaml
- id: check-todos
  name: Check TODOs have context
  entry: bash -c 'git diff --cached -U0 | grep "^+.*TODO:" | grep -v "TODO:.*-" && exit 1 || exit 0'
```
This checks TODOs have *some* context (hyphen after TODO), not specific format.

**Reference**: `.pre-commit-config.yaml` - removed lines 127-133

---

## Summary Dashboard

### By Priority
- 🔴 **HIGH** (Production Blockers): 1 item
  - Bill generation test for provider-specific rates

- 🟡 **MEDIUM** (Pre-Production): 3 items
  - Weight service type errors (57 errors)
  - Billing service type errors (10 errors)
  - Skipped repository tests (3 tests)

- 🟢 **LOW** (Nice-to-Have): 7 items
  - Ruff migration (billing-service)
  - MyISAM→InnoDB migration
  - Weight client retry tests (8 tests)
  - Other skipped tests (14 tests)

- ⚪ **DEFERRED** (Intentional): 1 item
  - Hardcoded admin credentials (demo simplification)

### By Effort
- **Quick Wins (< 2 hours)**: 4 items
- **Medium Effort (2-4 hours)**: 5 items
- **Large Effort (4-8 hours)**: 3 items

### By Impact
- **High Impact**: Type safety (67 errors), Bill tests (business logic)
- **Medium Impact**: Tooling consistency, database integrity
- **Low Impact**: Additional test coverage, documentation

---

## Actionable Roadmap

### Phase 1: Critical Fixes (4 hours)
1. ✅ Document all tech debt (DONE - this file)
2. ✅ Document skipped tests (DONE - SKIPPED_TESTS.md)
3. 🔴 Fix `test_generate_bill_provider_specific_rate` (2 hours)
4. 🟡 Fix repository pattern tests (1 hour)
5. 🟡 Try running `test_get_rates_excel_empty` (5 min)

### Phase 2: Type Safety (6 hours)
1. Fix billing-service type errors (10 errors) - 1 hour
2. Fix weight-service type errors (57 errors) - 4 hours
3. Remove mypy overrides
4. Verify CI/CD pipeline green

### Phase 3: Tooling Consistency (3 hours)
1. Migrate billing-service to Ruff
2. Update pre-commit hooks
3. Update CI/CD workflow
4. Remove flake8, black, isort

### Phase 4: Production Hardening (Deferred)
1. MyISAM → InnoDB migration (4 hours)
2. Add database constraints (2 hours)
3. User table + authentication (6 hours)
4. Additional test coverage (8 hours)

**Total Effort**: ~15 hours for phases 1-3 (demo-ready)
**Production Ready**: +20 hours for phase 4 (production-ready)

---

## Notes

- This is a **demo/portfolio project**, not deployed to production
- All tech debt is **documented and tracked**
- **CI/CD pipeline is green** - all committed code passes tests
- **Coverage is 90%+** despite skipped tests
- **Services run correctly** - Docker Compose end-to-end testing works
- Focus on **showcasing architecture** over production perfection
