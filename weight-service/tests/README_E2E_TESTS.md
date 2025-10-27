# Weight Service  - End-to-End Tests

This directory contains comprehensive end-to-end tests for the Weight Service  API, covering all real-world scenarios and edge cases discovered during manual testing.

## Test Files Overview

### 1. `test_e2e_workflows.py` - Core API Workflows
**Purpose**: Tests fundamental API functionality and user workflows

**Test Classes**:
- `TestHealthAndDiscovery` - System health and API documentation
- `TestEmptySystemState` - Behavior with no existing data
- `TestInputValidation` - Comprehensive input validation tests
- `TestBasicWeighingWorkflow` - Core weighing operations
- `TestBusinessLogicValidation` - Business rule enforcement
- `TestQueryAndFiltering` - Query functionality and filters
- `TestSessionManagement` - Session handling and UUIDs
- `TestCompleteWorkflows` - End-to-end business scenarios
- `TestErrorHandlingAndRecovery` - Error recovery and system resilience

**Key Scenarios Tested**:
- ✅ Health check functionality
- ✅ API documentation accessibility
- ✅ Input validation (negative weights, invalid formats, etc.)
- ✅ Basic IN/OUT/NONE transaction workflows
- ✅ Business rule enforcement (OUT without IN rejection)
- ✅ Unknown container detection
- ✅ Force flag functionality
- ✅ Unit conversion (lbs to kg)
- ✅ Date range queries and filtering
- ✅ Error handling and system recovery

### 2. `test_e2e_performance.py` - Performance and Load Testing
**Purpose**: Tests system performance and scalability characteristics

**Test Classes**:
- `TestPerformanceBasics` - Basic response time validation
- `TestConcurrentOperations` - Multi-threaded operation tests
- `TestScalabilityLimits` - System behavior under load
- `TestResourceUsagePatterns` - Resource-intensive scenarios
- `TestMemoryAndStateManagement` - Memory usage and consistency

**Key Scenarios Tested**:
- ✅ Response time benchmarks (health < 1s, weight recording < 2s)
- ✅ Concurrent weight recordings (10 simultaneous transactions)
- ✅ Large container shipments (50+ containers per transaction)
- ✅ Rapid sequential transactions (20 transactions in <10s)
- ✅ Session ID uniqueness at scale (100 unique UUIDs)
- ✅ System recovery after high load
- ✅ Mixed read/write operations under load

### 3. `test_e2e_batch_operations.py` - File Upload and Batch Processing
**Purpose**: Tests batch file upload functionality and file processing

**Test Classes**:
- `TestBatchFileValidation` - File security and validation
- `TestCSVFileProcessing` - CSV file handling
- `TestJSONFileProcessing` - JSON file handling
- `TestBatchUploadIntegration` - Integration with weighing operations
- `TestBatchProcessingEdgeCases` - Edge cases and special scenarios

**Key Scenarios Tested**:
- ✅ File validation and security (path traversal prevention)
- ✅ CSV processing (kg/lbs formats, headers, invalid rows)
- ✅ JSON processing (valid/invalid structures, mixed units)
- ✅ Large file handling (1000+ containers)
- ✅ Batch upload → weighing workflow integration
- ✅ Error handling in file processing
- ✅ Unicode and special character handling

### 4. `test_e2e_business_scenarios.py` - Complex Business Scenarios
**Purpose**: Tests complex real-world business scenarios and operational patterns

**Test Classes**:
- `TestComplexWeighingScenarios` - Multi-trip and complex weighing patterns
- `TestBusinessRuleEnforcement` - Advanced business rule validation
- `TestTimeBasedScenarios` - Time-related operations and queries
- `TestErrorRecoveryScenarios` - Complex error recovery patterns
- `TestRealWorldOperationalScenarios` - Realistic operational simulations

**Key Scenarios Tested**:
- ✅ Same truck multiple trips per day
- ✅ Incomplete session handling
- ✅ Container reuse across different trucks
- ✅ Large container shipments (20+ containers)
- ✅ Weight consistency validation
- ✅ Busy morning rush simulation (10 trucks)
- ✅ End-of-day reporting scenarios
- ✅ Mixed operations throughout the day
- ✅ Error recovery and system resilience

## Running the Tests

### Prerequisites
1. **Docker containers running**:
   ```bash
   docker-compose up weight-db weight-service
   ```

2. **Service healthy**:
   ```bash
   curl http://localhost:5001/health
   # Should return: {"status": "OK", "database": "OK"}
   ```

### Test Execution Options

#### Run All E2E Tests
```bash
cd weight-service
uv run pytest tests/test_e2e_*.py -v
```

