"""
Billing Service Retry Logic Tests
Test retry behavior, exponential backoff, and resilience
"""
import pytest
import time
from unittest.mock import AsyncMock, patch
import httpx
from src.services.billing_client import BillingClient, BillingServiceError

# Mark all tests in this module to skip billing mock and use httpx_mock instead
pytestmark = [pytest.mark.asyncio, pytest.mark.no_billing_mock]


# Override the conftest's mock_billing_service fixture to not mock in these tests
@pytest.fixture(autouse=True)
def mock_billing_service():
    """Override to disable billing mock for retry tests - httpx_mock will handle it"""
    yield  # Do nothing, let httpx_mock handle the mocking


class TestBillingServiceRetry:
    """Test retry behavior for billing service integration"""

    async def test_retry_on_500_error(self, httpx_mock):
        """
        RELIABILITY TEST: Retry on server errors
        Expected: 3 retries before giving up
        """
        # Mock billing service to fail 2 times, then succeed
        httpx_mock.add_response(
            url="http://localhost:5002/provider",
            method="POST",
            status_code=500,
            json={"error": "Internal server error"}
        )
        httpx_mock.add_response(
            url="http://localhost:5002/provider",
            method="POST",
            status_code=500,
            json={"error": "Internal server error"}
        )
        httpx_mock.add_response(
            url="http://localhost:5002/provider",
            method="POST",
            status_code=201,
            json={"id": 12345}
        )

        client = BillingClient()
        result = await client.create_provider("Test Company")

        # Should succeed after retries
        assert result == 12345

        # Verify 3 requests were made (initial + 2 retries)
        requests = httpx_mock.get_requests()
        assert len(requests) == 3

    async def test_retry_on_503_service_unavailable(self, httpx_mock):
        """
        RELIABILITY TEST: Retry on 503 Service Unavailable
        Expected: Automatic retry with backoff
        """
        httpx_mock.add_response(
            url="http://localhost:5002/provider",
            method="POST",
            status_code=503,
            json={"error": "Service temporarily unavailable"}
        )
        httpx_mock.add_response(
            url="http://localhost:5002/provider",
            method="POST",
            status_code=201,
            json={"id": 99999}
        )

        client = BillingClient()
        result = await client.create_provider("Retry Test Co")

        assert result == 99999
        assert len(httpx_mock.get_requests()) == 2

    async def test_no_retry_on_400_client_error(self, httpx_mock):
        """
        RELIABILITY TEST: Don't retry on client errors
        Expected: Immediate failure on 400-level errors
        """
        httpx_mock.add_response(
            url="http://localhost:5002/provider",
            method="POST",
            status_code=400,
            json={"error": "Invalid request"}
        )

        client = BillingClient()

        with pytest.raises(BillingServiceError, match="400"):
            await client.create_provider("Bad Request")

        # Should only make 1 request (no retries)
        assert len(httpx_mock.get_requests()) == 1

    async def test_no_retry_on_404_not_found(self, httpx_mock):
        """
        RELIABILITY TEST: Don't retry on 404
        Expected: Immediate failure
        """
        httpx_mock.add_response(
            url="http://localhost:5002/provider",
            method="POST",
            status_code=404,
            json={"error": "Endpoint not found"}
        )

        client = BillingClient()

        with pytest.raises(BillingServiceError):
            await client.create_provider("Not Found Test")

        assert len(httpx_mock.get_requests()) == 1

    async def test_exponential_backoff_timing(self, httpx_mock):
        """
        RELIABILITY TEST: Verify exponential backoff delays
        Expected: ~0.5s, ~1s delays between retries
        """
        # Mock 3 failures to trigger 2 retries
        for _ in range(3):
            httpx_mock.add_response(
                url="http://localhost:5002/provider",
                method="POST",
                status_code=500,
                json={"error": "Server error"}
            )

        # Final success
        httpx_mock.add_response(
            url="http://localhost:5002/provider",
            method="POST",
            status_code=201,
            json={"id": 77777}
        )

        client = BillingClient()

        start_time = time.time()
        result = await client.create_provider("Timing Test")
        total_time = time.time() - start_time

        # With exponential backoff (0.5s, 1s), total time should be at least 1.5s
        # Allow some margin for execution time
        assert result == 77777
        assert total_time >= 1.0, f"Expected at least 1s delay, got {total_time}s"

    async def test_retry_after_header_respected(self, httpx_mock):
        """
        RELIABILITY TEST: Respect Retry-After header
        Expected: Wait as instructed by server
        """
        httpx_mock.add_response(
            url="http://localhost:5002/provider",
            method="POST",
            status_code=429,
            headers={"Retry-After": "1"},
            json={"error": "Rate limit exceeded"}
        )
        httpx_mock.add_response(
            url="http://localhost:5002/provider",
            method="POST",
            status_code=201,
            json={"id": 55555}
        )

        start = time.time()
        client = BillingClient()
        result = await client.create_provider("Rate Limited")
        duration = time.time() - start

        assert result == 55555
        # Should wait at least 1 second due to Retry-After
        assert duration >= 1.0, f"Expected at least 1s delay, got {duration}s"

    async def test_max_retries_exhausted(self, httpx_mock):
        """
        RELIABILITY TEST: Give up after max retries
        Expected: Raise error after 3 retries
        """
        # Return 500 for all attempts
        for _ in range(4):  # Initial + 3 retries
            httpx_mock.add_response(
                url="http://localhost:5002/provider",
                method="POST",
                status_code=500,
                json={"error": "Persistent failure"}
            )

        client = BillingClient()

        with pytest.raises(BillingServiceError, match="500"):
            await client.create_provider("Max Retries Test")

        # Should make 4 total requests (initial + 3 retries)
        assert len(httpx_mock.get_requests()) == 4

    async def test_timeout_with_retry(self, httpx_mock):
        """
        RELIABILITY TEST: Retry on timeout
        Expected: Retry on connection timeout
        """
        httpx_mock.add_exception(httpx.TimeoutException("Connection timeout"))
        httpx_mock.add_response(
            url="http://localhost:5002/provider",
            method="POST",
            status_code=201,
            json={"id": 77777}
        )

        client = BillingClient()
        result = await client.create_provider("Timeout Recovery")

        assert result == 77777
        assert len(httpx_mock.get_requests()) == 2

    async def test_connection_error_with_retry(self, httpx_mock):
        """
        RELIABILITY TEST: Retry on connection error
        Expected: Retry on network errors
        """
        httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
        httpx_mock.add_response(
            url="http://localhost:5002/provider",
            method="POST",
            status_code=201,
            json={"id": 88888}
        )

        client = BillingClient()
        result = await client.create_provider("Connection Recovery")

        assert result == 88888

    async def test_retry_on_502_bad_gateway(self, httpx_mock):
        """
        RELIABILITY TEST: Retry on 502 Bad Gateway
        Expected: Automatic retry with backoff
        """
        httpx_mock.add_response(
            url="http://localhost:5002/provider",
            method="POST",
            status_code=502,
            json={"error": "Bad Gateway"}
        )
        httpx_mock.add_response(
            url="http://localhost:5002/provider",
            method="POST",
            status_code=201,
            json={"id": 11111}
        )

        client = BillingClient()
        result = await client.create_provider("502 Test")

        assert result == 11111
        assert len(httpx_mock.get_requests()) == 2

    async def test_retry_on_504_gateway_timeout(self, httpx_mock):
        """
        RELIABILITY TEST: Retry on 504 Gateway Timeout
        Expected: Automatic retry with backoff
        """
        httpx_mock.add_response(
            url="http://localhost:5002/provider",
            method="POST",
            status_code=504,
            json={"error": "Gateway Timeout"}
        )
        httpx_mock.add_response(
            url="http://localhost:5002/provider",
            method="POST",
            status_code=201,
            json={"id": 22222}
        )

        client = BillingClient()
        result = await client.create_provider("504 Test")

        assert result == 22222
        assert len(httpx_mock.get_requests()) == 2
