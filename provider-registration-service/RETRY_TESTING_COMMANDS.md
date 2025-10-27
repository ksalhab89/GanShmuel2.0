# Retry Logic Testing Commands

## Run All Retry Tests

```bash
# Docker
docker run --rm -v "/c/Users/ksalh/IdeaProjects/gan-shmuel-2/provider-registration-service:/app" provider-test pytest tests/test_billing_retry.py -v

# Expected: 11 passed
```

## Run Single Test

```bash
# Test retry on 500 error
docker run --rm -v "/c/Users/ksalh/IdeaProjects/gan-shmuel-2/provider-registration-service:/app" provider-test pytest tests/test_billing_retry.py::TestBillingServiceRetry::test_retry_on_500_error -v
```

## Run with Coverage

```bash
docker run --rm -v "/c/Users/ksalh/IdeaProjects/gan-shmuel-2/provider-registration-service:/app" provider-test pytest tests/test_billing_retry.py --cov=src/services/billing_client --cov-report=html
```

## Rebuild Test Image

```bash
cd /c/Users/ksalh/IdeaProjects/gan-shmuel-2/provider-registration-service
docker build -f Dockerfile.test -t provider-test .
```

## Test Results

✅ **11/11 Tests Passing**

- `test_retry_on_500_error` - Retries on server errors
- `test_retry_on_503_service_unavailable` - Retries on service unavailable
- `test_no_retry_on_400_client_error` - No retry on client errors
- `test_no_retry_on_404_not_found` - No retry on not found
- `test_exponential_backoff_timing` - Verifies delay timing
- `test_retry_after_header_respected` - Respects rate limiting
- `test_max_retries_exhausted` - Gives up after max attempts
- `test_timeout_with_retry` - Retries on timeout
- `test_connection_error_with_retry` - Retries on connection error
- `test_retry_on_502_bad_gateway` - Retries on bad gateway
- `test_retry_on_504_gateway_timeout` - Retries on gateway timeout
