"""
End-to-end integration tests
Test complete workflows across multiple endpoints
"""
import pytest

pytestmark = pytest.mark.asyncio


class TestFullWorkflowIntegration:
    """Test complete workflows from creation to approval"""

    async def test_complete_approval_workflow(
        self,
        test_client,
        sample_candidate_data,
        admin_token,
        setup_test_database
    ):
        """
        E2E TEST: Complete workflow from creation to approval
        """
        # 1. Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        assert create_resp.status_code == 201
        candidate_id = create_resp.json()["candidate_id"]

        # 2. Get candidate (verify pending)
        get_resp = await test_client.get(f"/candidates/{candidate_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "pending"
        assert get_resp.json()["version"] == 1

        # 3. List candidates (verify in list)
        list_resp = await test_client.get("/candidates?status=pending")
        assert list_resp.status_code == 200
        candidate_ids = [c["candidate_id"] for c in list_resp.json()["candidates"]]
        assert candidate_id in candidate_ids

        # 4. Approve candidate
        headers = {"Authorization": f"Bearer {admin_token}"}
        approve_resp = await test_client.post(
            f"/candidates/{candidate_id}/approve",
            headers=headers
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "approved"

        # 5. Get approved candidate (verify version incremented)
        get_approved = await test_client.get(f"/candidates/{candidate_id}")
        assert get_approved.status_code == 200
        data = get_approved.json()
        assert data["status"] == "approved"
        assert data["provider_id"] is not None
        assert data["version"] == 2

        # 6. List approved candidates
        approved_list = await test_client.get("/candidates?status=approved")
        approved_ids = [c["candidate_id"] for c in approved_list.json()["candidates"]]
        assert candidate_id in approved_ids

    async def test_multiple_candidates_workflow(
        self,
        test_client,
        admin_token,
        setup_test_database
    ):
        """
        E2E TEST: Create and manage multiple candidates
        """
        # Create 3 candidates
        candidates = []
        for i in range(3):
            data = {
                "company_name": f"Company {i}",
                "contact_email": f"company{i}@example.com",
                "products": ["apples"],
                "truck_count": 5,
                "capacity_tons_per_day": 100
            }
            resp = await test_client.post("/candidates", json=data)
            assert resp.status_code == 201
            candidates.append(resp.json()["candidate_id"])

        # List all pending candidates
        list_resp = await test_client.get("/candidates?status=pending")
        assert list_resp.status_code == 200
        assert list_resp.json()["pagination"]["total"] >= 3

        # Approve first candidate
        headers = {"Authorization": f"Bearer {admin_token}"}
        approve_resp = await test_client.post(
            f"/candidates/{candidates[0]}/approve",
            headers=headers
        )
        assert approve_resp.status_code == 200

        # Verify counts
        pending_resp = await test_client.get("/candidates?status=pending")
        approved_resp = await test_client.get("/candidates?status=approved")

        assert pending_resp.json()["pagination"]["total"] >= 2
        assert approved_resp.json()["pagination"]["total"] >= 1

    async def test_pagination_workflow(
        self,
        test_client,
        setup_test_database
    ):
        """
        E2E TEST: Test pagination through multiple candidates
        """
        # Create 5 candidates
        for i in range(5):
            data = {
                "company_name": f"Pagination Test {i}",
                "contact_email": f"pagination{i}@example.com",
                "products": ["apples"],
                "truck_count": 1,
                "capacity_tons_per_day": 10
            }
            resp = await test_client.post("/candidates", json=data)
            assert resp.status_code == 201

        # Get first page (limit=2)
        page1 = await test_client.get("/candidates?limit=2&offset=0")
        assert page1.status_code == 200
        page1_data = page1.json()
        assert len(page1_data["candidates"]) == 2
        assert page1_data["pagination"]["total"] >= 5

        # Get second page
        page2 = await test_client.get("/candidates?limit=2&offset=2")
        assert page2.status_code == 200
        page2_data = page2.json()
        assert len(page2_data["candidates"]) == 2

        # Verify no overlap
        page1_ids = {c["candidate_id"] for c in page1_data["candidates"]}
        page2_ids = {c["candidate_id"] for c in page2_data["candidates"]}
        assert page1_ids.isdisjoint(page2_ids)

    async def test_product_filtering_workflow(
        self,
        test_client,
        setup_test_database
    ):
        """
        E2E TEST: Create candidates with different products and filter
        """
        # Create candidates with different products
        apple_data = {
            "company_name": "Apple Co",
            "contact_email": "apples@test.com",
            "products": ["apples"],
            "truck_count": 5,
            "capacity_tons_per_day": 100
        }
        orange_data = {
            "company_name": "Orange Co",
            "contact_email": "oranges@test.com",
            "products": ["oranges"],
            "truck_count": 3,
            "capacity_tons_per_day": 50
        }
        both_data = {
            "company_name": "Both Co",
            "contact_email": "both@test.com",
            "products": ["apples", "oranges"],
            "truck_count": 10,
            "capacity_tons_per_day": 200
        }

        apple_resp = await test_client.post("/candidates", json=apple_data)
        orange_resp = await test_client.post("/candidates", json=orange_data)
        both_resp = await test_client.post("/candidates", json=both_data)

        apple_id = apple_resp.json()["candidate_id"]
        orange_id = orange_resp.json()["candidate_id"]
        both_id = both_resp.json()["candidate_id"]

        # Filter by apples (should include apple_id and both_id)
        apples_resp = await test_client.get("/candidates?product=apples")
        apples_ids = {c["candidate_id"] for c in apples_resp.json()["candidates"]}
        assert apple_id in apples_ids
        assert both_id in apples_ids

        # Filter by oranges (should include orange_id and both_id)
        oranges_resp = await test_client.get("/candidates?product=oranges")
        oranges_ids = {c["candidate_id"] for c in oranges_resp.json()["candidates"]}
        assert orange_id in oranges_ids
        assert both_id in oranges_ids

    async def test_health_and_metrics_endpoints(
        self,
        test_client,
        setup_test_database
    ):
        """
        E2E TEST: Verify monitoring endpoints work
        """
        # Health endpoint
        health_resp = await test_client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["status"] == "healthy"

        # Metrics endpoint
        metrics_resp = await test_client.get("/metrics")
        assert metrics_resp.status_code == 200
        # Should contain Prometheus metrics
        assert "http_requests_total" in metrics_resp.text or "# HELP" in metrics_resp.text

    async def test_authentication_workflow(
        self,
        test_client,
        sample_candidate_data,
        admin_token,
        user_token,
        setup_test_database
    ):
        """
        E2E TEST: Test authentication and authorization workflow
        """
        # Create candidate (no auth required)
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        assert create_resp.status_code == 201
        candidate_id = create_resp.json()["candidate_id"]

        # Try to approve without token (should fail)
        no_auth_resp = await test_client.post(f"/candidates/{candidate_id}/approve")
        assert no_auth_resp.status_code == 401

        # Try to approve with user token (should fail - not admin)
        user_headers = {"Authorization": f"Bearer {user_token}"}
        user_resp = await test_client.post(
            f"/candidates/{candidate_id}/approve",
            headers=user_headers
        )
        assert user_resp.status_code == 403

        # Approve with admin token (should succeed)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        admin_resp = await test_client.post(
            f"/candidates/{candidate_id}/approve",
            headers=admin_headers
        )
        assert admin_resp.status_code == 200

    async def test_data_consistency_after_operations(
        self,
        test_client,
        sample_candidate_data,
        admin_token,
        setup_test_database
    ):
        """
        E2E TEST: Verify data consistency after multiple operations
        """
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = create_resp.json()["candidate_id"]
        initial_data = create_resp.json()

        # Get candidate - should match created data
        get_resp = await test_client.get(f"/candidates/{candidate_id}")
        get_data = get_resp.json()
        assert get_data["company_name"] == initial_data["company_name"]
        assert get_data["contact_email"] == initial_data["contact_email"]
        assert get_data["products"] == initial_data["products"]

        # Approve candidate
        headers = {"Authorization": f"Bearer {admin_token}"}
        approve_resp = await test_client.post(
            f"/candidates/{candidate_id}/approve",
            headers=headers
        )
        assert approve_resp.status_code == 200

        # Get approved candidate - core data should remain unchanged
        approved_get = await test_client.get(f"/candidates/{candidate_id}")
        approved_data = approved_get.json()
        assert approved_data["company_name"] == initial_data["company_name"]
        assert approved_data["contact_email"] == initial_data["contact_email"]
        assert approved_data["products"] == initial_data["products"]
        # Only status and provider_id should change
        assert approved_data["status"] == "approved"
        assert approved_data["provider_id"] is not None
        assert approved_data["version"] == 2

    async def test_concurrent_operations_same_candidate(
        self,
        test_client,
        sample_candidate_data,
        setup_test_database
    ):
        """
        E2E TEST: Multiple reads of same candidate (idempotency)
        """
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = create_resp.json()["candidate_id"]

        # Make 5 simultaneous GET requests
        import asyncio
        tasks = [
            test_client.get(f"/candidates/{candidate_id}")
            for _ in range(5)
        ]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for resp in responses:
            assert resp.status_code == 200

        # All should return identical data
        first_data = responses[0].json()
        for resp in responses[1:]:
            assert resp.json() == first_data
