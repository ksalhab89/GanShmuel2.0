"""Tests for main application routes."""

import pytest
from fastapi.testclient import TestClient


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint returns service information."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Shift Service"
        assert data["version"] == "1.0.0"
        assert data["description"] == "Employee shift tracking and scheduling service"
        assert data["documentation"] == "/docs"

    def test_root_endpoint_structure(self, client: TestClient):
        """Test root endpoint has correct structure."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        # Verify main fields
        assert "service" in data
        assert "version" in data
        assert "description" in data
        assert "documentation" in data
        assert "endpoints" in data

        # Verify endpoints field
        endpoints = data["endpoints"]
        assert "health" in endpoints
        assert "shifts" in endpoints
        assert "operators" in endpoints
        assert "metrics" in endpoints

    def test_root_endpoint_values(self, client: TestClient):
        """Test root endpoint has correct endpoint paths."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        endpoints = data["endpoints"]

        assert endpoints["health"] == "/health"
        assert endpoints["shifts"] == "/shifts"
        assert endpoints["operators"] == "/shifts/operators"
        assert endpoints["metrics"] == "/metrics"


class TestMetricsEndpoint:
    """Tests for metrics endpoint."""

    def test_metrics_endpoint(self, client: TestClient):
        """Test metrics endpoint returns Prometheus metrics."""
        response = client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")

    def test_metrics_content(self, client: TestClient):
        """Test metrics endpoint contains expected metrics."""
        response = client.get("/metrics")

        assert response.status_code == 200
        content = response.text

        # Verify service up metric
        assert "shift_service_up" in content

        # Verify request counter metric
        assert "shift_service_requests_total" in content

    def test_metrics_format(self, client: TestClient):
        """Test metrics are in Prometheus format."""
        response = client.get("/metrics")

        assert response.status_code == 200
        content = response.text

        # Prometheus metrics should have HELP and TYPE comments
        assert "# HELP" in content
        assert "# TYPE" in content

    def test_metrics_after_requests(self, client: TestClient):
        """Test metrics are updated after making requests."""
        # Make some requests
        client.get("/health")
        client.get("/shifts/operators")

        # Get metrics
        response = client.get("/metrics")

        assert response.status_code == 200
        content = response.text

        # Verify metrics content is present
        assert len(content) > 0
        assert "shift_service_requests_total" in content


class TestApplicationConfig:
    """Tests for application configuration."""

    def test_cors_configuration(self, client: TestClient):
        """Test CORS is configured."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )

        # Should succeed (CORS middleware doesn't block in test)
        assert response.status_code == 200

    def test_openapi_docs_available(self, client: TestClient):
        """Test OpenAPI documentation is available."""
        response = client.get("/docs")

        # FastAPI serves docs at /docs
        assert response.status_code == 200

    def test_openapi_json_available(self, client: TestClient):
        """Test OpenAPI JSON schema is available."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()

        # Verify OpenAPI structure
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "Shift Service"
        assert data["info"]["version"] == "1.0.0"

    def test_openapi_paths(self, client: TestClient):
        """Test OpenAPI schema includes all paths."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        paths = data["paths"]

        # Verify main paths are documented
        assert "/health" in paths
        assert "/shifts/operators" in paths
        assert "/shifts/start" in paths
        assert "/shifts/{shift_id}/end" in paths
        assert "/shifts" in paths
        assert "/shifts/{shift_id}" in paths

    def test_redoc_available(self, client: TestClient):
        """Test ReDoc documentation is available."""
        response = client.get("/redoc")

        assert response.status_code == 200


class TestErrorHandling:
    """Tests for error handling."""

    def test_404_not_found(self, client: TestClient):
        """Test 404 error for non-existent route."""
        response = client.get("/nonexistent-route")

        assert response.status_code == 404

    def test_405_method_not_allowed(self, client: TestClient):
        """Test 405 error for unsupported method."""
        response = client.put("/health")

        assert response.status_code == 405

    def test_422_validation_error_structure(self, client: TestClient):
        """Test 422 validation error has correct structure."""
        # Send invalid data to trigger validation error
        response = client.post("/shifts/operators", json={})

        assert response.status_code == 422
        data = response.json()

        # FastAPI validation error structure
        assert "detail" in data
        assert isinstance(data["detail"], list)


class TestContentTypes:
    """Tests for content type handling."""

    def test_json_request(self, client: TestClient):
        """Test handling JSON request."""
        response = client.post(
            "/shifts/operators",
            json={"name": "Test User", "employee_id": "TEST001", "role": "weigher"}
        )

        # Should accept JSON
        assert response.status_code == 201

    def test_json_response(self, client: TestClient):
        """Test JSON response content type."""
        response = client.get("/health")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_metrics_text_response(self, client: TestClient):
        """Test metrics endpoint returns text/plain."""
        response = client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
