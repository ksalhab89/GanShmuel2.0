"""Performance tests for provider service."""
import pytest
import asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.usefixtures("setup_test_database")


class TestPerformance:
    """Performance test suite for high-volume operations"""

    @pytest.mark.asyncio
    async def test_concurrent_approvals(self, test_client: AsyncClient):
        """Process 50 concurrent approval requests."""
        # Create 50 candidates first
        candidates = []
        for i in range(50):
            response = await test_client.post("/candidates", json={
                "company_name": f"Approval Test {i}",
                "contact_email": f"approve{i}@test.com",
                "phone": f"555-{i:04d}",
                "products": ["oranges"],
                "truck_count": 3,
                "capacity_tons_per_day": 50,
                "location": "Approval City"
            })
            assert response.status_code == 201
            candidates.append(response.json()["candidate_id"])

        # Approve all concurrently
        tasks = [test_client.post(f"/candidates/{cid}/approve") for cid in candidates]
        responses = await asyncio.gather(*tasks)

        # All should succeed (assuming billing service is available)
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count == 50

        # Verify all have unique provider IDs
        provider_ids = [r.json()["provider_id"] for r in responses if r.status_code == 200]
        assert len(set(provider_ids)) == 50

    @pytest.mark.asyncio
    async def test_large_dataset_pagination(self, test_client: AsyncClient):
        """Test pagination with multiple pages of results."""
        # Create 25 candidates for pagination testing
        for i in range(25):
            await test_client.post("/candidates", json={
                "company_name": f"Pagination Test {i}",
                "contact_email": f"page{i}@test.com",
                "products": ["grapes"],
                "truck_count": 2,
                "capacity_tons_per_day": 30
            })

        # Test first page
        response = await test_client.get("/candidates?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert "pagination" in data
        assert data["pagination"]["limit"] == 10
        assert data["pagination"]["offset"] == 0
        assert data["pagination"]["total"] >= 25
        assert len(data["candidates"]) == 10

        # Test second page
        response = await test_client.get("/candidates?limit=10&offset=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["candidates"]) == 10

        # Test third page
        response = await test_client.get("/candidates?limit=10&offset=20")
        assert response.status_code == 200
        data = response.json()
        assert len(data["candidates"]) >= 5

    @pytest.mark.asyncio
    async def test_concurrent_duplicate_email_handling(self, test_client: AsyncClient):
        """Test handling of concurrent registrations with duplicate emails."""
        duplicate_data = {
            "company_name": "Duplicate Test",
            "contact_email": "duplicate@test.com",
            "products": ["apples"],
            "truck_count": 5,
            "capacity_tons_per_day": 100
        }

        # Try to create 10 candidates with same email concurrently
        tasks = [test_client.post("/candidates", json=duplicate_data) for _ in range(10)]
        responses = await asyncio.gather(*tasks)

        # Only one should succeed (201), others should fail (409)
        success_count = sum(1 for r in responses if r.status_code == 201)
        conflict_count = sum(1 for r in responses if r.status_code == 409)

        assert success_count == 1
        assert conflict_count == 9

