"""Router tests for batch upload endpoint."""

import pytest
from fastapi.testclient import TestClient


class TestBatchRouterExceptionHandlers:
    """Test suite for batch router exception handling."""

    def test_file_not_found_error_handling(self):
        """Test that FileNotFoundError returns 400 with proper message."""
        from unittest.mock import AsyncMock
        from src.main import app
        from src.dependencies import get_file_service

        # Mock file_service to raise FileNotFoundError
        mock_service = AsyncMock()
        async def mock_process_batch_file(filename):
            raise FileNotFoundError("File 'missing.csv' not found in /in directory")
        mock_service.process_batch_file = mock_process_batch_file

        # Override dependency
        app.dependency_overrides[get_file_service] = lambda: mock_service

        try:
            client = TestClient(app)
            payload = {"file": "missing.csv"}

            response = client.post("/batch-weight", json=payload)

            assert response.status_code == 400
            assert "File not found" in response.json()["detail"]
            assert "missing.csv" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_file_processing_error_handling(self):
        """Test that FileProcessingError returns 422 with proper message."""
        from unittest.mock import AsyncMock
        from src.main import app
        from src.dependencies import get_file_service
        from src.utils.exceptions import FileProcessingError

        # Mock file_service to raise FileProcessingError
        mock_service = AsyncMock()
        async def mock_process_batch_file(filename):
            raise FileProcessingError("Invalid CSV format: Missing required columns")
        mock_service.process_batch_file = mock_process_batch_file

        # Override dependency
        app.dependency_overrides[get_file_service] = lambda: mock_service

        try:
            client = TestClient(app)
            payload = {"file": "invalid.csv"}

            response = client.post("/batch-weight", json=payload)

            assert response.status_code == 422
            assert "File processing error" in response.json()["detail"]
            assert "Invalid CSV format" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_value_error_handling(self):
        """Test that ValueError returns 400 with proper message."""
        from unittest.mock import AsyncMock
        from src.main import app
        from src.dependencies import get_file_service

        # Mock file_service to raise ValueError
        mock_service = AsyncMock()
        async def mock_process_batch_file(filename):
            raise ValueError("Unsupported file format: .txt")
        mock_service.process_batch_file = mock_process_batch_file

        # Override dependency
        app.dependency_overrides[get_file_service] = lambda: mock_service

        try:
            client = TestClient(app)
            payload = {"file": "data.csv"}  # Use .csv to pass validation

            response = client.post("/batch-weight", json=payload)

            assert response.status_code == 400
            assert "Invalid file format" in response.json()["detail"]
            assert "Unsupported file format" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_generic_exception_handling(self):
        """Test that generic Exception returns 500 with proper message."""
        from unittest.mock import AsyncMock
        from src.main import app
        from src.dependencies import get_file_service

        # Mock file_service to raise generic Exception
        mock_service = AsyncMock()
        async def mock_process_batch_file(filename):
            raise Exception("Unexpected file system error")
        mock_service.process_batch_file = mock_process_batch_file

        # Override dependency
        app.dependency_overrides[get_file_service] = lambda: mock_service

        try:
            client = TestClient(app)
            payload = {"file": "data.csv"}

            response = client.post("/batch-weight", json=payload)

            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]
            assert "file system error" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
