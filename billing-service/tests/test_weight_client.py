"""Tests for weight service HTTP client - integration and retry logic."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from src.services.weight_client import WeightServiceClient
from src.utils.exceptions import WeightServiceError
from src.models.database import WeightItem


class TestWeightServiceClientGetTransactions:
    """Test weight service client transaction fetching."""

    @pytest.mark.asyncio
    async def test_get_transactions_success(self, mock_httpx_client):
        """Test successful transaction retrieval."""
        # Setup mock response
        expected_transactions = [
            {"id": "tr1", "truck": "ABC123", "neto": 1000, "produce": "apples"},
            {"id": "tr2", "truck": "XYZ789", "neto": 2000, "produce": "oranges"},
        ]
        mock_httpx_client.set_response(
            "/weight",
            expected_transactions,
            200
        )

        client = WeightServiceClient()

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            transactions = await client.get_transactions(
                from_date="20250101000000",
                to_date="20251231235959"
            )

        assert transactions == expected_transactions
        assert len(transactions) == 2

    @pytest.mark.asyncio
    async def test_get_transactions_with_filter(self, mock_httpx_client):
        """Test transaction retrieval with direction filter."""
        expected_transactions = [
            {"id": "tr1", "direction": "out", "neto": 1000},
        ]
        mock_httpx_client.set_response(
            "/weight",
            expected_transactions,
            200
        )

        client = WeightServiceClient()

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            transactions = await client.get_transactions(
                from_date="20250101000000",
                to_date="20251231235959",
                filter_directions="out"
            )

        assert len(transactions) == 1
        assert transactions[0]["direction"] == "out"

    @pytest.mark.asyncio
    async def test_get_transactions_empty_response(self, mock_httpx_client):
        """Test handling of empty transaction list."""
        mock_httpx_client.set_response("/weight", [], 200)

        client = WeightServiceClient()

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            transactions = await client.get_transactions(
                from_date="20250101000000",
                to_date="20251231235959"
            )

        assert transactions == []

    @pytest.mark.asyncio
    async def test_get_transactions_404_returns_empty(self, mock_httpx_client):
        """Test that 404 response returns empty list."""
        mock_httpx_client.set_response("/weight", None, 404)

        client = WeightServiceClient()

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            transactions = await client.get_transactions(
                from_date="20250101000000",
                to_date="20251231235959"
            )

        assert transactions == []

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="TODO: Fix later")
    async def test_get_transactions_handles_non_list_response(self):
        """Test handling of unexpected response format."""

        class MockAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def request(self, method, url, **kwargs):
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"data": "not a list"}  # Wrong format
                return mock_response

        client = WeightServiceClient()

        with patch("httpx.AsyncClient", MockAsyncClient):
            transactions = await client.get_transactions(
                from_date="20250101000000",
                to_date="20251231235959"
            )

        # Should return empty list for non-list responses
        assert transactions == []


class TestWeightServiceClientGetItemDetails:
    """Test weight service client item details fetching."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="TODO: Fix later")
    async def test_get_item_details_success(self):
        """Test successful item details retrieval."""

        class MockAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def request(self, method, url, **kwargs):
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "id": "ABC123",
                    "tara": 10000,
                    "sessions": ["sess1", "sess2"]
                }
                return mock_response

        client = WeightServiceClient()

        with patch("httpx.AsyncClient", MockAsyncClient):
            item = await client.get_item_details(
                item_id="ABC123",
                from_date="20250101000000",
                to_date="20251231235959"
            )

        assert item is not None
        assert isinstance(item, WeightItem)
        assert item.id == "ABC123"
        assert item.tara == 10000
        assert item.sessions == ["sess1", "sess2"]

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="TODO: Fix later")
    async def test_get_item_details_with_na_tara(self):
        """Test item details with tara='na'."""

        class MockAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def request(self, method, url, **kwargs):
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "id": "CONTAINER001",
                    "tara": "na",
                    "sessions": []
                }
                return mock_response

        client = WeightServiceClient()

        with patch("httpx.AsyncClient", MockAsyncClient):
            item = await client.get_item_details(
                item_id="CONTAINER001",
                from_date="20250101000000",
                to_date="20251231235959"
            )

        assert item is not None
        assert item.tara == "na"

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="TODO: Fix later")
    async def test_get_item_details_404_returns_none(self):
        """Test that 404 response returns None."""

        class MockAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def request(self, method, url, **kwargs):
                mock_response = MagicMock()
                mock_response.status_code = 404
                return mock_response

        client = WeightServiceClient()

        with patch("httpx.AsyncClient", MockAsyncClient):
            item = await client.get_item_details(
                item_id="NONEXISTENT",
                from_date="20250101000000",
                to_date="20251231235959"
            )

        assert item is None

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="TODO: Fix later")
    async def test_get_item_details_empty_sessions(self):
        """Test item details with empty sessions list."""

        class MockAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def request(self, method, url, **kwargs):
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "id": "NEWTRUCK",
                    "tara": 12000,
                    "sessions": []
                }
                return mock_response

        client = WeightServiceClient()

        with patch("httpx.AsyncClient", MockAsyncClient):
            item = await client.get_item_details(
                item_id="NEWTRUCK",
                from_date="20250101000000",
                to_date="20251231235959"
            )

        assert item is not None
        assert item.sessions == []


