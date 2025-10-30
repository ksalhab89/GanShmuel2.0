"""Tests for operator management endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestCreateOperator:
    """Tests for POST /shifts/operators endpoint."""

    def test_create_operator_success(self, client: TestClient):
        """Test successful operator creation."""
        operator_data = {
            "name": "Jane Smith",
            "employee_id": "EMP123",
            "role": "weigher"
        }

        response = client.post("/shifts/operators", json=operator_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == operator_data["name"]
        assert data["employee_id"] == operator_data["employee_id"]
        assert data["role"] == operator_data["role"]
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    def test_create_operator_supervisor_role(self, client: TestClient):
        """Test creating operator with supervisor role."""
        operator_data = {
            "name": "Bob Manager",
            "employee_id": "EMP456",
            "role": "supervisor"
        }

        response = client.post("/shifts/operators", json=operator_data)

        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "supervisor"

    def test_create_operator_admin_role(self, client: TestClient):
        """Test creating operator with admin role."""
        operator_data = {
            "name": "Alice Admin",
            "employee_id": "EMP789",
            "role": "admin"
        }

        response = client.post("/shifts/operators", json=operator_data)

        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "admin"

    def test_create_operator_default_role(self, client: TestClient):
        """Test creating operator with default role."""
        operator_data = {
            "name": "Default User",
            "employee_id": "EMP999"
        }

        response = client.post("/shifts/operators", json=operator_data)

        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "weigher"

    def test_create_operator_duplicate_employee_id(self, client: TestClient, sample_operator: dict):
        """Test creating operator with duplicate employee ID fails."""
        operator_data = {
            "name": "Duplicate User",
            "employee_id": sample_operator["employee_id"],  # Duplicate
            "role": "weigher"
        }

        response = client.post("/shifts/operators", json=operator_data)

        assert response.status_code == 400
        assert "Failed to create operator" in response.json()["detail"]

    def test_create_operator_invalid_role(self, client: TestClient):
        """Test creating operator with invalid role fails validation."""
        operator_data = {
            "name": "Invalid Role User",
            "employee_id": "EMP888",
            "role": "invalid_role"
        }

        response = client.post("/shifts/operators", json=operator_data)

        assert response.status_code == 422  # Validation error

    def test_create_operator_missing_name(self, client: TestClient):
        """Test creating operator without name fails validation."""
        operator_data = {
            "employee_id": "EMP777",
            "role": "weigher"
        }

        response = client.post("/shifts/operators", json=operator_data)

        assert response.status_code == 422  # Validation error

    def test_create_operator_missing_employee_id(self, client: TestClient):
        """Test creating operator without employee_id fails validation."""
        operator_data = {
            "name": "Missing ID User",
            "role": "weigher"
        }

        response = client.post("/shifts/operators", json=operator_data)

        assert response.status_code == 422  # Validation error

    def test_create_operator_empty_name(self, client: TestClient):
        """Test creating operator with empty name fails validation."""
        operator_data = {
            "name": "",
            "employee_id": "EMP666",
            "role": "weigher"
        }

        response = client.post("/shifts/operators", json=operator_data)

        assert response.status_code == 422  # Validation error

    def test_create_operator_empty_employee_id(self, client: TestClient):
        """Test creating operator with empty employee_id fails validation."""
        operator_data = {
            "name": "Empty ID User",
            "employee_id": "",
            "role": "weigher"
        }

        response = client.post("/shifts/operators", json=operator_data)

        assert response.status_code == 422  # Validation error

    def test_create_operator_long_name(self, client: TestClient):
        """Test creating operator with name at max length."""
        operator_data = {
            "name": "A" * 100,  # Max length
            "employee_id": "EMP555",
            "role": "weigher"
        }

        response = client.post("/shifts/operators", json=operator_data)

        assert response.status_code == 201

    def test_create_operator_too_long_name(self, client: TestClient):
        """Test creating operator with name exceeding max length fails."""
        operator_data = {
            "name": "A" * 101,  # Exceeds max length
            "employee_id": "EMP444",
            "role": "weigher"
        }

        response = client.post("/shifts/operators", json=operator_data)

        assert response.status_code == 422  # Validation error


class TestListOperators:
    """Tests for GET /shifts/operators endpoint."""

    def test_list_operators_empty(self, client: TestClient):
        """Test listing operators when none exist."""
        response = client.get("/shifts/operators")

        assert response.status_code == 200
        data = response.json()
        assert data["operators"] == []
        assert data["total"] == 0

    def test_list_operators_single(self, client: TestClient, sample_operator: dict):
        """Test listing operators with one operator."""
        response = client.get("/shifts/operators")

        assert response.status_code == 200
        data = response.json()
        assert len(data["operators"]) == 1
        assert data["total"] == 1
        assert data["operators"][0]["id"] == sample_operator["id"]
        assert data["operators"][0]["name"] == sample_operator["name"]

    def test_list_operators_multiple(self, client: TestClient, multiple_operators: list):
        """Test listing multiple operators."""
        response = client.get("/shifts/operators")

        assert response.status_code == 200
        data = response.json()
        assert len(data["operators"]) == 5
        assert data["total"] == 5

    def test_list_operators_active_only(self, client: TestClient, sample_operator: dict, inactive_operator: dict):
        """Test listing only active operators."""
        response = client.get("/shifts/operators?active_only=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data["operators"]) == 1
        assert data["total"] == 1
        assert data["operators"][0]["id"] == sample_operator["id"]
        assert data["operators"][0]["is_active"] is True

    def test_list_operators_include_inactive(self, client: TestClient, sample_operator: dict, inactive_operator: dict):
        """Test listing all operators including inactive."""
        response = client.get("/shifts/operators?active_only=false")

        assert response.status_code == 200
        data = response.json()
        assert len(data["operators"]) == 2
        assert data["total"] == 2

        # Verify both active and inactive are included
        operator_ids = [op["id"] for op in data["operators"]]
        assert sample_operator["id"] in operator_ids
        assert inactive_operator["id"] in operator_ids

    def test_list_operators_sorted_by_name(self, client: TestClient, multiple_operators: list):
        """Test that operators are sorted by name."""
        response = client.get("/shifts/operators")

        assert response.status_code == 200
        data = response.json()

        names = [op["name"] for op in data["operators"]]
        assert names == sorted(names)

    def test_list_operators_response_structure(self, client: TestClient, sample_operator: dict):
        """Test that operator response has correct structure."""
        response = client.get("/shifts/operators")

        assert response.status_code == 200
        data = response.json()

        # Verify top-level structure
        assert "operators" in data
        assert "total" in data

        # Verify operator structure
        operator = data["operators"][0]
        assert "id" in operator
        assert "name" in operator
        assert "employee_id" in operator
        assert "role" in operator
        assert "is_active" in operator
        assert "created_at" in operator
