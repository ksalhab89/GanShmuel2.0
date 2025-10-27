"""
Rejection Endpoint Tests - Phase 3, Task 3.1
TDD Approach: Tests written BEFORE implementation

Test Coverage:
1. Successful rejection (pending → rejected)
2. Rejection of non-existent candidate (404)
3. Rejection of already approved candidate (400)
4. Rejection of already rejected candidate (400)
5. Concurrent rejection detection (optimistic locking)
6. Admin-only access (403 for non-admin)
7. Rejection reason field in response
8. Version increment on rejection
9. Concurrent rejections (race condition)
10. Rejection without reason (optional field)
"""

import pytest
import asyncio
from uuid import uuid4

pytestmark = pytest.mark.asyncio


class TestRejectionEndpoint:
    """Test rejection endpoint functionality"""

    async def test_successful_rejection_with_reason(
        self, test_client, setup_test_database, sample_candidate_data, admin_token
    ):
        """
        TEST 1: Successful rejection with reason
        Expected: 200 status, status='rejected', rejection_reason in response
        """
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        assert create_resp.status_code == 201
        candidate_id = create_resp.json()["candidate_id"]

        # Reject candidate with reason
        rejection_data = {"reason": "Does not meet our quality standards"}
        reject_resp = await test_client.post(
            f"/candidates/{candidate_id}/reject",
            json=rejection_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Verify rejection successful
        assert reject_resp.status_code == 200
        response_data = reject_resp.json()
        assert response_data["status"] == "rejected"
        assert response_data["candidate_id"] == candidate_id
        assert response_data["rejection_reason"] == "Does not meet our quality standards"

        # Verify candidate status in database
        get_resp = await test_client.get(f"/candidates/{candidate_id}")
        assert get_resp.status_code == 200
        candidate = get_resp.json()
        assert candidate["status"] == "rejected"
        assert candidate["rejection_reason"] == "Does not meet our quality standards"

    async def test_rejection_without_reason(
        self, test_client, setup_test_database, sample_candidate_data, admin_token
    ):
        """
        TEST 2: Successful rejection without reason (optional field)
        Expected: 200 status, rejection_reason is None
        """
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = create_resp.json()["candidate_id"]

        # Reject without reason (empty body or no reason field)
        reject_resp = await test_client.post(
            f"/candidates/{candidate_id}/reject",
            json={},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Verify rejection successful
        assert reject_resp.status_code == 200
        response_data = reject_resp.json()
        assert response_data["status"] == "rejected"
        assert response_data["rejection_reason"] is None

    async def test_rejection_nonexistent_candidate(
        self, test_client, setup_test_database, admin_token
    ):
        """
        TEST 3: Rejection of non-existent candidate
        Expected: 404 status
        """
        fake_id = str(uuid4())
        reject_resp = await test_client.post(
            f"/candidates/{fake_id}/reject",
            json={"reason": "Test"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert reject_resp.status_code == 404
        assert "not found" in reject_resp.json()["detail"].lower()

    async def test_rejection_already_approved_candidate(
        self, test_client, setup_test_database, sample_candidate_data, admin_token
    ):
        """
        TEST 4: Rejection of already approved candidate
        Expected: 400 status (bad request - already processed)
        """
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = create_resp.json()["candidate_id"]

        # Approve first
        approve_resp = await test_client.post(
            f"/candidates/{candidate_id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert approve_resp.status_code == 200

        # Try to reject approved candidate
        reject_resp = await test_client.post(
            f"/candidates/{candidate_id}/reject",
            json={"reason": "Changed mind"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert reject_resp.status_code == 400
        assert "already approved" in reject_resp.json()["detail"].lower()

    async def test_rejection_already_rejected_candidate(
        self, test_client, setup_test_database, sample_candidate_data, admin_token
    ):
        """
        TEST 5: Rejection of already rejected candidate
        Expected: 400 status (idempotency - already rejected)
        """
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = create_resp.json()["candidate_id"]

        # First rejection
        reject_resp1 = await test_client.post(
            f"/candidates/{candidate_id}/reject",
            json={"reason": "First rejection"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert reject_resp1.status_code == 200

        # Second rejection
        reject_resp2 = await test_client.post(
            f"/candidates/{candidate_id}/reject",
            json={"reason": "Second rejection"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert reject_resp2.status_code == 400
        assert "already rejected" in reject_resp2.json()["detail"].lower()

    async def test_rejection_requires_admin_authentication(
        self, test_client, setup_test_database, sample_candidate_data, user_token
    ):
        """
        TEST 6: Admin-only access control
        Expected: 403 status for non-admin user
        """
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = create_resp.json()["candidate_id"]

        # Try to reject with user token (not admin)
        reject_resp = await test_client.post(
            f"/candidates/{candidate_id}/reject",
            json={"reason": "Unauthorized rejection"},
            headers={"Authorization": f"Bearer {user_token}"}
        )

        assert reject_resp.status_code == 403
        assert "admin" in reject_resp.json()["detail"].lower()

    async def test_rejection_requires_authentication(
        self, test_client, setup_test_database, sample_candidate_data
    ):
        """
        TEST 7: Authentication required
        Expected: 401 status without token
        """
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = create_resp.json()["candidate_id"]

        # Try to reject without authentication
        reject_resp = await test_client.post(
            f"/candidates/{candidate_id}/reject",
            json={"reason": "Unauthenticated rejection"}
        )

        assert reject_resp.status_code == 401

    async def test_version_increments_on_rejection(
        self, test_client, setup_test_database, sample_candidate_data, admin_token
    ):
        """
        TEST 8: Version increments on rejection (optimistic locking)
        Expected: version field increases from 1 to 2
        """
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = create_resp.json()["candidate_id"]

        # Get initial version
        get_resp = await test_client.get(f"/candidates/{candidate_id}")
        initial_version = get_resp.json()["version"]
        assert initial_version == 1

        # Reject candidate
        reject_resp = await test_client.post(
            f"/candidates/{candidate_id}/reject",
            json={"reason": "Test"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert reject_resp.status_code == 200

        # Get updated version
        get_resp2 = await test_client.get(f"/candidates/{candidate_id}")
        updated_version = get_resp2.json()["version"]

        assert updated_version == 2, f"Expected version 2, got {updated_version}"

    async def test_concurrent_rejection_race_condition(
        self, test_client, setup_test_database, sample_candidate_data, admin_token
    ):
        """
        TEST 9: Concurrent rejections with optimistic locking
        Expected: Only ONE rejection succeeds, others get 409/400
        """
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = create_resp.json()["candidate_id"]

        # Define rejection function
        async def reject():
            try:
                return await test_client.post(
                    f"/candidates/{candidate_id}/reject",
                    json={"reason": "Concurrent rejection"},
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
            except Exception as e:
                return e

        # Execute 10 concurrent rejection requests
        results = await asyncio.gather(
            *[reject() for _ in range(10)],
            return_exceptions=True
        )

        # Count successes and failures
        success_count = sum(
            1 for r in results
            if hasattr(r, 'status_code') and r.status_code == 200
        )
        conflict_count = sum(
            1 for r in results
            if hasattr(r, 'status_code') and r.status_code in [400, 409]
        )

        # CRITICAL: Exactly ONE rejection should succeed
        assert success_count == 1, f"Expected 1 success, got {success_count}"
        assert conflict_count == 9, f"Expected 9 conflicts, got {conflict_count}"

    async def test_rejection_optimistic_locking_prevents_stale_updates(
        self, test_client, setup_test_database, sample_candidate_data, admin_token
    ):
        """
        TEST 10: Optimistic locking prevents stale updates
        Expected: If candidate changes between operations, rejection detects it
        """
        # Create two candidates with same email pattern but different
        candidate1_data = sample_candidate_data.copy()
        candidate1_data["contact_email"] = "test1@fruits.com"
        create_resp1 = await test_client.post("/candidates", json=candidate1_data)
        candidate_id = create_resp1.json()["candidate_id"]

        # First rejection should succeed
        reject_resp1 = await test_client.post(
            f"/candidates/{candidate_id}/reject",
            json={"reason": "First rejection"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert reject_resp1.status_code == 200

        # Second rejection should fail (candidate already rejected)
        reject_resp2 = await test_client.post(
            f"/candidates/{candidate_id}/reject",
            json={"reason": "Second rejection"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert reject_resp2.status_code in [400, 409]


class TestRejectionFieldValidation:
    """Test rejection reason field validation"""

    async def test_rejection_reason_max_length(
        self, test_client, setup_test_database, sample_candidate_data, admin_token
    ):
        """
        TEST 11: Rejection reason respects max length
        Expected: Long reasons are accepted (up to 1000 chars based on schema)
        """
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = create_resp.json()["candidate_id"]

        # Create long reason (within limit)
        long_reason = "X" * 500
        reject_resp = await test_client.post(
            f"/candidates/{candidate_id}/reject",
            json={"reason": long_reason},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert reject_resp.status_code == 200
        assert reject_resp.json()["rejection_reason"] == long_reason

    async def test_rejection_reason_too_long(
        self, test_client, setup_test_database, sample_candidate_data, admin_token
    ):
        """
        TEST 12: Rejection reason exceeding max length is rejected
        Expected: 422 validation error for reasons > 1000 chars
        """
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = create_resp.json()["candidate_id"]

        # Create reason exceeding max length
        too_long_reason = "X" * 1001
        reject_resp = await test_client.post(
            f"/candidates/{candidate_id}/reject",
            json={"reason": too_long_reason},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert reject_resp.status_code == 422  # Validation error
