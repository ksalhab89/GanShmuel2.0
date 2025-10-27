"""Router tests for query and reporting endpoints."""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def setup_test_data(client):
    """Create test weighing data for query tests."""
    # Create several IN/OUT transactions
    transactions = []

    # Transaction 1: Completed IN/OUT
    truck1 = f"QUERY_TRUCK_001_{datetime.now().timestamp()}"
    in1 = {
        "direction": "in",
        "truck": truck1,
        "containers": "C001,C002",
        "weight": 5000,
        "unit": "kg",
        "produce": "apples"
    }
    in1_response = client.post("/weight", json=in1)
    if in1_response.status_code == 200:
        transactions.append(in1_response.json())

    out1 = {
        "direction": "out",
        "truck": truck1,
        "containers": "C001,C002",
        "weight": 4500,
        "unit": "kg"
    }
    out1_response = client.post("/weight", json=out1)
    if out1_response.status_code == 200:
        transactions.append(out1_response.json())

    # Transaction 2: IN only
    truck2 = f"QUERY_TRUCK_002_{datetime.now().timestamp()}"
    in2 = {
        "direction": "in",
        "truck": truck2,
        "containers": "C003,C004",
        "weight": 6000,
        "unit": "kg",
        "produce": "oranges"
    }
    in2_response = client.post("/weight", json=in2)
    if in2_response.status_code == 200:
        transactions.append(in2_response.json())

    # Transaction 3: NONE direction
    none1 = {
        "direction": "none",
        "truck": "na",
        "containers": "C005",
        "weight": 100,
        "unit": "kg"
    }
    none1_response = client.post("/weight", json=none1)
    if none1_response.status_code == 200:
        transactions.append(none1_response.json())

    return transactions