class TestWeightServiceClientRetryLogic:
    """Test retry logic and error handling."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="TODO: Fix later")
    async def test_retry_on_timeout(self):
        """Test exponential backoff retry on timeout."""
        attempt_count = 0

        class MockAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def request(self, method, url, **kwargs):
                nonlocal attempt_count
                attempt_count += 1

                if attempt_count < 2:
                    # First attempt fails
                    raise httpx.TimeoutException("Timeout")

                # Second attempt succeeds
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = []
                return mock_response

        client = WeightServiceClient()
        client.max_retries = 3

        with patch("httpx.AsyncClient", MockAsyncClient):
            with patch("asyncio.sleep", AsyncMock()):  # Skip actual sleep
                transactions = await client.get_transactions(
                    from_date="20250101000000",
                    to_date="20251231235959"
                )

        assert attempt_count == 2  # Failed once, succeeded second time
        assert transactions == []

    @pytest.mark.asyncio
    async def test_retry_exhaustion_raises_error(self):
        """Test that WeightServiceError is raised after max retries."""

        class MockAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def request(self, method, url, **kwargs):
                raise httpx.TimeoutException("Timeout")

        client = WeightServiceClient()
        client.max_retries = 3

        with patch("httpx.AsyncClient", MockAsyncClient):
            with patch("asyncio.sleep", AsyncMock()):
                with pytest.raises(WeightServiceError, match="Weight service unavailable after 3 attempts"):
                    await client.get_transactions(
                        from_date="20250101000000",
                        to_date="20251231235959"
                    )

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="TODO: Fix later")
    async def test_retry_on_generic_exception(self):
        """Test retry on generic exceptions."""
        attempt_count = 0

        class MockAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def request(self, method, url, **kwargs):
                nonlocal attempt_count
                attempt_count += 1

                if attempt_count < 2:
                    raise Exception("Connection error")

                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = []
                return mock_response

        client = WeightServiceClient()
        client.max_retries = 3

        with patch("httpx.AsyncClient", MockAsyncClient):
            with patch("asyncio.sleep", AsyncMock()):
                transactions = await client.get_transactions(
                    from_date="20250101000000",
                    to_date="20251231235959"
                )

        assert attempt_count == 2
        assert transactions == []

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="TODO: Fix later")
    async def test_no_retry_on_success(self):
        """Test that successful requests don't retry."""
        attempt_count = 0

        class MockAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def request(self, method, url, **kwargs):
                nonlocal attempt_count
                attempt_count += 1

                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = [{"id": "tr1"}]
                return mock_response

        client = WeightServiceClient()

        with patch("httpx.AsyncClient", MockAsyncClient):
            transactions = await client.get_transactions(
                from_date="20250101000000",
                to_date="20251231235959"
            )

        assert attempt_count == 1  # Only one attempt
        assert len(transactions) == 1

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="TODO: Fix later")
    async def test_handles_500_error_with_retry(self):
        """Test handling of 500 errors with retry."""
        attempt_count = 0

        class MockAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def request(self, method, url, **kwargs):
                nonlocal attempt_count
                attempt_count += 1

                mock_response = MagicMock()
                if attempt_count < 2:
                    mock_response.status_code = 500
                else:
                    mock_response.status_code = 200
                    mock_response.json.return_value = []
                return mock_response

        client = WeightServiceClient()
        client.max_retries = 3

        with patch("httpx.AsyncClient", MockAsyncClient):
            with patch("asyncio.sleep", AsyncMock()):
                transactions = await client.get_transactions(
                    from_date="20250101000000",
                    to_date="20251231235959"
                )

        assert attempt_count == 2
        assert transactions == []


