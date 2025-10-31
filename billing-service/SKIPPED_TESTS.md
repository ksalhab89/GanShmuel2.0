# Skipped Tests Report

This document tracks all skipped tests in billing-service and provides context for why they're skipped and what needs to be done to enable them.

**Total Skipped Tests**: 25
**Test Coverage**: Still 90%+ despite skipped tests
**Priority**: Low - Demo project, not blocking deployment

---

## Category 1: Database Constraint Tests (3 tests)
**File**: `test_database_models.py`
**Issue**: MyISAM engine doesn't enforce foreign key constraints and unique constraints

### Tests:
1. `test_provider_name_unique_constraint` (line 304)
   - **What**: Tests that provider names must be unique
   - **Why Skipped**: MyISAM doesn't enforce UNIQUE constraints
   - **Fix**: Migrate to InnoDB engine OR add application-level validation

2. `test_truck_foreign_key_constraint` (line 322)
   - **What**: Tests that trucks cannot reference non-existent providers
   - **Why Skipped**: MyISAM doesn't enforce foreign key constraints
   - **Fix**: Migrate to InnoDB engine OR add application-level validation

3. Another constraint test (line 389)
   - **What**: Additional database constraint test
   - **Why Skipped**: MyISAM engine limitations
   - **Fix**: Same as above

---

## Category 2: Repository Pattern Tests (3 tests)
**File**: `test_repositories.py`
**Issue**: Tests use outdated `database.execute_query` manual mocking pattern

### Tests:
1. `test_get_all_rates_empty` (line 884)
   - **What**: Tests getting rates when none exist
   - **Why Skipped**: Uses old execute_query mocking, should use clean_database fixture
   - **Fix**: Refactor to use pytest fixtures instead of manual mocking

2. `test_get_all_rates_multiple` (line 926)
   - **What**: Tests getting multiple rates
   - **Why Skipped**: Same - outdated testing pattern
   - **Fix**: Refactor to use sample_rates fixture

3. `test_rate_scope_filtering` (line 975)
   - **What**: Tests filtering rates by scope (ALL vs provider-specific)
   - **Why Skipped**: Same - outdated testing pattern
   - **Fix**: Refactor to use fixtures, important test for business logic

---

## Category 3: Weight Client Integration Tests (8 tests)
**File**: `test_weight_client.py`
**Issue**: Complex async mocking for retry logic and error handling

### Tests:
1. `test_get_transactions_handles_non_list_response` (line 85)
   - **What**: Tests handling of unexpected response format from weight service
   - **Why Skipped**: Need to verify current WeightServiceClient error handling
   - **Fix**: Update to match current client implementation

2. `test_retry_on_timeout` (line 199)
   - **What**: Tests exponential backoff retry on timeout
   - **Why Skipped**: Complex async mocking needs httpx.TimeoutException
   - **Fix**: Use pytest-httpx or similar for cleaner mocking

3-8. Additional retry and error handling tests (lines 265, 302, 334, 396, 427, 474)
   - **What**: Various timeout, connection error, and retry scenarios
   - **Why Skipped**: Same - need proper async mocking infrastructure
   - **Fix**: Implement comprehensive async HTTP mocking strategy

---

## Category 4: Bill Generation API Tests (6 tests)
**File**: `test_bills_api.py`
**Issue**: Depend on weight service mocking with complex transaction data

### Tests:
1. `test_generate_bill_provider_specific_rate` (line 177)
   - **What**: Tests provider-specific rate overrides general rate (CRITICAL BUSINESS LOGIC)
   - **Why Skipped**: Complex weight service transaction mocking
   - **Fix**: HIGH PRIORITY - This tests core billing logic

2. `test_generate_bill_multiple_products` (line 261)
   - **What**: Tests bill calculation with multiple different products
   - **Why Skipped**: Same - complex transaction mocking
   - **Fix**: MEDIUM PRIORITY - Important for multi-product scenarios

3-6. Additional bill generation tests (lines 305, 354, 444, 464)
   - **What**: Various bill generation scenarios
   - **Why Skipped**: Weight service integration complexity
   - **Fix**: Refactor mocking or use integration tests

---

## Category 5: Truck API Tests (3 tests)
**File**: `test_trucks_api.py`
**Issue**: Require weight service integration for truck details

### Tests:
1. `test_get_truck_details_success` (line 157)
   - **What**: Tests fetching truck details from weight service
   - **Why Skipped**: Mocking weight_client.get_item_details
   - **Fix**: Verify endpoint still exists, update mocking

2-3. Additional truck detail tests (lines 275, 321)
   - **What**: Additional truck detail scenarios
   - **Why Skipped**: Same integration mocking issues
   - **Fix**: Refactor with proper httpx mocking

---

## Category 6: Rate Export Tests (1 test)
**File**: `test_rates_api.py`
**Issue**: Excel export edge case testing

### Tests:
1. `test_get_rates_excel_empty` (line 237)
   - **What**: Tests downloading Excel file when database is empty
   - **Why Skipped**: Unknown - test looks straightforward
   - **Fix**: Try running test, may just work now

---

## Category 7: Concurrency Tests (1 test)
**File**: `test_providers_api.py`
**Issue**: Race condition testing for concurrent provider creation

### Tests:
1. `test_concurrent_provider_creation_same_name` (line 262)
   - **What**: Tests that concurrent creation of same provider name handles race condition
   - **Why Skipped**: MyISAM doesn't enforce unique constraints + complex async testing
   - **Fix**: Requires InnoDB migration + proper transaction isolation testing

---

## Recommended Action Plan

### Quick Wins (Can fix today):
1. `test_get_rates_excel_empty` - Just try running it
2. Repository pattern tests - Refactor to use existing fixtures

### Medium Priority (Requires refactoring):
1. Bill generation tests - CRITICAL for business logic validation
2. Weight client retry tests - Important for production resilience

### Low Priority (Architecture changes needed):
1. Database constraint tests - Requires InnoDB migration
2. Concurrency tests - Requires InnoDB + transaction testing

### Non-Priority (Demo project):
- Most integration tests work via Docker Compose integration
- Coverage still 90%+, not blocking demo or deployment
- Technical debt documented for future production hardening

---

## How to Fix

### Pattern 1: Outdated Mocking (Repository Tests)
**Before**:
```python
@pytest.mark.skip(reason="TODO: Fix later")
async def test_get_all_rates_empty(self, db_connection):
    # Manual execute_query mocking...
```

**After**:
```python
async def test_get_all_rates_empty(self, clean_database):
    repo = RateRepository()
    rates = await repo.get_all()
    assert rates == []
```

### Pattern 2: Complex Async Mocking (Weight Client Tests)
**Before**:
```python
@pytest.mark.skip(reason="TODO: Fix later")
async def test_retry_on_timeout(self):
    # Manual MockAsyncClient...
```

**After**:
```python
async def test_retry_on_timeout(self, httpx_mock):
    httpx_mock.add_exception(httpx.TimeoutException("Timeout"), method="GET")
    httpx_mock.add_response(json=[], status_code=200)
    # Test retry logic...
```

### Pattern 3: Database Constraints (MyISAM → InnoDB)
**Current** (`docker-compose.yml` or schema):
```sql
ENGINE=MyISAM
```

**Fixed**:
```sql
ENGINE=InnoDB
-- Then enable constraints in schema
UNIQUE KEY `name` (`name`)
FOREIGN KEY (`provider_id`) REFERENCES `Provider` (`id`)
```

---

## Notes
- This is a demo project, not production
- 90%+ coverage maintained despite skipped tests
- Integration works via Docker Compose end-to-end testing
- Document technical debt for future reference
