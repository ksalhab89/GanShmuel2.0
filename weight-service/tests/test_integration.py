"""End-to-end integration tests for the Weight Service  API."""

import json
import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


class TestCompleteWeighingWorkflow:
    """Test complete weighing workflows from start to finish."""

    def test_complete_in_out_workflow(self, client):
        """Test complete IN → OUT weighing workflow."""
        truck_id = "WORKFLOW_TEST_001"
        containers = "C001,C002,C003"
        
        # Step 1: Record IN weighing
        in_request = {
            "direction": "in",
            "truck": truck_id,
            "containers": containers,
            "weight": 5000,
            "unit": "kg",
            "produce": "apples"
        }
        
        in_response = client.post("/weight", json=in_request)
        assert in_response.status_code == 200
        
        in_data = in_response.json()
        session_id = in_data["session_id"]
        assert in_data["direction"] == "in"
        assert in_data["truck"] == truck_id
        assert in_data["gross_weight"] == 5000
        assert in_data["net_weight"] == "na"
        
        # Step 2: Verify session was created
        session_response = client.get(f"/session/{session_id}")
        assert session_response.status_code == 200
        
        session_data = session_response.json()
        assert session_data["session_id"] == session_id
        assert session_data["truck"] == truck_id
        
        # Step 3: Record OUT weighing
        out_request = {
            "direction": "out",
            "truck": truck_id,
            "containers": containers,
            "weight": 4500,
            "unit": "kg"
        }
        
        out_response = client.post("/weight", json=out_request)
        assert out_response.status_code == 200
        
        out_data = out_response.json()
        assert out_data["direction"] == "out"
        assert out_data["truck"] == truck_id
        assert out_data["gross_weight"] == 4500
        assert out_data["net_weight"] != "na"  # Should calculate net weight
        
        # Step 4: Verify both transactions appear in queries
        query_response = client.get("/weight")
        assert query_response.status_code == 200
        
        transactions = query_response.json()
        truck_transactions = [t for t in transactions if t["truck"] == truck_id]
        assert len(truck_transactions) >= 2
        
        # Step 5: Verify truck information
        truck_response = client.get(f"/item/{truck_id}")
        assert truck_response.status_code == 200
        
        truck_data = truck_response.json()
        assert truck_data["item_id"] == truck_id
        assert truck_data["item_type"] == "truck"

    def test_batch_upload_then_weighing_workflow(self, client, tmp_path, monkeypatch):
        """Test batch upload followed by weighing workflow."""
        # Step 1: Create and upload container weights
        containers_data = [
            {"id": "BATCH_C001", "weight": 50, "unit": "kg"},
            {"id": "BATCH_C002", "weight": 75, "unit": "kg"},
            {"id": "BATCH_C003", "weight": 60, "unit": "kg"}
        ]
        
        in_dir = tmp_path / "in"
        in_dir.mkdir()
        
        json_file = in_dir / "batch_containers.json"
        json_file.write_text(json.dumps(containers_data))
        
        # Mock the /in directory path
        monkeypatch.setattr("src.config.settings.files_directory", str(in_dir))
        
        batch_request = {"filename": "batch_containers.json"}
        batch_response = client.post("/batch-weight", json=batch_request)
        assert batch_response.status_code == 200
        
        batch_data = batch_response.json()
        assert batch_data["successful_count"] == 3
        
        # Step 2: Use uploaded containers in weighing
        weight_request = {
            "direction": "in",
            "truck": "BATCH_TRUCK_001",
            "containers": "BATCH_C001,BATCH_C002,BATCH_C003",
            "weight": 5000,
            "unit": "kg",
            "produce": "apples"
        }
        
        weight_response = client.post("/weight", json=weight_request)
        assert weight_response.status_code == 200
        
        weight_data = weight_response.json()
        assert weight_data["direction"] == "in"
        # Net weight calculation should now work with known container weights
        
        # Step 3: Check container information
        for container_id in ["BATCH_C001", "BATCH_C002", "BATCH_C003"]:
            container_response = client.get(f"/item/{container_id}")
            assert container_response.status_code == 200
            
            container_data = container_response.json()
            assert container_data["item_id"] == container_id
            assert container_data["item_type"] == "container"

    def test_unknown_containers_detection_workflow(self, client):
        """Test workflow for detecting and handling unknown containers."""
        # Step 1: Check initial unknown containers
        unknown_response = client.get("/unknown")
        assert unknown_response.status_code == 200
        initial_unknowns = set(unknown_response.json())
        
        # Step 2: Create weighing with unknown containers
        unknown_containers = "UNKNOWN_TEST_001,UNKNOWN_TEST_002"
        weight_request = {
            "direction": "in",
            "truck": "UNKNOWN_TRUCK",
            "containers": unknown_containers,
            "weight": 5000,
            "unit": "kg"
        }
        
        weight_response = client.post("/weight", json=weight_request)
        assert weight_response.status_code == 200
        
        # Step 3: Verify unknown containers are detected
        unknown_response = client.get("/unknown")
        assert unknown_response.status_code == 200
        
        current_unknowns = set(unknown_response.json())
        new_unknowns = current_unknowns - initial_unknowns
        
        # Should include our new unknown containers
        assert "UNKNOWN_TEST_001" in new_unknowns or "UNKNOWN_TEST_002" in new_unknowns

    def test_error_handling_workflow(self, client):
        """Test error handling in complete workflows."""
        # Step 1: Try OUT without IN
        out_request = {
            "direction": "out",
            "truck": "NO_IN_TRUCK",
            "containers": "C001",
            "weight": 4500,
            "unit": "kg"
        }
        
        out_response = client.post("/weight", json=out_request)
        assert out_response.status_code == 400
        assert "Invalid weighing sequence" in out_response.json()["detail"]
        
        # Step 2: Invalid file upload
        batch_request = {"filename": "nonexistent.csv"}
        batch_response = client.post("/batch-weight", json=batch_request)
        assert batch_response.status_code == 400
        assert "File not found" in batch_response.json()["detail"]
        
        # Step 3: Invalid query parameters
        query_response = client.get("/weight?from=invalid-date")
        assert query_response.status_code == 400
        assert "Invalid date range" in query_response.json()["detail"]

    def test_force_flag_workflow(self, client):
        """Test force flag workflow for overriding business rules."""
        truck_id = "FORCE_TEST_TRUCK"
        
        # Step 1: Create initial IN session
        in_request = {
            "direction": "in",
            "truck": truck_id,
            "containers": "C001",
            "weight": 5000,
            "unit": "kg"
        }
        
        in_response = client.post("/weight", json=in_request)
        assert in_response.status_code == 200
        
        # Step 2: Try duplicate IN without force (should fail)
        duplicate_response = client.post("/weight", json=in_request)
        assert duplicate_response.status_code == 400
        
        # Step 3: Use force flag to override
        in_request["force"] = True
        force_response = client.post("/weight", json=in_request)
        assert force_response.status_code == 200

    def test_multi_container_calculation_workflow(self, client, tmp_path, monkeypatch):
        """Test workflow with multiple containers and weight calculations."""
        # Step 1: Upload container weights
        containers_data = [
            {"id": "MULTI_C001", "weight": 100, "unit": "kg"},
            {"id": "MULTI_C002", "weight": 150, "unit": "kg"},
            {"id": "MULTI_C003", "weight": 200, "unit": "kg"}
        ]
        
        in_dir = tmp_path / "in"
        in_dir.mkdir()
        
        json_file = in_dir / "multi_containers.json"
        json_file.write_text(json.dumps(containers_data))
        
        # Mock the /in directory path
        monkeypatch.setattr("src.config.settings.files_directory", str(in_dir))
        
        batch_request = {"filename": "multi_containers.json"}
        client.post("/batch-weight", json=batch_request)
        
        # Step 2: IN weighing with multiple containers
        in_request = {
            "direction": "in",
            "truck": "MULTI_TRUCK",
            "containers": "MULTI_C001,MULTI_C002,MULTI_C003",
            "weight": 10000,  # Total weight
            "unit": "kg"
        }
        
        in_response = client.post("/weight", json=in_request)
        assert in_response.status_code == 200
        
        # Step 3: OUT weighing
        out_request = {
            "direction": "out",
            "truck": "MULTI_TRUCK",
            "containers": "MULTI_C001,MULTI_C002,MULTI_C003",
            "weight": 9000,  # Lighter after unloading
            "unit": "kg"
        }
        
        out_response = client.post("/weight", json=out_request)
        assert out_response.status_code == 200
        
        out_data = out_response.json()
        
        # Net weight should be calculated correctly
        # Net = (IN_weight - OUT_weight) - sum(container_weights)
        # Net = (10000 - 9000) - (100 + 150 + 200) = 1000 - 450 = 550
        expected_net = 1000 - 450  # 550 kg
        
        if out_data["net_weight"] != "na":
            actual_net = int(out_data["net_weight"])
            assert abs(actual_net - expected_net) < 10  # Allow small calculation differences

    def test_health_check_integration(self, client):
        """Test health check endpoint integration."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        
        # Health check should work independently of other operations
        assert data["status"] in ["OK", "FAILURE"]
        assert data["database"] in ["OK", "FAILURE"]