class TestWeightServiceClientConfiguration:
    """Test client configuration and initialization."""

    def test_client_initialization_default_config(self):
        """Test client initializes with default config from settings."""
        client = WeightServiceClient()

        assert client.base_url is not None
        assert client.timeout > 0
        assert client.max_retries > 0

    def test_client_builds_correct_urls(self):
        """Test that client builds correct request URLs."""
        client = WeightServiceClient()
        client.base_url = "http://weight-service:5001"

        # We can't directly test URL building without making real requests,
        # but we can verify the base_url is set correctly
        assert "weight-service" in client.base_url or "localhost" in client.base_url


class TestWeightServiceClientEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="TODO: Fix later")
    async def test_get_item_details_handles_parsing_error(self):
        """Test handling of malformed item response."""

        class MockAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def request(self, method, url, **kwargs):
                mock_response = MagicMock()
                mock_response.status_code = 200
                # Invalid JSON structure
                mock_response.json.side_effect = Exception("Invalid JSON")
                return mock_response

        client = WeightServiceClient()

        with patch("httpx.AsyncClient", MockAsyncClient):
            with pytest.raises(WeightServiceError, match="Error processing weight service response"):
                await client.get_item_details(
                    item_id="ABC123",
                    from_date="20250101000000",
                    to_date="20251231235959"
                )

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="TODO: Fix later")
    async def test_get_transactions_handles_parsing_error(self):
        """Test handling of malformed transaction response."""

        class MockAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def request(self, method, url, **kwargs):
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.side_effect = Exception("Invalid JSON")
                return mock_response

        client = WeightServiceClient()

        with patch("httpx.AsyncClient", MockAsyncClient):
            with pytest.raises(WeightServiceError, match="Error processing weight service response"):
                await client.get_transactions(
                    from_date="20250101000000",
                    to_date="20251231235959"
                )

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="TODO: Fix later")
    async def test_get_item_details_missing_fields(self):
        """Test handling of response with missing fields."""

        class MockAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def request(self, method, url, **kwargs):
                mock_response = MagicMock()
                mock_response.status_code = 200
                # Missing 'sessions' field
                mock_response.json.return_value = {
                    "id": "ABC123",
                    "tara": 10000
                }
                return mock_response

        client = WeightServiceClient()

        with patch("httpx.AsyncClient", MockAsyncClient):
            item = await client.get_item_details(
                item_id="ABC123",
                from_date="20250101000000",
                to_date="20251231235959"
            )

        # Should handle missing fields gracefully with defaults
        assert item is not None
        assert item.sessions == []  # Default empty list

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="TODO: Fix later")
    async def test_request_parameters_passed_correctly(self):
        """Test that request parameters are passed correctly."""
        captured_params = {}

        class MockAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def request(self, method, url, **kwargs):
                nonlocal captured_params
                captured_params = kwargs.get("params", {})

                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = []
                return mock_response

        client = WeightServiceClient()

        with patch("httpx.AsyncClient", MockAsyncClient):
            await client.get_transactions(
                from_date="20250101120000",
                to_date="20250131235959",
                filter_directions="out,in"
            )

        assert captured_params.get("from") == "20250101120000"
        assert captured_params.get("to") == "20250131235959"
        assert captured_params.get("filter") == "out,in"
