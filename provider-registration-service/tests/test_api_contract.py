"""
Provider Registration Service - API Contract Tests
Shift-Left: Define expected API behavior BEFORE implementation

These tests define the contract that Backend-1 and Backend-2 must implement.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.usefixtures("setup_test_database")


class TestCandidateRegistrationContract:
    """
    API Contract: POST /candidates

    Expected behavior defined for Backend-1 to implement
    """

    @pytest.mark.asyncio
    async def test_create_candidate_success(
        self, test_client: AsyncClient, sample_candidate_data
    ):
        """
        CONTRACT: POST /candidates with valid data should return 201

        Response must include:
        - candidate_id (UUID)
        - status ("pending")
        - company_name (echoed from request)
        - contact_email (echoed from request)
        - created_at (timestamp)
        """
        response = await test_client.post("/candidates", json=sample_candidate_data)

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "candidate_id" in data
        assert "status" in data
        assert "company_name" in data
        assert "contact_email" in data
        assert "created_at" in data

        # Verify values
        assert data["status"] == "pending"
        assert data["company_name"] == sample_candidate_data["company_name"]
        assert data["contact_email"] == sample_candidate_data["contact_email"]

    @pytest.mark.asyncio
    async def test_create_candidate_validation_error(
        self, test_client: AsyncClient, invalid_candidate_data
    ):
        """
        CONTRACT: POST /candidates with invalid data should return 422
        """
        response = await test_client.post("/candidates", json=invalid_candidate_data)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data  # Pydantic validation error

    @pytest.mark.asyncio
    async def test_create_candidate_duplicate_email(
        self, test_client: AsyncClient, sample_candidate_data
    ):
        """
        CONTRACT: Duplicate email should return 409 Conflict
        """
        # First registration should succeed
        response1 = await test_client.post("/candidates", json=sample_candidate_data)
        assert response1.status_code == 201

        # Second registration with same email should fail
        response2 = await test_client.post("/candidates", json=sample_candidate_data)
        assert response2.status_code == 409


class TestCandidateListContract:
    """
    API Contract: GET /candidates

    Expected behavior for listing candidates with filters
    """

    @pytest.mark.asyncio
    async def test_list_candidates_empty(self, test_client: AsyncClient):
        """
        CONTRACT: GET /candidates should return empty list when no candidates exist
        """
        response = await test_client.get("/candidates")

        assert response.status_code == 200
        data = response.json()

        assert "candidates" in data
        assert "pagination" in data
        assert isinstance(data["candidates"], list)
        assert len(data["candidates"]) == 0
        assert data["pagination"]["total"] == 0

    @pytest.mark.asyncio
    async def test_list_candidates_with_status_filter(self, test_client: AsyncClient):
        """
        CONTRACT: GET /candidates?status=pending should filter by status
        """
        response = await test_client.get("/candidates?status=pending")

        assert response.status_code == 200
        data = response.json()

        # All returned candidates should have status='pending'
        for candidate in data["candidates"]:
            assert candidate["status"] == "pending"

    @pytest.mark.asyncio
    async def test_list_candidates_with_product_filter(self, test_client: AsyncClient):
        """
        CONTRACT: GET /candidates?product=apples should filter by product
        """
        response = await test_client.get("/candidates?product=apples")

        assert response.status_code == 200
        data = response.json()

        # All returned candidates should have 'apples' in their products
        for candidate in data["candidates"]:
            assert "products" in candidate
            assert "apples" in candidate["products"]

    @pytest.mark.asyncio
    async def test_list_candidates_pagination(self, test_client: AsyncClient):
        """
        CONTRACT: GET /candidates?limit=10&offset=0 should paginate results
        """
        response = await test_client.get("/candidates?limit=10&offset=0")

        assert response.status_code == 200
        data = response.json()

        assert "pagination" in data
        assert data["pagination"]["limit"] == 10
        assert data["pagination"]["offset"] == 0
        assert "total" in data["pagination"]


class TestCandidateApprovalContract:
    """
    API Contract: POST /candidates/{id}/approve

    Expected behavior for approving candidates and billing integration
    """

    @pytest.mark.asyncio
    async def test_approve_candidate_success(
        self, test_client: AsyncClient, sample_candidate_data
    ):
        """
        CONTRACT: POST /candidates/{id}/approve should:
        1. Update candidate status to 'approved'
        2. Call billing service to create provider
        3. Store provider_id from billing service
        4. Return approval response
        """
        # First create a candidate
        create_response = await test_client.post(
            "/candidates", json=sample_candidate_data
        )
        candidate_id = create_response.json()["candidate_id"]

        # Then approve it
        approve_response = await test_client.post(
            f"/candidates/{candidate_id}/approve"
        )

        assert approve_response.status_code == 200
        data = approve_response.json()

        # Verify response structure
        assert "candidate_id" in data
        assert "status" in data
        assert "provider_id" in data

        # Verify values
        assert data["candidate_id"] == candidate_id
        assert data["status"] == "approved"
        assert isinstance(data["provider_id"], int)

    @pytest.mark.asyncio
    async def test_approve_candidate_not_found(self, test_client: AsyncClient):
        """
        CONTRACT: Approving non-existent candidate should return 404
        """
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await test_client.post(f"/candidates/{fake_uuid}/approve")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_approve_candidate_already_approved(
        self, test_client: AsyncClient, sample_candidate_data
    ):
        """
        CONTRACT: Approving already-approved candidate should return 400
        """
        # Create and approve
        create_response = await test_client.post(
            "/candidates", json=sample_candidate_data
        )
        candidate_id = create_response.json()["candidate_id"]
        await test_client.post(f"/candidates/{candidate_id}/approve")

        # Try to approve again
        response = await test_client.post(f"/candidates/{candidate_id}/approve")

        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_approve_candidate_billing_service_failure(
        self, test_client: AsyncClient, sample_candidate_data, monkeypatch
    ):
        """
        CONTRACT: If billing service fails, should return 502 Bad Gateway
        """
        from unittest.mock import AsyncMock
        from src.services.billing_client import BillingServiceError

        # Create candidate
        create_response = await test_client.post(
            "/candidates", json=sample_candidate_data
        )
        candidate_id = create_response.json()["candidate_id"]

        # Mock billing service to fail
        async def mock_create_provider(*args, **kwargs):
            raise BillingServiceError("Billing service unavailable")

        from src.routers import candidates
        original_billing_client = candidates.BillingClient

        class MockBillingClient:
            create_provider = mock_create_provider

        monkeypatch.setattr(candidates, "BillingClient", lambda: MockBillingClient())

        # Approval should fail gracefully
        response = await test_client.post(f"/candidates/{candidate_id}/approve")

        assert response.status_code == 502
        assert "billing" in response.json()["detail"].lower()


class TestHealthEndpointContract:
    """
    API Contract: GET /health

    Required for monitoring and Docker healthchecks
    """

    @pytest.mark.asyncio
    async def test_health_endpoint(self, test_client: AsyncClient):
        """
        CONTRACT: GET /health should return service status
        """
        response = await test_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "status" in data
        assert "service" in data
        assert "version" in data

        # Expected values
        assert data["status"] == "healthy"
        assert data["service"] == "provider-registration-service"
        assert data["version"] == "1.0.0"


class TestMetricsEndpointContract:
    """
    API Contract: GET /metrics

    Required for Prometheus monitoring
    """

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, test_client: AsyncClient):
        """
        CONTRACT: GET /metrics should return Prometheus format
        """
        response = await test_client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")

        # Should contain service uptime metric
        content = response.text
        assert "provider_service_up" in content
        assert "provider_service_requests_total" in content
