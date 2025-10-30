"""Test health check endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_async(async_client: AsyncClient) -> None:
    """Test health check endpoint (async)."""
    response = await async_client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "weight-service"
    assert "version" in data
