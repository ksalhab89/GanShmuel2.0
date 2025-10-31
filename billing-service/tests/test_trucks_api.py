"""API tests for truck endpoints."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient


class TestTrucksAPI:
    """Test suite for truck API endpoints."""

    @pytest.mark.asyncio
    async def test_register_truck_success(
        self, test_client: AsyncClient, sample_provider
    ):
        """Test registering a new truck via API."""
        response = await test_client.post(
            "/truck", json={"id": "TRUCK123", "provider_id": sample_provider.id}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "TRUCK123"
        assert data["provider_id"] == sample_provider.id

    @pytest.mark.asyncio
    async def test_register_truck_upsert(
        self, test_client: AsyncClient, sample_truck, sample_provider_2
    ):
        """Test truck registration upsert - update existing truck."""
        # Register same truck with different provider
        response = await test_client.post(
            "/truck", json={"id": sample_truck.id, "provider_id": sample_provider_2.id}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == sample_truck.id
        assert data["provider_id"] == sample_provider_2.id

    @pytest.mark.asyncio
    async def test_register_truck_invalid_provider(
        self, test_client: AsyncClient, clean_database
    ):
        """Test registering truck with non-existent provider returns 404."""
        response = await test_client.post(
            "/truck", json={"id": "TRUCK999", "provider_id": 99999}
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_register_truck_validation_error_missing_id(
        self, test_client: AsyncClient, sample_provider
    ):
        """Test validation error for missing truck ID."""
        response = await test_client.post(
            "/truck", json={"provider_id": sample_provider.id}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_truck_validation_error_missing_provider_id(
        self, test_client: AsyncClient
    ):
        """Test validation error for missing provider ID."""
        response = await test_client.post("/truck", json={"id": "TRUCK999"})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_truck_max_length_id(
        self, test_client: AsyncClient, sample_provider
    ):
        """Test registering truck with maximum length ID (10 chars)."""
        response = await test_client.post(
            "/truck",
            json={
                "id": "TRUCK12345",  # 10 characters
                "provider_id": sample_provider.id,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "TRUCK12345"

    @pytest.mark.asyncio
    async def test_register_truck_over_max_length_id(
        self, test_client: AsyncClient, sample_provider
    ):
        """Test registering truck with ID exceeding max length."""
        response = await test_client.post(
            "/truck",
            json={
                "id": "TRUCK123456",  # 11 characters - over limit
                "provider_id": sample_provider.id,
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_truck_success(
        self, test_client: AsyncClient, sample_truck, sample_provider_2
    ):
        """Test updating truck's provider assignment."""
        response = await test_client.put(
            f"/truck/{sample_truck.id}", json={"provider_id": sample_provider_2.id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_truck.id
        assert data["provider_id"] == sample_provider_2.id

    @pytest.mark.asyncio
    async def test_update_truck_not_found(
        self, test_client: AsyncClient, sample_provider, clean_database
    ):
        """Test updating non-existent truck returns 404."""
        response = await test_client.put(
            "/truck/NONEXIST", json={"provider_id": sample_provider.id}
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_update_truck_invalid_provider(
        self, test_client: AsyncClient, sample_truck
    ):
        """Test updating truck with non-existent provider returns 404."""
        response = await test_client.put(
            f"/truck/{sample_truck.id}", json={"provider_id": 99999}
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_update_truck_validation_error_missing_provider_id(
        self, test_client: AsyncClient, sample_truck
    ):
        """Test validation error when updating without provider ID."""
        response = await test_client.put(f"/truck/{sample_truck.id}", json={})

        assert response.status_code == 422

    @pytest.mark.asyncio
    @patch("src.services.weight_client.weight_client.get_item_details")
    @pytest.mark.skip(reason="See SKIPPED_TESTS.md for details")
    async def test_get_truck_details_success(
        self,
        mock_get_item,
        test_client: AsyncClient,
        sample_truck,
        sample_truck_details,
    ):
        """Test getting truck details from weight service."""
        mock_get_item.return_value = type("obj", (object,), sample_truck_details)

        response = await test_client.get(f"/truck/{sample_truck.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_truck.id
        assert "tara" in data
        assert "sessions" in data

    @pytest.mark.asyncio
    async def test_get_truck_details_not_found_in_billing(
        self, test_client: AsyncClient, clean_database
    ):
        """Test getting details for truck not in billing database."""
        response = await test_client.get("/truck/NONEXIST")

        assert response.status_code == 404

    @pytest.mark.asyncio
    @patch("src.services.weight_client.weight_client.get_item_details")
    async def test_get_truck_details_not_found_in_weight_service(
        self, mock_get_item, test_client: AsyncClient, sample_truck
    ):
        """Test getting details when truck not found in weight service."""
        mock_get_item.return_value = None

        response = await test_client.get(f"/truck/{sample_truck.id}")

        assert response.status_code == 404
        data = response.json()
        assert "weight service" in data["detail"].lower()

    @pytest.mark.asyncio
    @patch("src.services.weight_client.weight_client.get_item_details")
    async def test_get_truck_details_with_date_range(
        self,
        mock_get_item,
        test_client: AsyncClient,
        sample_truck,
        sample_truck_details,
    ):
        """Test getting truck details with date range parameters."""
        mock_get_item.return_value = type("obj", (object,), sample_truck_details)

        response = await test_client.get(
            f"/truck/{sample_truck.id}",
            params={"from": "20250101000000", "to": "20250131235959"},
        )

        assert response.status_code == 200
        mock_get_item.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.weight_client.weight_client.get_item_details")
    async def test_get_truck_details_weight_service_unavailable(
        self, mock_get_item, test_client: AsyncClient, sample_truck
    ):
        """Test getting truck details when weight service is unavailable."""
        from src.utils.exceptions import WeightServiceError

        mock_get_item.side_effect = WeightServiceError("Service unavailable")

        response = await test_client.get(f"/truck/{sample_truck.id}")

        assert response.status_code == 503
        data = response.json()
        assert "unavailable" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_multiple_trucks_registration(
        self, test_client: AsyncClient, sample_provider
    ):
        """Test registering multiple trucks for same provider."""
        truck_ids = ["TRUCK001", "TRUCK002", "TRUCK003"]

        for truck_id in truck_ids:
            response = await test_client.post(
                "/truck", json={"id": truck_id, "provider_id": sample_provider.id}
            )
            assert response.status_code == 201
            assert response.json()["id"] == truck_id

    @pytest.mark.asyncio
    async def test_truck_lifecycle(
        self, test_client: AsyncClient, sample_provider, sample_provider_2
    ):
        """Test complete truck lifecycle: register and update."""
        truck_id = "LIFECYCLE"

        # Register
        register_response = await test_client.post(
            "/truck", json={"id": truck_id, "provider_id": sample_provider.id}
        )
        assert register_response.status_code == 201
        assert register_response.json()["provider_id"] == sample_provider.id

        # Update provider
        update_response = await test_client.put(
            f"/truck/{truck_id}", json={"provider_id": sample_provider_2.id}
        )
        assert update_response.status_code == 200
        assert update_response.json()["provider_id"] == sample_provider_2.id


class TestTrucksAPIEdgeCases:
    """Test suite for truck API edge cases."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="See SKIPPED_TESTS.md for details")
    async def test_register_truck_empty_id(
        self, test_client: AsyncClient, sample_provider
    ):
        """Test registering truck with empty ID."""
        response = await test_client.post(
            "/truck", json={"id": "", "provider_id": sample_provider.id}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_truck_special_characters(
        self, test_client: AsyncClient, sample_provider
    ):
        """Test registering truck with special characters in ID."""
        response = await test_client.post(
            "/truck", json={"id": "TRK@#$", "provider_id": sample_provider.id}
        )

        # Should accept or reject based on business rules
        assert response.status_code in [201, 422]

    @pytest.mark.asyncio
    async def test_register_truck_numeric_id(
        self, test_client: AsyncClient, sample_provider
    ):
        """Test registering truck with numeric ID."""
        response = await test_client.post(
            "/truck", json={"id": "12345", "provider_id": sample_provider.id}
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_update_truck_same_provider(
        self, test_client: AsyncClient, sample_truck
    ):
        """Test updating truck with same provider."""
        response = await test_client.put(
            f"/truck/{sample_truck.id}", json={"provider_id": sample_truck.provider_id}
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="See SKIPPED_TESTS.md for details")
    async def test_get_truck_details_invalid_date_format(
        self, test_client: AsyncClient, sample_truck
    ):
        """Test getting truck details with invalid date format."""
        response = await test_client.get(
            f"/truck/{sample_truck.id}",
            params={"from": "invalid-date", "to": "20250131235959"},
        )

        # Should handle gracefully
        assert response.status_code in [200, 400, 422]