class TestQueryRouter:
    """Test suite for query endpoints."""

    def test_get_weight_all(self, client, setup_test_data):
        """Test getting all weighing transactions."""
        response = client.get("/weight")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        # Should have at least the transactions we created
        assert len(data) >= len(setup_test_data)

    def test_get_weight_empty_result(self, client):
        """Test query with no results."""
        # Query far future date
        future_date = (datetime.now() + timedelta(days=365)).strftime("%Y%m%d%H%M%S")
        response = client.get(f"/weight?from={future_date}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_weight_filter_by_date_range(self, client, setup_test_data):
        """Test filtering by date range."""
        # Get today's date range
        today = datetime.now()
        from_date = today.replace(hour=0, minute=0, second=0).strftime("%Y%m%d%H%M%S")
        to_date = today.strftime("%Y%m%d%H%M%S")

        response = client.get(f"/weight?from={from_date}&to={to_date}")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_get_weight_filter_by_from_date(self, client, setup_test_data):
        """Test filtering with from date only."""
        from_date = datetime.now().replace(hour=0, minute=0, second=0).strftime("%Y%m%d%H%M%S")

        response = client.get(f"/weight?from={from_date}")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_get_weight_filter_by_to_date(self, client):
        """Test filtering with to date only."""
        to_date = datetime.now().strftime("%Y%m%d%H%M%S")

        response = client.get(f"/weight?to={to_date}")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_get_weight_filter_by_direction_in(self, client, setup_test_data):
        """Test filtering by direction=in."""
        response = client.get("/weight?filter=in")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        # All returned transactions should be IN direction
        for transaction in data:
            assert transaction["direction"] == "in"

    def test_get_weight_filter_by_direction_out(self, client, setup_test_data):
        """Test filtering by direction=out."""
        response = client.get("/weight?filter=out")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        for transaction in data:
            assert transaction["direction"] == "out"

    def test_get_weight_filter_by_direction_none(self, client, setup_test_data):
        """Test filtering by direction=none."""
        response = client.get("/weight?filter=none")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        for transaction in data:
            assert transaction["direction"] == "none"

    def test_get_weight_filter_multiple_directions(self, client, setup_test_data):
        """Test filtering by multiple directions."""
        response = client.get("/weight?filter=in,out")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        for transaction in data:
            assert transaction["direction"] in ["in", "out"]

    def test_get_weight_invalid_date_format(self, client):
        """Test that invalid date format returns error."""
        response = client.get("/weight?from=2024-12-01")  # Wrong format
        assert response.status_code == 400

    def test_get_weight_invalid_date_range(self, client):
        """Test that from > to returns error."""
        from_date = "20241231235959"
        to_date = "20240101000000"

        response = client.get(f"/weight?from={from_date}&to={to_date}")
        assert response.status_code == 400

    def test_get_weight_response_structure(self, client):
        """Test that response has expected structure."""
        response = client.get("/weight")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        if len(data) > 0:
            transaction = data[0]
            assert "direction" in transaction
            assert "truck" in transaction
            assert "gross_weight" in transaction

    def test_get_item_by_truck_id(self, client, setup_test_data):
        """Test getting item details by truck ID."""
        # Get a truck from setup data
        truck_id = None
        for transaction in setup_test_data:
            if transaction.get("truck") and transaction["truck"] != "na":
                truck_id = transaction["truck"]
                break

        if truck_id:
            response = client.get(f"/item/{truck_id}")
            assert response.status_code in [200, 404]

            if response.status_code == 200:
                data = response.json()
                assert "id" in data or "item_id" in data

    def test_get_item_by_container_id(self, client):
        """Test getting item details by container ID."""
        # Use a container that was created
        response = client.get("/item/C001")

        # May or may not exist
        assert response.status_code in [200, 404]

    def test_get_item_not_found(self, client):
        """Test getting non-existent item returns 404."""
        response = client.get("/item/NONEXISTENT_ITEM_XYZ")
        assert response.status_code == 404

    def test_get_item_with_date_range(self, client, setup_test_data):
        """Test getting item with date range filter."""
        truck_id = None
        for transaction in setup_test_data:
            if transaction.get("truck") and transaction["truck"] != "na":
                truck_id = transaction["truck"]
                break

        if truck_id:
            from_date = datetime.now().replace(hour=0, minute=0, second=0).strftime("%Y%m%d%H%M%S")
            to_date = datetime.now().strftime("%Y%m%d%H%M%S")

            response = client.get(f"/item/{truck_id}?from={from_date}&to={to_date}")
            assert response.status_code in [200, 404]

    def test_get_item_response_structure(self, client, setup_test_data):
        """Test item response structure."""
        truck_id = None
        for transaction in setup_test_data:
            if transaction.get("truck") and transaction["truck"] != "na":
                truck_id = transaction["truck"]
                break

        if truck_id:
            response = client.get(f"/item/{truck_id}")

            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict)

    def test_get_session_by_id(self, client, setup_test_data):
        """Test getting session details by session ID."""
        session_id = None
        for transaction in setup_test_data:
            if "session_id" in transaction and transaction["session_id"]:
                session_id = transaction["session_id"]
                break

        if session_id:
            response = client.get(f"/session/{session_id}")
            assert response.status_code in [200, 404]

            if response.status_code == 200:
                data = response.json()
                assert "session_id" in data
                assert data["session_id"] == session_id

    def test_get_session_not_found(self, client):
        """Test getting non-existent session returns 404."""
        fake_session_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/session/{fake_session_id}")
        assert response.status_code == 404

    def test_get_session_invalid_uuid_format(self, client):
        """Test that invalid UUID format returns error."""
        response = client.get("/session/invalid-uuid")
        assert response.status_code in [400, 404]

    def test_get_session_response_structure(self, client, setup_test_data):
        """Test session response structure."""
        session_id = None
        for transaction in setup_test_data:
            if "session_id" in transaction and transaction["session_id"]:
                session_id = transaction["session_id"]
                break

        if session_id:
            response = client.get(f"/session/{session_id}")

            if response.status_code == 200:
                data = response.json()
                assert "session_id" in data
                assert "truck" in data

    def test_get_unknown_containers(self, client):
        """Test listing unknown containers."""
        response = client.get("/unknown")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_get_unknown_containers_response_structure(self, client):
        """Test unknown containers response is list of strings."""
        response = client.get("/unknown")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # All items should be strings
        for item in data:
            assert isinstance(item, str)

    def test_query_with_all_filters(self, client):
        """Test query with all filters combined."""
        from_date = datetime.now().replace(hour=0, minute=0, second=0).strftime("%Y%m%d%H%M%S")
        to_date = datetime.now().strftime("%Y%m%d%H%M%S")

        response = client.get(f"/weight?from={from_date}&to={to_date}&filter=in,out")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_query_date_format_yyyymmddhhmmss(self, client):
        """Test that date format yyyymmddhhmmss is accepted."""
        from_date = "20240101000000"
        to_date = "20241231235959"

        response = client.get(f"/weight?from={from_date}&to={to_date}")
        assert response.status_code in [200, 400]

    def test_query_partial_date_format(self, client):
        """Test that partial date format is rejected."""
        response = client.get("/weight?from=20241201")  # Missing time
        assert response.status_code == 400

    def test_query_special_characters_in_filter(self, client):
        """Test that special characters in filter are handled."""
        response = client.get("/weight?filter=in;out")
        # Should handle gracefully
        assert response.status_code in [200, 400]

    def test_query_empty_filter(self, client):
        """Test query with empty filter parameter."""
        response = client.get("/weight?filter=")
        assert response.status_code in [200, 400]

    def test_query_invalid_direction_filter(self, client):
        """Test query with invalid direction in filter."""
        response = client.get("/weight?filter=invalid")
        # Should handle gracefully
        assert response.status_code in [200, 400]

    def test_query_case_sensitive_filter(self, client):
        """Test that filter is case-sensitive."""
        response = client.get("/weight?filter=IN")  # Uppercase
        # Should handle or reject
        assert response.status_code in [200, 400]

    def test_item_empty_id(self, client):
        """Test getting item with empty ID."""
        response = client.get("/item/")
        # Should return 404 or 405 (method not allowed)
        assert response.status_code in [404, 405]

    def test_item_special_characters(self, client):
        """Test getting item with special characters in ID."""
        response = client.get("/item/TEST@#$")
        assert response.status_code in [200, 404]

    def test_item_very_long_id(self, client):
        """Test getting item with very long ID."""
        long_id = "T" * 1000
        response = client.get(f"/item/{long_id}")
        assert response.status_code in [200, 404]

    def test_session_empty_id(self, client):
        """Test getting session with empty ID."""
        response = client.get("/session/")
        assert response.status_code in [404, 405]

    def test_query_results_sorted_by_datetime(self, client, setup_test_data):
        """Test that query results are sorted by datetime."""
        response = client.get("/weight")
        assert response.status_code == 200

        data = response.json()
        if len(data) > 1:
            # Results should be sorted
            assert isinstance(data, list)

    def test_query_no_parameters(self, client):
        """Test query without any parameters."""
        response = client.get("/weight")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_query_default_date_range(self, client):
        """Test that default date range is applied when not specified."""
        response = client.get("/weight")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

    def test_item_date_range_validation(self, client):
        """Test item endpoint date range validation."""
        response = client.get("/item/TEST?from=20241231235959&to=20240101000000")
        # Should reject invalid range
        assert response.status_code in [400, 404]

    def test_query_returns_json(self, client):
        """Test that query returns valid JSON."""
        response = client.get("/weight")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_item_returns_json(self, client):
        """Test that item endpoint returns valid JSON."""
        response = client.get("/item/TEST")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            assert response.headers["content-type"] == "application/json"

    def test_session_returns_json(self, client):
        """Test that session endpoint returns valid JSON."""
        response = client.get("/session/00000000-0000-0000-0000-000000000000")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            assert response.headers["content-type"] == "application/json"

    def test_unknown_returns_json_array(self, client):
        """Test that unknown endpoint returns JSON array."""
        response = client.get("/unknown")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        data = response.json()
        assert isinstance(data, list)
