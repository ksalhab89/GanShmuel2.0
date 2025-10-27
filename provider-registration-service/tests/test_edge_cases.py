"""
Edge cases and error scenarios
Comprehensive coverage of unusual inputs and boundary conditions
"""
import pytest

pytestmark = pytest.mark.asyncio


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    async def test_create_candidate_minimal_fields(self, test_client, setup_test_database):
        """
        EDGE CASE: Create candidate with only required fields
        Optional fields (phone, location) can be null
        """
        minimal_data = {
            "company_name": "Minimal Co",
            "contact_email": "minimal@example.com",
            "products": ["apples"],
            "truck_count": 1,
            "capacity_tons_per_day": 1
            # phone and location omitted
        }

        response = await test_client.post("/candidates", json=minimal_data)

        assert response.status_code == 201
        data = response.json()
        assert data["phone"] is None
        assert data["location"] is None

    async def test_create_candidate_maximum_values(self, test_client, setup_test_database):
        """
        BOUNDARY: Maximum valid values
        """
        max_data = {
            "company_name": "X" * 255,  # Max length
            "contact_email": "test@example.com",
            "products": ["apples", "oranges", "grapes", "bananas", "mangoes"],  # All products
            "truck_count": 1000,  # Large fleet
            "capacity_tons_per_day": 10000,  # High capacity
            "phone": "X" * 50,  # Max phone length
            "location": "Y" * 255  # Max location length
        }

        response = await test_client.post("/candidates", json=max_data)
        assert response.status_code == 201

    async def test_create_candidate_zero_truck_count(self, test_client, setup_test_database):
        """
        VALIDATION: Zero truck count should fail
        Expected: 422 (must be > 0)
        """
        invalid_data = {
            "company_name": "Zero Trucks",
            "contact_email": "zero@example.com",
            "products": ["apples"],
            "truck_count": 0,  # Invalid
            "capacity_tons_per_day": 100
        }

        response = await test_client.post("/candidates", json=invalid_data)
        assert response.status_code == 422

    async def test_create_candidate_negative_capacity(self, test_client, setup_test_database):
        """
        VALIDATION: Negative capacity should fail
        Expected: 422 (must be > 0)
        """
        invalid_data = {
            "company_name": "Negative Capacity",
            "contact_email": "negative@example.com",
            "products": ["apples"],
            "truck_count": 5,
            "capacity_tons_per_day": -100  # Invalid
        }

        response = await test_client.post("/candidates", json=invalid_data)
        assert response.status_code == 422

    async def test_create_candidate_invalid_product(self, test_client, setup_test_database):
        """
        VALIDATION: Invalid product name should fail
        Expected: 422 (not in allowed list)
        """
        invalid_data = {
            "company_name": "Invalid Product",
            "contact_email": "invalid@example.com",
            "products": ["watermelon"],  # Not in allowed list
            "truck_count": 5,
            "capacity_tons_per_day": 100
        }

        response = await test_client.post("/candidates", json=invalid_data)
        assert response.status_code == 422

    async def test_create_candidate_empty_products_list(self, test_client, setup_test_database):
        """
        VALIDATION: Empty products list should fail
        Expected: 422 (must have at least one product)
        """
        invalid_data = {
            "company_name": "No Products",
            "contact_email": "noproducts@example.com",
            "products": [],  # Empty list
            "truck_count": 5,
            "capacity_tons_per_day": 100
        }

        response = await test_client.post("/candidates", json=invalid_data)
        assert response.status_code == 422

    async def test_list_candidates_pagination_limits(self, test_client, setup_test_database):
        """
        PAGINATION: Test limit and offset boundaries
        """
        # Test max limit (100)
        response = await test_client.get("/candidates?limit=100")
        assert response.status_code == 200

        # Test exceeding max limit (should fail)
        response = await test_client.get("/candidates?limit=101")
        assert response.status_code == 422

        # Test zero limit (should fail)
        response = await test_client.get("/candidates?limit=0")
        assert response.status_code == 422

        # Test negative offset (should fail)
        response = await test_client.get("/candidates?offset=-1")
        assert response.status_code == 422

    async def test_list_candidates_invalid_status_filter(self, test_client, setup_test_database):
        """
        VALIDATION: Invalid status filter should return empty results
        Expected: 200 OK with empty results
        """
        response = await test_client.get("/candidates?status=invalid_status")
        assert response.status_code == 200
        data = response.json()
        # Should return empty results for invalid status
        assert len(data["candidates"]) == 0

    async def test_list_candidates_invalid_product_filter(self, test_client, setup_test_database):
        """
        VALIDATION: Invalid product filter should return empty results
        Expected: 200 OK with empty results
        """
        response = await test_client.get("/candidates?product=invalid_product")
        assert response.status_code == 200
        data = response.json()
        # Should return empty results for invalid product
        assert len(data["candidates"]) == 0

    async def test_create_candidate_invalid_email_format(self, test_client, setup_test_database):
        """
        VALIDATION: Invalid email format should fail
        Expected: 422 Unprocessable Entity
        """
        invalid_data = {
            "company_name": "Bad Email",
            "contact_email": "not-an-email",  # Invalid format
            "products": ["apples"],
            "truck_count": 5,
            "capacity_tons_per_day": 100
        }

        response = await test_client.post("/candidates", json=invalid_data)
        assert response.status_code == 422

    async def test_create_candidate_missing_required_field(self, test_client, setup_test_database):
        """
        VALIDATION: Missing required field should fail
        Expected: 422 Unprocessable Entity
        """
        incomplete_data = {
            "company_name": "Missing Fields",
            # contact_email missing
            "products": ["apples"],
            "truck_count": 5,
            "capacity_tons_per_day": 100
        }

        response = await test_client.post("/candidates", json=incomplete_data)
        assert response.status_code == 422

    async def test_create_candidate_empty_company_name(self, test_client, setup_test_database):
        """
        VALIDATION: Empty company name should fail
        Expected: 422 Unprocessable Entity
        """
        invalid_data = {
            "company_name": "",  # Empty
            "contact_email": "test@example.com",
            "products": ["apples"],
            "truck_count": 5,
            "capacity_tons_per_day": 100
        }

        response = await test_client.post("/candidates", json=invalid_data)
        assert response.status_code == 422

    async def test_approve_candidate_twice_fails(
        self,
        test_client,
        sample_candidate_data,
        admin_token,
        setup_test_database
    ):
        """
        IDEMPOTENCY: Approving already approved candidate should fail
        Expected: 400 Bad Request
        """
        # Create and approve candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        candidate_id = create_resp.json()["candidate_id"]

        headers = {"Authorization": f"Bearer {admin_token}"}
        approve_resp = await test_client.post(
            f"/candidates/{candidate_id}/approve",
            headers=headers
        )
        assert approve_resp.status_code == 200

        # Try to approve again
        second_approve = await test_client.post(
            f"/candidates/{candidate_id}/approve",
            headers=headers
        )
        assert second_approve.status_code == 400
        assert "already approved" in second_approve.json()["detail"].lower()

    async def test_approve_nonexistent_candidate(
        self,
        test_client,
        admin_token,
        setup_test_database
    ):
        """
        ERROR CASE: Approve non-existent candidate
        Expected: 404 Not Found
        """
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = await test_client.post(
            f"/candidates/{fake_uuid}/approve",
            headers=headers
        )
        assert response.status_code == 404

    async def test_list_candidates_with_large_offset(
        self,
        test_client,
        sample_candidate_data,
        setup_test_database
    ):
        """
        PAGINATION: Large offset beyond available data
        Expected: 200 OK with empty results
        """
        # Create one candidate
        await test_client.post("/candidates", json=sample_candidate_data)

        # Request with large offset
        response = await test_client.get("/candidates?offset=1000")
        assert response.status_code == 200
        data = response.json()
        assert len(data["candidates"]) == 0
        assert data["pagination"]["total"] == 1
        assert data["pagination"]["offset"] == 1000

    async def test_create_candidate_duplicate_email_conflict(
        self,
        test_client,
        sample_candidate_data,
        setup_test_database
    ):
        """
        CONSTRAINT: Duplicate email should fail with 409 Conflict
        Expected: 409 Conflict
        """
        # Create first candidate
        first_resp = await test_client.post("/candidates", json=sample_candidate_data)
        assert first_resp.status_code == 201

        # Try to create second candidate with same email
        second_resp = await test_client.post("/candidates", json=sample_candidate_data)
        assert second_resp.status_code == 409
        assert "email" in second_resp.json()["detail"].lower()

    async def test_create_candidate_with_all_products(self, test_client, setup_test_database):
        """
        EDGE CASE: Create candidate with all allowed products
        Expected: 201 Created
        """
        all_products_data = {
            "company_name": "All Products Co",
            "contact_email": "allproducts@example.com",
            "products": ["apples", "oranges", "grapes", "bananas", "mangoes"],
            "truck_count": 10,
            "capacity_tons_per_day": 500
        }

        response = await test_client.post("/candidates", json=all_products_data)
        assert response.status_code == 201
        data = response.json()
        assert len(data["products"]) == 5

    async def test_list_candidates_combined_filters(
        self,
        test_client,
        setup_test_database
    ):
        """
        FILTERING: Multiple filters combined
        Expected: 200 OK with correctly filtered results
        """
        # Create multiple candidates
        candidate1 = {
            "company_name": "Apples Inc",
            "contact_email": "apples@example.com",
            "products": ["apples"],
            "truck_count": 5,
            "capacity_tons_per_day": 100
        }
        candidate2 = {
            "company_name": "Oranges Corp",
            "contact_email": "oranges@example.com",
            "products": ["oranges"],
            "truck_count": 3,
            "capacity_tons_per_day": 50
        }

        await test_client.post("/candidates", json=candidate1)
        resp2 = await test_client.post("/candidates", json=candidate2)
        candidate2_id = resp2.json()["candidate_id"]

        # Filter by status=pending and product=oranges
        response = await test_client.get("/candidates?status=pending&product=oranges")
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total"] >= 1
        # Should include candidate2
        candidate_ids = [c["candidate_id"] for c in data["candidates"]]
        assert candidate2_id in candidate_ids
