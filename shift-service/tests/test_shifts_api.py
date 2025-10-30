"""Tests for shift management endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text


class TestStartShift:
    """Tests for POST /shifts/start endpoint."""

    def test_start_shift_success(self, client: TestClient, sample_operator: dict):
        """Test successfully starting a shift."""
        shift_data = {
            "operator_id": sample_operator["id"],
            "shift_type": "morning"
        }

        response = client.post("/shifts/start", json=shift_data)

        assert response.status_code == 201
        data = response.json()
        assert data["operator_id"] == sample_operator["id"]
        assert data["shift_type"] == "morning"
        assert data["end_time"] is None
        assert data["duration_minutes"] is None
        assert data["transactions_processed"] == 0
        assert "id" in data
        assert "start_time" in data

    def test_start_shift_afternoon(self, client: TestClient, sample_operator: dict):
        """Test starting an afternoon shift."""
        shift_data = {
            "operator_id": sample_operator["id"],
            "shift_type": "afternoon"
        }

        response = client.post("/shifts/start", json=shift_data)

        assert response.status_code == 201
        data = response.json()
        assert data["shift_type"] == "afternoon"

    def test_start_shift_night(self, client: TestClient, sample_operator: dict):
        """Test starting a night shift."""
        shift_data = {
            "operator_id": sample_operator["id"],
            "shift_type": "night"
        }

        response = client.post("/shifts/start", json=shift_data)

        assert response.status_code == 201
        data = response.json()
        assert data["shift_type"] == "night"

    def test_start_shift_operator_not_found(self, client: TestClient):
        """Test starting shift with non-existent operator fails."""
        shift_data = {
            "operator_id": 99999,
            "shift_type": "morning"
        }

        response = client.post("/shifts/start", json=shift_data)

        assert response.status_code == 404
        assert "Operator not found" in response.json()["detail"]

    def test_start_shift_inactive_operator(self, client: TestClient, inactive_operator: dict):
        """Test starting shift with inactive operator fails."""
        shift_data = {
            "operator_id": inactive_operator["id"],
            "shift_type": "morning"
        }

        response = client.post("/shifts/start", json=shift_data)

        assert response.status_code == 404
        assert "Operator not found or inactive" in response.json()["detail"]

    def test_start_shift_duplicate_active_shift(self, client: TestClient, sample_operator: dict, active_shift: dict):
        """Test starting shift when operator already has active shift fails."""
        shift_data = {
            "operator_id": sample_operator["id"],
            "shift_type": "afternoon"
        }

        response = client.post("/shifts/start", json=shift_data)

        assert response.status_code == 400
        assert "already has an active shift" in response.json()["detail"]

    def test_start_shift_after_ending_previous(self, client: TestClient, sample_operator: dict, active_shift: dict):
        """Test starting new shift after ending previous one."""
        # End the active shift
        end_data = {"notes": "Shift completed"}
        end_response = client.post(f"/shifts/{active_shift['id']}/end", json=end_data)
        assert end_response.status_code == 200

        # Start new shift
        shift_data = {
            "operator_id": sample_operator["id"],
            "shift_type": "afternoon"
        }

        response = client.post("/shifts/start", json=shift_data)

        assert response.status_code == 201
        data = response.json()
        assert data["operator_id"] == sample_operator["id"]
        assert data["id"] != active_shift["id"]

    def test_start_shift_invalid_type(self, client: TestClient, sample_operator: dict):
        """Test starting shift with invalid shift type fails."""
        shift_data = {
            "operator_id": sample_operator["id"],
            "shift_type": "invalid_type"
        }

        response = client.post("/shifts/start", json=shift_data)

        assert response.status_code == 422  # Validation error

    def test_start_shift_missing_operator_id(self, client: TestClient):
        """Test starting shift without operator_id fails."""
        shift_data = {
            "shift_type": "morning"
        }

        response = client.post("/shifts/start", json=shift_data)

        assert response.status_code == 422  # Validation error

    def test_start_shift_missing_shift_type(self, client: TestClient, sample_operator: dict):
        """Test starting shift without shift_type fails."""
        shift_data = {
            "operator_id": sample_operator["id"]
        }

        response = client.post("/shifts/start", json=shift_data)

        assert response.status_code == 422  # Validation error


class TestEndShift:
    """Tests for POST /shifts/{shift_id}/end endpoint."""

    def test_end_shift_success(self, client: TestClient, active_shift: dict):
        """Test successfully ending an active shift."""
        end_data = {"notes": "Completed successfully"}

        response = client.post(f"/shifts/{active_shift['id']}/end", json=end_data)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == active_shift["id"]
        assert data["end_time"] is not None
        assert data["duration_minutes"] is not None
        assert data["notes"] == "Completed successfully"

    def test_end_shift_without_notes(self, client: TestClient, active_shift: dict):
        """Test ending shift without notes."""
        end_data = {}

        response = client.post(f"/shifts/{active_shift['id']}/end", json=end_data)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == active_shift["id"]
        assert data["end_time"] is not None
        assert data["notes"] is None

    def test_end_shift_with_null_notes(self, client: TestClient, active_shift: dict):
        """Test ending shift with null notes."""
        end_data = {"notes": None}

        response = client.post(f"/shifts/{active_shift['id']}/end", json=end_data)

        assert response.status_code == 200
        data = response.json()
        assert data["notes"] is None

    def test_end_shift_long_notes(self, client: TestClient, active_shift: dict):
        """Test ending shift with long notes."""
        end_data = {"notes": "A" * 500}  # Max length

        response = client.post(f"/shifts/{active_shift['id']}/end", json=end_data)

        assert response.status_code == 200
        data = response.json()
        assert len(data["notes"]) == 500

    def test_end_shift_too_long_notes(self, client: TestClient, active_shift: dict):
        """Test ending shift with notes exceeding max length fails."""
        end_data = {"notes": "A" * 501}  # Exceeds max length

        response = client.post(f"/shifts/{active_shift['id']}/end", json=end_data)

        assert response.status_code == 422  # Validation error

    def test_end_shift_not_found(self, client: TestClient):
        """Test ending non-existent shift fails."""
        end_data = {"notes": "Test"}

        response = client.post("/shifts/99999/end", json=end_data)

        assert response.status_code == 404
        assert "Active shift not found" in response.json()["detail"]

    def test_end_shift_already_ended(self, client: TestClient, completed_shift: dict):
        """Test ending already completed shift fails."""
        end_data = {"notes": "Trying to end again"}

        response = client.post(f"/shifts/{completed_shift['id']}/end", json=end_data)

        assert response.status_code == 404
        assert "Active shift not found" in response.json()["detail"]

    def test_end_shift_twice(self, client: TestClient, active_shift: dict):
        """Test ending shift twice fails."""
        end_data = {"notes": "First end"}

        # End shift first time
        response1 = client.post(f"/shifts/{active_shift['id']}/end", json=end_data)
        assert response1.status_code == 200

        # Try to end again
        response2 = client.post(f"/shifts/{active_shift['id']}/end", json=end_data)
        assert response2.status_code == 404


class TestListShifts:
    """Tests for GET /shifts endpoint."""

    def test_list_shifts_empty(self, client: TestClient):
        """Test listing shifts when none exist."""
        response = client.get("/shifts")

        assert response.status_code == 200
        data = response.json()
        assert data["shifts"] == []
        assert data["total"] == 0

    def test_list_shifts_single(self, client: TestClient, active_shift: dict):
        """Test listing shifts with one shift."""
        response = client.get("/shifts")

        assert response.status_code == 200
        data = response.json()
        assert len(data["shifts"]) == 1
        assert data["total"] == 1
        assert data["shifts"][0]["id"] == active_shift["id"]

    def test_list_shifts_multiple(self, client: TestClient, multiple_shifts: list):
        """Test listing multiple shifts."""
        response = client.get("/shifts")

        assert response.status_code == 200
        data = response.json()
        assert len(data["shifts"]) == 10
        assert data["total"] == 10

    def test_list_shifts_active_only(self, client: TestClient, multiple_shifts: list):
        """Test listing only active shifts."""
        response = client.get("/shifts?active_only=true")

        assert response.status_code == 200
        data = response.json()

        # Count how many active shifts we have in the fixture
        active_count = sum(1 for s in multiple_shifts if s["end_time"] is None)
        assert len(data["shifts"]) == active_count
        assert data["total"] == active_count

        # Verify all returned shifts are active
        for shift in data["shifts"]:
            assert shift["end_time"] is None

    def test_list_shifts_by_operator(self, client: TestClient, sample_operator: dict, multiple_shifts: list):
        """Test listing shifts filtered by operator."""
        response = client.get(f"/shifts?operator_id={sample_operator['id']}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["shifts"]) == 10
        assert data["total"] == 10

        # Verify all shifts belong to the operator
        for shift in data["shifts"]:
            assert shift["operator_id"] == sample_operator["id"]

    def test_list_shifts_by_nonexistent_operator(self, client: TestClient, multiple_shifts: list):
        """Test listing shifts for non-existent operator returns empty list."""
        response = client.get("/shifts?operator_id=99999")

        assert response.status_code == 200
        data = response.json()
        assert len(data["shifts"]) == 0
        assert data["total"] == 0

    def test_list_shifts_pagination_limit(self, client: TestClient, multiple_shifts: list):
        """Test pagination with limit parameter."""
        response = client.get("/shifts?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data["shifts"]) == 5
        assert data["total"] == 10

    def test_list_shifts_pagination_offset(self, client: TestClient, multiple_shifts: list):
        """Test pagination with offset parameter."""
        response = client.get("/shifts?limit=5&offset=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data["shifts"]) == 5
        assert data["total"] == 10

    def test_list_shifts_pagination_last_page(self, client: TestClient, multiple_shifts: list):
        """Test pagination on last page with fewer results."""
        response = client.get("/shifts?limit=7&offset=7")

        assert response.status_code == 200
        data = response.json()
        assert len(data["shifts"]) == 3
        assert data["total"] == 10

    def test_list_shifts_pagination_beyond_total(self, client: TestClient, multiple_shifts: list):
        """Test pagination beyond total returns empty list."""
        response = client.get("/shifts?limit=10&offset=20")

        assert response.status_code == 200
        data = response.json()
        assert len(data["shifts"]) == 0
        assert data["total"] == 10

    def test_list_shifts_sorted_by_start_time_desc(self, client: TestClient, multiple_shifts: list):
        """Test that shifts are sorted by start_time descending."""
        response = client.get("/shifts")

        assert response.status_code == 200
        data = response.json()

        # Verify descending order (most recent first)
        for i in range(len(data["shifts"]) - 1):
            current = data["shifts"][i]["start_time"]
            next_item = data["shifts"][i + 1]["start_time"]
            assert current >= next_item

    def test_list_shifts_combined_filters(self, client: TestClient, sample_operator: dict, multiple_shifts: list):
        """Test combining operator_id and active_only filters."""
        response = client.get(f"/shifts?operator_id={sample_operator['id']}&active_only=true")

        assert response.status_code == 200
        data = response.json()

        # Count active shifts for this operator in fixture
        active_count = sum(1 for s in multiple_shifts if s["end_time"] is None and s["operator_id"] == sample_operator["id"])
        assert len(data["shifts"]) == active_count
        assert data["total"] == active_count

        # Verify all returned shifts match both filters
        for shift in data["shifts"]:
            assert shift["operator_id"] == sample_operator["id"]
            assert shift["end_time"] is None

    def test_list_shifts_limit_validation_min(self, client: TestClient, multiple_shifts: list):
        """Test that limit must be at least 1."""
        response = client.get("/shifts?limit=0")

        assert response.status_code == 422  # Validation error

    def test_list_shifts_limit_validation_max(self, client: TestClient, multiple_shifts: list):
        """Test that limit cannot exceed 100."""
        response = client.get("/shifts?limit=101")

        assert response.status_code == 422  # Validation error

    def test_list_shifts_offset_validation(self, client: TestClient, multiple_shifts: list):
        """Test that offset cannot be negative."""
        response = client.get("/shifts?offset=-1")

        assert response.status_code == 422  # Validation error

    def test_list_shifts_default_limit(self, client: TestClient, db_session: Session, sample_operator: dict):
        """Test default limit of 50."""
        # Create 60 shifts
        for i in range(60):
            query = text("""
                INSERT INTO shifts (operator_id, shift_type, start_time, transactions_processed)
                VALUES (:operator_id, :shift_type, CURRENT_TIMESTAMP, 0)
            """)
            db_session.execute(
                query,
                {
                    "operator_id": sample_operator["id"],
                    "shift_type": "morning",
                }
            )
        db_session.commit()

        response = client.get("/shifts")

        assert response.status_code == 200
        data = response.json()
        assert len(data["shifts"]) == 50  # Default limit
        assert data["total"] == 60

    def test_list_shifts_response_structure(self, client: TestClient, active_shift: dict):
        """Test that shift response has correct structure."""
        response = client.get("/shifts")

        assert response.status_code == 200
        data = response.json()

        # Verify top-level structure
        assert "shifts" in data
        assert "total" in data

        # Verify shift structure
        shift = data["shifts"][0]
        assert "id" in shift
        assert "operator_id" in shift
        assert "shift_type" in shift
        assert "start_time" in shift
        assert "end_time" in shift
        assert "duration_minutes" in shift
        assert "transactions_processed" in shift
        assert "notes" in shift


class TestGetShift:
    """Tests for GET /shifts/{shift_id} endpoint."""

    def test_get_shift_success(self, client: TestClient, active_shift: dict):
        """Test successfully getting a shift by ID."""
        response = client.get(f"/shifts/{active_shift['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == active_shift["id"]
        assert data["operator_id"] == active_shift["operator_id"]
        assert data["shift_type"] == active_shift["shift_type"]
        assert "start_time" in data

    def test_get_shift_completed(self, client: TestClient, completed_shift: dict):
        """Test getting a completed shift."""
        response = client.get(f"/shifts/{completed_shift['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == completed_shift["id"]
        assert data["end_time"] is not None
        assert data["duration_minutes"] is not None

    def test_get_shift_not_found(self, client: TestClient):
        """Test getting non-existent shift returns 404."""
        response = client.get("/shifts/99999")

        assert response.status_code == 404
        assert "Shift not found" in response.json()["detail"]

    def test_get_shift_response_structure(self, client: TestClient, active_shift: dict):
        """Test that shift response has correct structure."""
        response = client.get(f"/shifts/{active_shift['id']}")

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields
        assert "id" in data
        assert "operator_id" in data
        assert "shift_type" in data
        assert "start_time" in data
        assert "end_time" in data
        assert "duration_minutes" in data
        assert "transactions_processed" in data
        assert "notes" in data

    def test_get_shift_invalid_id_format(self, client: TestClient):
        """Test getting shift with invalid ID format."""
        response = client.get("/shifts/invalid")

        assert response.status_code == 422  # Validation error
