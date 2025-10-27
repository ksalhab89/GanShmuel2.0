"""
Concurrency Control Tests
Verify race conditions are prevented with optimistic locking

TDD Approach: These tests are written BEFORE implementation
Expected: Tests will FAIL until optimistic locking is implemented
"""

import pytest
import asyncio
from uuid import uuid4

pytestmark = pytest.mark.asyncio


class TestConcurrentApprovalPrevention:
    """Test optimistic locking prevents duplicate approvals"""

    async def test_concurrent_approval_race_condition(self, test_client, setup_test_database, sample_candidate_data, admin_token):
        """
        CONCURRENCY TEST: 10 simultaneous approvals
        Expected: Only ONE approval succeeds, others get 409/400
        """
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        assert create_resp.status_code == 201
        candidate_id = create_resp.json()["candidate_id"]

        # Define approval function
        async def approve():
            try:
                return await test_client.post(
                    f"/candidates/{candidate_id}/approve",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
            except Exception as e:
                return e

        # Execute 10 concurrent approval requests
        results = await asyncio.gather(
            *[approve() for _ in range(10)],
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

        # CRITICAL: Exactly ONE approval should succeed
        assert success_count == 1, f"Expected 1 success, got {success_count}"
        assert conflict_count == 9, f"Expected 9 conflicts, got {conflict_count}"

    async def test_100_concurrent_approvals_stress_test(self, test_client, setup_test_database, sample_candidate_data, admin_token):
        """
        STRESS TEST: 100 parallel approvals
        Expected: Exactly 1 success under high concurrency
        """
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = create_resp.json()["candidate_id"]

        # Execute 100 concurrent requests
        async def approve():
            try:
                return await test_client.post(
                    f"/candidates/{candidate_id}/approve",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
            except:
                return None

        results = await asyncio.gather(*[approve() for _ in range(100)])

        # Count successes
        successes = [r for r in results if r and hasattr(r, 'status_code') and r.status_code == 200]

        # CRITICAL: Must be exactly 1 success
        assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}"

    async def test_version_increments_on_update(self, test_client, setup_test_database, sample_candidate_data, admin_token):
        """
        CONCURRENCY TEST: Version increments on each update
        Expected: version field increases
        """
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = create_resp.json()["candidate_id"]

        # Get initial version
        get_resp = await test_client.get(f"/candidates/{candidate_id}")
        initial_version = get_resp.json()["version"]
        assert initial_version == 1, "Initial version should be 1"

        # Approve (should increment version)
        approve_resp = await test_client.post(
            f"/candidates/{candidate_id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert approve_resp.status_code == 200

        # Get updated version
        get_resp2 = await test_client.get(f"/candidates/{candidate_id}")
        updated_version = get_resp2.json()["version"]

        assert updated_version == 2, f"Expected version 2, got {updated_version}"

    async def test_version_field_in_response(self, test_client, setup_test_database, sample_candidate_data):
        """
        SCHEMA TEST: Verify version field is included in API responses
        """
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        assert create_resp.status_code == 201

        response_data = create_resp.json()
        assert "version" in response_data, "version field must be in create response"
        assert response_data["version"] == 1, "New candidates should have version=1"

    async def test_optimistic_locking_prevents_stale_updates(self, test_client, setup_test_database, sample_candidate_data, admin_token):
        """
        OPTIMISTIC LOCKING TEST: Verify stale version is rejected
        Expected: If candidate changes between read and update, update fails
        """
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = create_resp.json()["candidate_id"]

        # First approval should succeed
        approve_resp1 = await test_client.post(
            f"/candidates/{candidate_id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert approve_resp1.status_code == 200

        # Second approval should fail (candidate already approved)
        approve_resp2 = await test_client.post(
            f"/candidates/{candidate_id}/approve",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert approve_resp2.status_code in [400, 409], "Second approval should fail"

    async def test_concurrent_approvals_different_candidates(self, test_client, setup_test_database, sample_candidate_data, admin_token):
        """
        ISOLATION TEST: Concurrent approvals of DIFFERENT candidates should all succeed
        Expected: No interference between different candidate approvals
        """
        # Create 10 different candidates
        candidate_ids = []
        for i in range(10):
            data = sample_candidate_data.copy()
            data["contact_email"] = f"test{i}@fruits.com"
            data["company_name"] = f"Test Fruits Ltd {i}"
            create_resp = await test_client.post("/candidates", json=data)
            assert create_resp.status_code == 201
            candidate_ids.append(create_resp.json()["candidate_id"])

        # Approve all candidates concurrently
        async def approve(cid):
            try:
                return await test_client.post(
                    f"/candidates/{cid}/approve",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
            except Exception as e:
                return e

        results = await asyncio.gather(*[approve(cid) for cid in candidate_ids])

        # All should succeed (different candidates = no conflict)
        success_count = sum(
            1 for r in results
            if hasattr(r, 'status_code') and r.status_code == 200
        )

        assert success_count == 10, f"Expected 10 successes for different candidates, got {success_count}"
