"""Tests for billing service integration."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, TimeoutException, HTTPStatusError, Response
from src.services.billing_client import BillingServiceError

pytestmark = pytest.mark.usefixtures("setup_test_database")


class TestBillingIntegration:
    """Test suite for billing service integration scenarios"""

    @pytest.mark.asyncio
    async def test_approve_creates_provider_in_billing(
        self, test_client: AsyncClient, sample_candidate_data
    ):
        """Verify provider created in billing service on approval."""
        # Create candidate
        response = await test_client.post("/candidates", json=sample_candidate_data)
        assert response.status_code == 201
        candidate_id = response.json()["candidate_id"]

        # Approve candidate - this should call billing service
        response = await test_client.post(f"/candidates/{candidate_id}/approve")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert "provider_id" in data
        assert data["provider_id"] is not None
        assert isinstance(data["provider_id"], int)

    @pytest.mark.asyncio
    async def test_billing_service_timeout_handling(
        self, test_client: AsyncClient, sample_candidate_data, monkeypatch
    ):
        """Test timeout handling for billing service calls."""

        async def mock_timeout(*args, **kwargs):
            raise BillingServiceError("Billing service timeout")

        # Create candidate
        response = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = response.json()["candidate_id"]

        # Mock billing client to timeout
        from src.routers import candidates

        class MockBillingClient:
            create_provider = mock_timeout

        monkeypatch.setattr(candidates, "BillingClient", lambda: MockBillingClient())

        response = await test_client.post(f"/candidates/{candidate_id}/approve")
        assert response.status_code == 502
        assert "billing" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_billing_service_404_error(
        self, test_client: AsyncClient, sample_candidate_data, monkeypatch
    ):
        """Test handling when billing service returns 404."""

        async def mock_404(*args, **kwargs):
            raise BillingServiceError("Billing service returned 404: Not Found")

        # Create candidate
        response = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = response.json()["candidate_id"]

        # Mock billing client to return 404
        from src.routers import candidates

        class MockBillingClient:
            create_provider = mock_404

        monkeypatch.setattr(candidates, "BillingClient", lambda: MockBillingClient())

        response = await test_client.post(f"/candidates/{candidate_id}/approve")
        assert response.status_code == 502
        assert "404" in response.json()["detail"] or "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_billing_service_500_error(
        self, test_client: AsyncClient, sample_candidate_data, monkeypatch
    ):
        """Test handling when billing service returns 500."""

        async def mock_500(*args, **kwargs):
            raise BillingServiceError("Billing service returned 500: Internal Server Error")

        # Create candidate
        response = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = response.json()["candidate_id"]

        # Mock billing client to return 500
        from src.routers import candidates

        class MockBillingClient:
            create_provider = mock_500

        monkeypatch.setattr(candidates, "BillingClient", lambda: MockBillingClient())

        response = await test_client.post(f"/candidates/{candidate_id}/approve")
        assert response.status_code == 502
        assert "500" in response.json()["detail"] or "internal server error" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_billing_service_connection_refused(
        self, test_client: AsyncClient, sample_candidate_data, monkeypatch
    ):
        """Test handling when billing service is unreachable."""

        async def mock_connection_error(*args, **kwargs):
            raise BillingServiceError("Failed to connect to billing service: Connection refused")

        # Create candidate
        response = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = response.json()["candidate_id"]

        # Mock billing client connection error
        from src.routers import candidates

        class MockBillingClient:
            create_provider = mock_connection_error

        monkeypatch.setattr(candidates, "BillingClient", lambda: MockBillingClient())

        response = await test_client.post(f"/candidates/{candidate_id}/approve")
        assert response.status_code == 502
        assert "failed to connect" in response.json()["detail"].lower()
