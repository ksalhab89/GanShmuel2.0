"""
Comprehensive tests for GET /candidates/{id} endpoint
Added in Phase 1, needs full test coverage
"""
import pytest
from uuid import uuid4
from datetime import datetime

pytestmark = pytest.mark.asyncio


class TestGetCandidateEndpoint:
    """Test single candidate retrieval endpoint"""

    async def test_get_existing_candidate_success(
        self,
        test_client,
        sample_candidate_data,
        setup_test_database
    ):
        """
        HAPPY PATH: Get existing candidate by ID
        Expected: 200 OK with all candidate fields
        """
        # Create candidate
        create_resp = await test_client.post(
            "/candidates",
            json=sample_candidate_data
        )
        assert create_resp.status_code == 201
        candidate_id = create_resp.json()["candidate_id"]

        # Get candidate
        response = await test_client.get(f"/candidates/{candidate_id}")

        assert response.status_code == 200
        data = response.json()

        # Verify all fields present
        assert data["candidate_id"] == candidate_id
        assert data["status"] == "pending"
        assert data["company_name"] == sample_candidate_data["company_name"]
        assert data["contact_email"] == sample_candidate_data["contact_email"]
        assert data["phone"] == sample_candidate_data["phone"]
        assert data["products"] == sample_candidate_data["products"]
        assert data["truck_count"] == sample_candidate_data["truck_count"]
        assert data["capacity_tons_per_day"] == sample_candidate_data["capacity_tons_per_day"]
        assert data["location"] == sample_candidate_data["location"]
        assert "created_at" in data
        assert "updated_at" in data
        assert data["provider_id"] is None
        assert data["version"] == 1

    async def test_get_nonexistent_candidate_404(self, test_client, setup_test_database):
        """
        ERROR CASE: Get non-existent candidate
        Expected: 404 Not Found
        """
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await test_client.get(f"/candidates/{fake_uuid}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_get_candidate_invalid_uuid_422(self, test_client, setup_test_database):
        """
        VALIDATION: Invalid UUID format
        Expected: 422 Unprocessable Entity
        """
        response = await test_client.get("/candidates/not-a-valid-uuid")
        assert response.status_code == 422

    async def test_get_candidate_malformed_uuid_422(self, test_client, setup_test_database):
        """
        VALIDATION: Malformed UUID
        Expected: 422 Unprocessable Entity
        """
        response = await test_client.get("/candidates/12345")
        assert response.status_code == 422

    async def test_get_approved_candidate(
        self,
        test_client,
        sample_candidate_data,
        admin_token,
        setup_test_database
    ):
        """
        APPROVED STATE: Get approved candidate
        Expected: 200 OK with provider_id and version=2
        """
        # Create and approve candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = create_resp.json()["candidate_id"]

        headers = {"Authorization": f"Bearer {admin_token}"}
        await test_client.post(
            f"/candidates/{candidate_id}/approve",
            headers=headers
        )

        # Get approved candidate
        response = await test_client.get(f"/candidates/{candidate_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["provider_id"] is not None
        assert data["version"] == 2  # Incremented after approval

    async def test_get_candidate_includes_timestamps(
        self,
        test_client,
        sample_candidate_data,
        setup_test_database
    ):
        """
        DATA INTEGRITY: Timestamps are included and valid
        Expected: created_at and updated_at in ISO format
        """
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = create_resp.json()["candidate_id"]

        response = await test_client.get(f"/candidates/{candidate_id}")
        data = response.json()

        # Verify timestamps exist and are valid ISO format
        assert "created_at" in data
        assert "updated_at" in data

        # Should be parseable as ISO datetime
        datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))

    async def test_get_candidate_response_schema_complete(
        self,
        test_client,
        sample_candidate_data,
        setup_test_database
    ):
        """
        SCHEMA VALIDATION: Response contains ALL required fields
        Expected: All CandidateResponse fields present
        """
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = create_resp.json()["candidate_id"]

        response = await test_client.get(f"/candidates/{candidate_id}")
        data = response.json()

        required_fields = [
            "candidate_id", "status", "company_name", "contact_email",
            "phone", "products", "truck_count", "capacity_tons_per_day",
            "location", "created_at", "updated_at", "provider_id", "version"
        ]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    async def test_get_candidate_no_sql_injection(self, test_client, setup_test_database):
        """
        SECURITY: SQL injection attempts blocked
        Expected: Safe handling of malicious UUIDs
        """
        malicious_inputs = [
            "'; DROP TABLE candidates; --",
            "' OR '1'='1",
            '" UNION SELECT * FROM users --'
        ]

        for malicious in malicious_inputs:
            response = await test_client.get(f"/candidates/{malicious}")

            # Should return 422 (validation error), NOT 500 (SQL error)
            assert response.status_code == 422

    async def test_get_candidate_with_null_optional_fields(
        self,
        test_client,
        setup_test_database
    ):
        """
        NULL HANDLING: Get candidate with null optional fields
        Expected: 200 OK with phone and location as null
        """
        # Create candidate without optional fields
        minimal_data = {
            "company_name": "Minimal Co",
            "contact_email": "minimal@example.com",
            "products": ["apples"],
            "truck_count": 1,
            "capacity_tons_per_day": 1
        }

        create_resp = await test_client.post("/candidates", json=minimal_data)
        candidate_id = create_resp.json()["candidate_id"]

        # Get candidate
        response = await test_client.get(f"/candidates/{candidate_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["phone"] is None
        assert data["location"] is None
        assert data["company_name"] == "Minimal Co"

    async def test_get_candidate_multiple_times_consistent(
        self,
        test_client,
        sample_candidate_data,
        setup_test_database
    ):
        """
        IDEMPOTENCY: Multiple GET requests return same data
        Expected: Consistent responses
        """
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = create_resp.json()["candidate_id"]

        # Get candidate multiple times
        responses = []
        for _ in range(3):
            resp = await test_client.get(f"/candidates/{candidate_id}")
            assert resp.status_code == 200
            responses.append(resp.json())

        # All responses should be identical
        assert responses[0] == responses[1] == responses[2]
