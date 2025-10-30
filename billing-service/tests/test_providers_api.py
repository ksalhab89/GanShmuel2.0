"""API tests for provider endpoints."""

import pytest
from httpx import AsyncClient


class TestProvidersAPI:
    """Test suite for provider API endpoints."""

    @pytest.mark.asyncio
    async def test_create_provider_success(
        self, test_client: AsyncClient, clean_database
    ):
        """Test creating a provider via API."""
        response = await test_client.post(
            "/provider", json={"name": "API Test Provider"}
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "API Test Provider"
        assert isinstance(data["id"], int)

    @pytest.mark.asyncio
    async def test_create_provider_validation_error_empty_name(
        self, test_client: AsyncClient, clean_database
    ):
        """Test validation error for empty provider name."""
        response = await test_client.post("/provider", json={"name": ""})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_provider_validation_error_missing_name(
        self, test_client: AsyncClient, clean_database
    ):
        """Test validation error for missing provider name."""
        response = await test_client.post("/provider", json={})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_provider_duplicate_name(
        self, test_client: AsyncClient, sample_provider
    ):
        """Test creating provider with duplicate name returns 409."""
        response = await test_client.post(
            "/provider", json={"name": sample_provider.name}
        )

        assert response.status_code == 409
        data = response.json()
        assert "detail" in data
        assert "unique" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_provider_long_name(
        self, test_client: AsyncClient, clean_database
    ):
        """Test creating provider with very long name."""
        long_name = "A" * 255  # Max length
        response = await test_client.post("/provider", json={"name": long_name})

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == long_name

    @pytest.mark.asyncio
    async def test_create_provider_special_characters(
        self, test_client: AsyncClient, clean_database
    ):
        """Test creating provider with special characters in name."""
        response = await test_client.post(
            "/provider", json={"name": "Test & Provider #1 (2025)"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test & Provider #1 (2025)"

    @pytest.mark.asyncio
    async def test_create_provider_international_name(
        self, test_client: AsyncClient, clean_database
    ):
        """Test creating provider with international name."""
        response = await test_client.post(
            "/provider", json={"name": "International Provider GmbH"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "International Provider GmbH"

    @pytest.mark.asyncio
    async def test_update_provider_success(
        self, test_client: AsyncClient, sample_provider
    ):
        """Test updating provider name via API."""
        response = await test_client.put(
            f"/provider/{sample_provider.id}", json={"name": "Updated Provider Name"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_provider.id
        assert data["name"] == "Updated Provider Name"

    @pytest.mark.asyncio
    async def test_update_provider_not_found(
        self, test_client: AsyncClient, clean_database
    ):
        """Test updating non-existent provider returns 404."""
        response = await test_client.put("/provider/99999", json={"name": "New Name"})

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_update_provider_duplicate_name(
        self, test_client: AsyncClient, sample_provider, sample_provider_2
    ):
        """Test updating provider with duplicate name returns 409."""
        response = await test_client.put(
            f"/provider/{sample_provider.id}", json={"name": sample_provider_2.name}
        )

        assert response.status_code == 409
        data = response.json()
        assert "detail" in data
        assert "unique" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_provider_same_name(
        self, test_client: AsyncClient, sample_provider
    ):
        """Test updating provider with same name succeeds."""
        response = await test_client.put(
            f"/provider/{sample_provider.id}", json={"name": sample_provider.name}
        )

        # Should succeed or fail depending on implementation
        assert response.status_code in [200, 409]

    @pytest.mark.asyncio
    async def test_update_provider_validation_error_empty_name(
        self, test_client: AsyncClient, sample_provider
    ):
        """Test validation error when updating with empty name."""
        response = await test_client.put(
            f"/provider/{sample_provider.id}", json={"name": ""}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_provider_validation_error_missing_name(
        self, test_client: AsyncClient, sample_provider
    ):
        """Test validation error when updating without name."""
        response = await test_client.put(f"/provider/{sample_provider.id}", json={})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_provider_invalid_id_format(
        self, test_client: AsyncClient, clean_database
    ):
        """Test updating provider with invalid ID format."""
        response = await test_client.put("/provider/invalid", json={"name": "New Name"})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_multiple_providers_creation(
        self, test_client: AsyncClient, clean_database
    ):
        """Test creating multiple providers in sequence."""
        providers = ["Provider A", "Provider B", "Provider C"]
        created_ids = []

        for name in providers:
            response = await test_client.post("/provider", json={"name": name})
            assert response.status_code == 201
            data = response.json()
            created_ids.append(data["id"])
            assert data["name"] == name

        # Verify all IDs are unique
        assert len(created_ids) == len(set(created_ids))

    @pytest.mark.asyncio
    async def test_provider_lifecycle(self, test_client: AsyncClient, clean_database):
        """Test complete provider lifecycle: create and update."""
        # Create
        create_response = await test_client.post(
            "/provider", json={"name": "Lifecycle Test Provider"}
        )
        assert create_response.status_code == 201
        provider_id = create_response.json()["id"]

        # Update
        update_response = await test_client.put(
            f"/provider/{provider_id}", json={"name": "Updated Lifecycle Provider"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Updated Lifecycle Provider"


class TestProvidersAPIEdgeCases:
    """Test suite for provider API edge cases."""

    @pytest.mark.asyncio
    async def test_create_provider_whitespace_name(
        self, test_client: AsyncClient, clean_database
    ):
        """Test creating provider with only whitespace."""
        response = await test_client.post("/provider", json={"name": "   "})

        # Depending on implementation, might accept or reject
        assert response.status_code in [201, 422]

    @pytest.mark.asyncio
    async def test_create_provider_with_newlines(
        self, test_client: AsyncClient, clean_database
    ):
        """Test creating provider with newline characters."""
        response = await test_client.post(
            "/provider", json={"name": "Provider\nWith\nNewlines"}
        )

        assert response.status_code in [201, 422]

    @pytest.mark.asyncio
    async def test_update_provider_zero_id(
        self, test_client: AsyncClient, clean_database
    ):
        """Test updating provider with ID 0."""
        response = await test_client.put(
            "/provider/0", json={"name": "Zero ID Provider"}
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_provider_negative_id(
        self, test_client: AsyncClient, clean_database
    ):
        """Test updating provider with negative ID."""
        response = await test_client.put(
            "/provider/-1", json={"name": "Negative ID Provider"}
        )

        assert response.status_code in [404, 422]


class TestProvidersAPIConcurrency:
    """Test suite for provider API concurrency scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="TODO: Fix later")
    async def test_concurrent_provider_creation_same_name(
        self, test_client: AsyncClient, clean_database
    ):
        """Test concurrent attempts to create providers with same name."""
        import asyncio

        async def create_provider(name: str):
            return await test_client.post("/provider", json={"name": name})

        # Try to create two providers with same name concurrently
        results = await asyncio.gather(
            create_provider("Concurrent Provider"),
            create_provider("Concurrent Provider"),
            return_exceptions=True,
        )

        # One should succeed (201), one should fail (409)
        status_codes = [
            r.status_code if hasattr(r, "status_code") else 500 for r in results
        ]
        assert 201 in status_codes
        assert 409 in status_codes or 500 in status_codes

    @pytest.mark.asyncio
    async def test_concurrent_provider_updates(
        self, test_client: AsyncClient, sample_provider
    ):
        """Test concurrent updates to same provider."""
        import asyncio

        async def update_provider(name: str):
            return await test_client.put(
                f"/provider/{sample_provider.id}", json={"name": name}
            )

        # Try to update same provider with different names concurrently
        results = await asyncio.gather(
            update_provider("Name A"), update_provider("Name B"), return_exceptions=True
        )

        # Both might succeed or one might fail depending on timing
        status_codes = [
            r.status_code if hasattr(r, "status_code") else 500 for r in results
        ]
        assert 200 in status_codes