#### Run Specific Test File
```bash
# Core workflows
uv run pytest tests/test_e2e_workflows.py -v

# Performance tests  
uv run pytest tests/test_e2e_performance.py -v

# Batch operations
uv run pytest tests/test_e2e_batch_operations.py -v

# Business scenarios
uv run pytest tests/test_e2e_business_scenarios.py -v
```

#### Run Specific Test Class
```bash
# Test only input validation
uv run pytest tests/test_e2e_workflows.py::TestInputValidation -v

# Test only performance basics
uv run pytest tests/test_e2e_performance.py::TestPerformanceBasics -v
```

#### Run Specific Test Method
```bash
# Test specific functionality
uv run pytest tests/test_e2e_workflows.py::TestHealthAndDiscovery::test_health_check_works -v
```

### Test Configuration

#### For Local Testing
Tests assume the Weight Service  is running at `http://localhost:5001`. If using different port:

```python
# Modify client fixture in test files
@pytest.fixture
def client():
    app.base_url = "http://localhost:5004"  # Change port if needed
    return TestClient(app)
```

#### For CI/CD Integration
Tests can be configured for automated testing:

```bash
# Run with coverage
uv run pytest tests/test_e2e_*.py --cov=src --cov-report=html

# Run with detailed output
uv run pytest tests/test_e2e_*.py -v --tb=long

# Run only critical tests (fast subset)
uv run pytest tests/test_e2e_workflows.py::TestHealthAndDiscovery tests/test_e2e_workflows.py::TestBasicWeighingWorkflow -v
```

## Test Data Management

### Clean State Testing
Each test class is designed to work with existing data in the system. Tests verify:
- System works with empty state
- System works with existing transactions
- Tests don't interfere with each other

### Test Data Cleanup
Tests create data with distinctive identifiers:
- Truck IDs: `TEST001`, `PERF001`, `BATCH001`, etc.
- Container IDs: `C001`, `WORKFLOW001`, `LARGE001`, etc.
- Session IDs: Generated UUIDs are tracked per test

## Expected Test Results

### Success Criteria
All tests should pass when:
- ✅ Weight Service  is running and healthy
- ✅ Database is connected and accessible
- ✅ All API endpoints are responding correctly
- ✅ Business logic is properly implemented

### Common Failure Patterns

#### Database Connection Issues
```
AssertionError: assert 500 == 200
```
**Solution**: Ensure MySQL database is running and healthy

#### Business Logic Errors
```
AssertionError: assert 400 == 200
# Detail: "Unknown container weights"
```
**Expected**: This is correct behavior for business rule enforcement

#### Performance Issues
```
AssertionError: assert 3.5 < 2.0  # Response time too slow
```
**Investigation**: Check system load and database performance

### Test Coverage Statistics

The E2E tests provide comprehensive coverage:
- **API Endpoints**: 7/7 endpoints tested (100%)
- **HTTP Methods**: GET, POST tested
- **Status Codes**: 200, 400, 404, 422, 500 tested
- **Business Rules**: All major rules validated
- **Edge Cases**: 50+ edge cases covered
- **Performance**: Response time and concurrency tested
- **Security**: Input validation and file security tested

## Integration with Development Workflow

### Pre-Commit Testing
```bash
# Quick health check
uv run pytest tests/test_e2e_workflows.py::TestHealthAndDiscovery -v

# Core functionality check
uv run pytest tests/test_e2e_workflows.py::TestBasicWeighingWorkflow -v
```

### Pre-Release Testing
```bash
# Full test suite
uv run pytest tests/test_e2e_*.py -v --tb=short

# Performance validation
uv run pytest tests/test_e2e_performance.py -v
```

### Production Readiness Validation
```bash
# Critical path testing
uv run pytest tests/test_e2e_workflows.py::TestCompleteWorkflows -v

# Load testing
uv run pytest tests/test_e2e_performance.py::TestConcurrentOperations -v

# Business scenario validation
uv run pytest tests/test_e2e_business_scenarios.py::TestRealWorldOperationalScenarios -v
```

## Extending the Tests

### Adding New Test Scenarios
1. **Identify the test category** (workflows, performance, batch, business)
2. **Add to appropriate test file**
3. **Follow naming conventions**: `test_descriptive_name`
4. **Use distinctive test data**: Unique prefixes for identifiers
5. **Include assertions for**:
   - Expected HTTP status codes
   - Response data validation
   - System state verification

### Test Data Patterns
```python
# Good test data patterns
truck_id = "NEWTEST001"  # Unique prefix + sequence
containers = "NT001,NT002"  # Related to test name
weight = 5000 + test_variation  # Realistic values

# Bad patterns
truck_id = "ABC123"  # Generic, might conflict
containers = "C001"  # Too generic
weight = 999999  # Unrealistic
```

The E2E tests provide comprehensive validation of the Weight Service  API, ensuring all functionality works correctly in real-world scenarios and edge cases.