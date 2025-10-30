"""Tests for health check endpoints."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


def test_health_check_healthy(client: TestClient):
    """Test health check endpoint when database is healthy."""
    with patch("src.routers.health.test_db_connection", return_value=True):
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Shift Service"
    assert data["version"] == "1.0.0"
    assert data["database"] == "connected"


def test_health_check_unhealthy(client: TestClient):
    """Test health check endpoint when database is unhealthy."""
    with patch("src.routers.health.test_db_connection", return_value=False):
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["service"] == "Shift Service"
    assert data["version"] == "1.0.0"
    assert data["database"] == "disconnected"


def test_health_check_response_structure(client: TestClient):
    """Test that health check response has correct structure."""
    with patch("src.routers.health.test_db_connection", return_value=True):
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    # Verify all required fields are present
    assert "status" in data
    assert "service" in data
    assert "version" in data
    assert "database" in data

    # Verify field types
    assert isinstance(data["status"], str)
    assert isinstance(data["service"], str)
    assert isinstance(data["version"], str)
    assert isinstance(data["database"], str)
