"""Router tests for health check endpoint."""

import pytest
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


class TestHealthRouter:
    """Test suite for GET /health endpoint."""

    def test_health_check_success(self, client):
        """Test health check endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_response_structure(self, client):
        """Test health check response has expected structure."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data
        assert "service" in data
        assert "version" in data

    def test_health_check_status_healthy(self, client):
        """Test health check returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"

    def test_health_check_service_name(self, client):
        """Test health check includes service name."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "weight-service"

    def test_health_check_includes_version(self, client):
        """Test health check includes version information."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

    def test_health_check_returns_json(self, client):
        """Test health check returns JSON response."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_health_check_method_get_only(self, client):
        """Test health check only accepts GET method."""
        # POST should not be allowed
        post_response = client.post("/health")
        assert post_response.status_code == 405

        # PUT should not be allowed
        put_response = client.put("/health")
        assert put_response.status_code == 405

        # DELETE should not be allowed
        delete_response = client.delete("/health")
        assert delete_response.status_code == 405

    def test_health_check_no_parameters_required(self, client):
        """Test health check works without parameters."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_idempotent(self, client):
        """Test health check is idempotent."""
        response1 = client.get("/health")
        response2 = client.get("/health")

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json()["status"] == response2.json()["status"]

    def test_health_check_fast_response(self, client):
        """Test health check responds quickly."""
        import time

        start = time.time()
        response = client.get("/health")
        duration = time.time() - start

        assert response.status_code == 200
        # Should respond in under 1 second
        assert duration < 1.0

    def test_health_check_database_success_with_mock(self):
        """Test health check with mocked successful database connection."""
        from unittest.mock import AsyncMock
        from src.main import app
        from src.dependencies import get_db

        # Mock database session to succeed
        async def mock_db_success():
            mock_db = AsyncMock()
            async def return_success(*args, **kwargs):
                return True
            mock_db.execute = return_success
            yield mock_db

        # Override database dependency
        app.dependency_overrides[get_db] = mock_db_success

        try:
            client = TestClient(app)
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["database"] == "healthy"
            assert data["service"] == "weight-service"
            assert "version" in data
        finally:
            app.dependency_overrides.clear()

    def test_health_check_database_failure(self):
        """Test health check returns degraded status when database fails."""
        from unittest.mock import AsyncMock
        from src.main import app
        from src.dependencies import get_db

        # Mock database session to raise exception
        async def mock_db_fail():
            mock_db = AsyncMock()
            async def raise_exception(*args, **kwargs):
                raise Exception("Database connection failed")
            mock_db.execute = raise_exception
            yield mock_db

        # Override database dependency
        app.dependency_overrides[get_db] = mock_db_fail

        try:
            client = TestClient(app)
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["database"] == "unhealthy"
            assert data["service"] == "weight-service"
            assert "version" in data
        finally:
            app.dependency_overrides.clear()
