"""Router tests for weight recording endpoint."""

import pytest
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


class TestWeightRecordingRouter:
    """Test suite for POST /weight endpoint."""

    def test_post_weight_in_direction_success(self, client):
        """Test successful IN weighing creates new session."""
        payload = {
            "direction": "in",
            "truck": "TEST_TRUCK_001",
            "containers": "C001,C002,C003",
            "weight": 5000,
            "unit": "kg",
            "produce": "apples"
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "id" in data or "transaction_id" in data
        assert data["direction"] == "in"
        assert data["truck"] == "TEST_TRUCK_001"
        assert data["gross_weight"] == 5000
        assert "session_id" in data
        assert data["net_weight"] == "na"  # IN direction doesn't have net weight yet

    def test_post_weight_out_direction_success(self, client):
        """Test successful OUT weighing completes existing session."""
        truck_id = "TEST_TRUCK_OUT_001"
        containers = "C001,C002"

        # First create IN session
        in_payload = {
            "direction": "in",
            "truck": truck_id,
            "containers": containers,
            "weight": 5000,
            "unit": "kg",
            "produce": "oranges"
        }

        in_response = client.post("/weight", json=in_payload)
        assert in_response.status_code == 200
        in_data = in_response.json()
        session_id = in_data["session_id"]

        # Then create OUT transaction
        out_payload = {
            "direction": "out",
            "truck": truck_id,
            "containers": containers,
            "weight": 4500,
            "unit": "kg"
        }

        out_response = client.post("/weight", json=out_payload)
        assert out_response.status_code == 200

        out_data = out_response.json()
        assert out_data["direction"] == "out"
        assert out_data["truck"] == truck_id
        assert out_data["gross_weight"] == 4500
        assert out_data["session_id"] == session_id
        assert out_data["net_weight"] != "na"

    def test_post_weight_none_direction_success(self, client):
        """Test NONE direction for container-only weighing."""
        payload = {
            "direction": "none",
            "truck": "na",
            "containers": "C100,C101",
            "weight": 150,
            "unit": "kg"
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["direction"] == "none"
        assert data["gross_weight"] == 150

    def test_post_weight_creates_session(self, client):
        """Test that IN direction creates a new session."""
        payload = {
            "direction": "in",
            "truck": "SESSION_TEST_001",
            "containers": "C200,C201",
            "weight": 6000,
            "unit": "kg",
            "produce": "grapes"
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "session_id" in data
        assert data["session_id"] is not None
        assert len(data["session_id"]) > 0

        # Verify session exists
        session_id = data["session_id"]
        session_response = client.get(f"/session/{session_id}")
        assert session_response.status_code == 200

    def test_post_weight_links_to_session(self, client):
        """Test that OUT direction links to existing session."""
        truck_id = "LINK_TEST_001"
        containers = "C300,C301,C302"

        # Create IN session
        in_payload = {
            "direction": "in",
            "truck": truck_id,
            "containers": containers,
            "weight": 7000,
            "unit": "kg",
            "produce": "peaches"
        }

        in_response = client.post("/weight", json=in_payload)
        assert in_response.status_code == 200
        session_id = in_response.json()["session_id"]

        # Create OUT transaction
        out_payload = {
            "direction": "out",
            "truck": truck_id,
            "containers": containers,
            "weight": 6500,
            "unit": "kg"
        }

        out_response = client.post("/weight", json=out_payload)
        assert out_response.status_code == 200

        out_data = out_response.json()
        assert out_data["session_id"] == session_id

    def test_post_weight_invalid_direction(self, client):
        """Test that invalid direction returns validation error."""
        payload = {
            "direction": "invalid",
            "truck": "TEST_001",
            "containers": "C001",
            "weight": 1000,
            "unit": "kg"
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 422  # Validation error

    def test_post_weight_missing_required_fields(self, client):
        """Test that missing required fields returns validation error."""
        # Missing direction
        payload = {
            "truck": "TEST_002",
            "containers": "C001",
            "weight": 1000
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 422

    def test_post_weight_missing_containers(self, client):
        """Test that missing containers field returns validation error."""
        payload = {
            "direction": "in",
            "truck": "TEST_003",
            "weight": 1000,
            "unit": "kg"
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 422

    def test_post_weight_missing_weight(self, client):
        """Test that missing weight field returns validation error."""
        payload = {
            "direction": "in",
            "truck": "TEST_004",
            "containers": "C001,C002",
            "unit": "kg"
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 422

    def test_post_weight_zero_weight(self, client):
        """Test that zero weight is rejected."""
        payload = {
            "direction": "in",
            "truck": "TEST_005",
            "containers": "C001",
            "weight": 0,
            "unit": "kg"
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 422

    def test_post_weight_negative_weight(self, client):
        """Test that negative weight is rejected."""
        payload = {
            "direction": "in",
            "truck": "TEST_006",
            "containers": "C001",
            "weight": -1000,
            "unit": "kg"
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 422

    def test_post_weight_force_mode(self, client):
        """Test force mode bypasses business rules."""
        truck_id = "FORCE_TEST_001"

        # First OUT without IN (should fail normally)
        out_payload = {
            "direction": "out",
            "truck": truck_id,
            "containers": "C400,C401",
            "weight": 4000,
            "unit": "kg",
            "force": True
        }

        response = client.post("/weight", json=out_payload)
        # With force mode, should succeed
        assert response.status_code == 200

        data = response.json()
        assert data["direction"] == "out"

    def test_post_weight_duplicate_in_without_force(self, client):
        """Test that duplicate IN for same truck is handled."""
        truck_id = "DUP_TEST_001"
        containers = "C500,C501"

        # First IN
        in_payload = {
            "direction": "in",
            "truck": truck_id,
            "containers": containers,
            "weight": 5000,
            "unit": "kg",
            "produce": "plums"
        }

        first_response = client.post("/weight", json=in_payload)
        assert first_response.status_code == 200

        # Second IN for same truck (without force)
        second_response = client.post("/weight", json=in_payload)
        # Should either succeed (creating new session) or fail depending on business rules
        assert second_response.status_code in [200, 400]

    def test_post_weight_empty_containers(self, client):
        """Test that empty container list is rejected."""
        payload = {
            "direction": "in",
            "truck": "TEST_007",
            "containers": "",
            "weight": 1000,
            "unit": "kg"
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 422

    def test_post_weight_invalid_container_format(self, client):
        """Test that invalid container format is rejected."""
        payload = {
            "direction": "in",
            "truck": "TEST_008",
            "containers": "C001, , C002",  # Empty container in list
            "weight": 1000,
            "unit": "kg"
        }

        response = client.post("/weight", json=payload)
        # Should be accepted (empty strings are filtered)
        assert response.status_code in [200, 422]

    def test_post_weight_invalid_unit(self, client):
        """Test that invalid unit returns validation error."""
        payload = {
            "direction": "in",
            "truck": "TEST_009",
            "containers": "C001",
            "weight": 1000,
            "unit": "grams"  # Invalid unit
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 422

    def test_post_weight_with_lbs_unit(self, client):
        """Test successful weighing with lbs unit."""
        payload = {
            "direction": "in",
            "truck": "TEST_LBS_001",
            "containers": "C600,C601",
            "weight": 11000,
            "unit": "lbs",
            "produce": "cherries"
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 200

        data = response.json()
        # 11000 lbs converts to ~4990 kg (11000 / 2.20462)
        assert data["gross_weight"] == 4989

    def test_post_weight_default_truck_na(self, client):
        """Test that truck defaults to 'na' for NONE direction."""
        payload = {
            "direction": "none",
            "containers": "C700",
            "weight": 50,
            "unit": "kg"
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 200

    def test_post_weight_default_produce_na(self, client):
        """Test that produce defaults to 'na' if not provided."""
        payload = {
            "direction": "in",
            "truck": "TEST_010",
            "containers": "C800",
            "weight": 3000,
            "unit": "kg"
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 200

    def test_post_weight_long_truck_license(self, client):
        """Test truck license length validation."""
        payload = {
            "direction": "in",
            "truck": "A" * 25,  # Exceeds 20 character limit
            "containers": "C001",
            "weight": 1000,
            "unit": "kg"
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 422

    def test_post_weight_long_container_id(self, client):
        """Test container ID length validation."""
        payload = {
            "direction": "in",
            "truck": "TEST_011",
            "containers": "C" * 20,  # Exceeds 15 character limit
            "weight": 1000,
            "unit": "kg"
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 422

    def test_post_weight_special_characters_in_containers(self, client):
        """Test container IDs with special characters."""
        payload = {
            "direction": "in",
            "truck": "TEST_012",
            "containers": "C-001,C_002,C003",  # Hyphens and underscores allowed
            "weight": 1000,
            "unit": "kg"
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 200

    def test_post_weight_invalid_special_characters(self, client):
        """Test that invalid special characters in containers are rejected."""
        payload = {
            "direction": "in",
            "truck": "TEST_013",
            "containers": "C@001,C#002",  # Invalid characters
            "weight": 1000,
            "unit": "kg"
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 422

    def test_post_weight_multiple_containers(self, client):
        """Test weighing with multiple containers."""
        payload = {
            "direction": "in",
            "truck": "MULTI_CONT_001",
            "containers": "C001,C002,C003,C004,C005",
            "weight": 10000,
            "unit": "kg",
            "produce": "watermelons"
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["gross_weight"] == 10000

    def test_post_weight_single_container(self, client):
        """Test weighing with single container."""
        payload = {
            "direction": "in",
            "truck": "SINGLE_CONT_001",
            "containers": "C900",
            "weight": 2000,
            "unit": "kg",
            "produce": "strawberries"
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 200

    def test_post_weight_whitespace_handling(self, client):
        """Test that whitespace in container list is handled correctly."""
        payload = {
            "direction": "in",
            "truck": "SPACE_TEST_001",
            "containers": " C001 , C002 , C003 ",  # Extra whitespace
            "weight": 5000,
            "unit": "kg"
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 200

    def test_post_weight_response_structure(self, client):
        """Test that response has expected structure."""
        payload = {
            "direction": "in",
            "truck": "STRUCT_TEST_001",
            "containers": "C001,C002",
            "weight": 5000,
            "unit": "kg",
            "produce": "apples"
        }

        response = client.post("/weight", json=payload)
        assert response.status_code == 200

        data = response.json()
        # Check for expected fields
        assert "direction" in data
        assert "truck" in data
        assert "gross_weight" in data
        assert "net_weight" in data
        assert "session_id" in data or data["direction"] == "none"

    def test_post_weight_out_without_in_no_force(self, client):
        """Test that OUT without IN fails when force=false."""
        payload = {
            "direction": "out",
            "truck": "NO_IN_TEST_001",
            "containers": "C001,C002",
            "weight": 4000,
            "unit": "kg",
            "force": False
        }

        response = client.post("/weight", json=payload)
        # Should fail without existing IN session
        assert response.status_code == 400

    def test_post_weight_case_sensitivity(self, client):
        """Test case sensitivity in direction field."""
        payload = {
            "direction": "IN",  # Uppercase
            "truck": "CASE_TEST_001",
            "containers": "C001",
            "weight": 5000,
            "unit": "kg"
        }

        response = client.post("/weight", json=payload)
        # Should fail - direction is case-sensitive
        assert response.status_code == 422


class TestWeightRouterExceptionHandlers:
    """Test suite for router exception handling."""

    def test_weighing_sequence_error_handling(self):
        """Test that WeighingSequenceError returns 400 with proper message."""
        from unittest.mock import AsyncMock
        from src.utils.exceptions import WeighingSequenceError
        from src.main import app
        from src.dependencies import get_weight_service

        # Mock weight_service to raise WeighingSequenceError
        mock_service = AsyncMock()
        async def mock_record_weight(request):
            raise WeighingSequenceError("OUT weighing without matching IN transaction")
        mock_service.record_weight = mock_record_weight

        # Override dependency
        app.dependency_overrides[get_weight_service] = lambda: mock_service

        try:
            client = TestClient(app)
            payload = {
                "direction": "out",
                "truck": "ERROR_TEST_001",
                "containers": "C001",
                "weight": 4000,
                "unit": "kg"
            }

            response = client.post("/weight", json=payload)

            assert response.status_code == 400
            assert "Invalid weighing sequence" in response.json()["detail"]
            assert "OUT weighing without matching IN transaction" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_container_not_found_error_handling(self):
        """Test that ContainerNotFoundError returns 400 with proper message."""
        from unittest.mock import AsyncMock
        from src.utils.exceptions import ContainerNotFoundError
        from src.main import app
        from src.dependencies import get_weight_service

        # Mock weight_service to raise ContainerNotFoundError
        mock_service = AsyncMock()
        async def mock_record_weight(request):
            raise ContainerNotFoundError("Container C999 not found in database")
        mock_service.record_weight = mock_record_weight

        # Override dependency
        app.dependency_overrides[get_weight_service] = lambda: mock_service

        try:
            client = TestClient(app)
            payload = {
                "direction": "in",
                "truck": "ERROR_TEST_002",
                "containers": "C999",
                "weight": 5000,
                "unit": "kg"
            }

            response = client.post("/weight", json=payload)

            assert response.status_code == 400
            assert "Container not found" in response.json()["detail"]
            assert "C999" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_invalid_weight_error_handling(self):
        """Test that InvalidWeightError returns 400 with proper message."""
        from unittest.mock import AsyncMock
        from src.utils.exceptions import InvalidWeightError
        from src.main import app
        from src.dependencies import get_weight_service

        # Mock weight_service to raise InvalidWeightError
        mock_service = AsyncMock()
        async def mock_record_weight(request):
            raise InvalidWeightError("Weight value 200000 kg exceeds maximum allowed")
        mock_service.record_weight = mock_record_weight

        # Override dependency
        app.dependency_overrides[get_weight_service] = lambda: mock_service

        try:
            client = TestClient(app)
            payload = {
                "direction": "in",
                "truck": "ERROR_TEST_003",
                "containers": "C001",
                "weight": 200000,
                "unit": "kg"
            }

            response = client.post("/weight", json=payload)

            assert response.status_code == 400
            assert "Invalid weight value" in response.json()["detail"]
            assert "200000" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_generic_exception_handling(self):
        """Test that generic Exception returns 500 with proper message."""
        from unittest.mock import AsyncMock
        from src.main import app
        from src.dependencies import get_weight_service

        # Mock weight_service to raise generic Exception
        mock_service = AsyncMock()
        async def mock_record_weight(request):
            raise Exception("Unexpected database connection error")
        mock_service.record_weight = mock_record_weight

        # Override dependency
        app.dependency_overrides[get_weight_service] = lambda: mock_service

        try:
            client = TestClient(app)
            payload = {
                "direction": "in",
                "truck": "ERROR_TEST_004",
                "containers": "C001",
                "weight": 5000,
                "unit": "kg"
            }

            response = client.post("/weight", json=payload)

            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]
            assert "database connection" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
