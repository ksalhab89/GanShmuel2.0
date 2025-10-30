"""Real end-to-end tests that make actual HTTP API calls to the running Weight Service V2."""

import json
import time
import requests
from typing import Dict, Any, List
import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed


# Configuration for the running service
# Use API Gateway URL (port 80) - backend ports are not exposed externally
BASE_URL = "http://localhost/api/weight"
TIMEOUT = 10  # seconds


@pytest.fixture(scope="session")
def api_client():
    """Test that the API is running before starting tests."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        if response.status_code != 200:
            pytest.skip(f"Weight Service not healthy. Status: {response.status_code}")

        health_data = response.json()
        if health_data.get("status") != "healthy":
            pytest.skip(f"Weight Service not healthy. Health: {health_data}")

        print(f"\n✅ Connected to Weight Service at {BASE_URL}")
        return BASE_URL
    except requests.exceptions.RequestException as e:
        pytest.skip(f"Cannot connect to Weight Service at {BASE_URL}: {e}")


class TestRealAPIHealth:
    """Test real API health and connectivity."""

    def test_health_endpoint_responds(self, api_client):
        """Test that health endpoint responds with healthy status."""
        print(f"\n🔍 Testing health endpoint at {api_client}/health")

        response = requests.get(f"{api_client}/health", timeout=TIMEOUT)

        print(f"📡 HTTP {response.status_code}: {response.text}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "weight-service"
        assert "version" in data

    def test_api_documentation_accessible(self, api_client):
        """Test that API documentation is accessible."""
        print(f"\n🔍 Testing API docs at {api_client}/docs")

        response = requests.get(f"{api_client}/docs", timeout=TIMEOUT)

        print(f"📡 HTTP {response.status_code}: Content length {len(response.text)}")

        assert response.status_code == 200
        assert "Weight Service" in response.text
        assert "swagger-ui" in response.text

    def test_openapi_spec_available(self, api_client):
        """Test that OpenAPI specification is available."""
        print(f"\n🔍 Testing OpenAPI spec at {api_client}/openapi.json")

        response = requests.get(f"{api_client}/openapi.json", timeout=TIMEOUT)

        print(f"📡 HTTP {response.status_code}: OpenAPI spec received")

        assert response.status_code == 200
        spec = response.json()
        assert spec["info"]["title"] == "Weight Service"
        assert "/weight" in spec["paths"]
        assert "/health" in spec["paths"]


class TestRealAPIWeightRecording:
    """Test real API weight recording operations."""

    def test_successful_in_transaction(self, api_client):
        """Test successful IN direction weighing with real API call."""
        print(f"\n🔍 Testing IN transaction via real API call")
        
        request_data = {
            "direction": "in",
            "truck": "REAL001",
            "containers": "REAL_C001,REAL_C002",
            "weight": 8000,
            "unit": "kg",
            "produce": "api_test_apples"
        }
        
        print(f"📤 POST {api_client}/weight")
        print(f"📦 Request: {json.dumps(request_data, indent=2)}")
        
        response = requests.post(
            f"{api_client}/weight",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT
        )
        
        print(f"📡 HTTP {response.status_code}: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["truck"] == "REAL001"
        assert data["bruto"] == 8000
        assert "id" in data  # Session ID
        
        # Store session ID for other tests
        TestRealAPIWeightRecording.test_session_id = data["id"]

    def test_input_validation_negative_weight(self, api_client):
        """Test that negative weights are rejected via real API."""
        print(f"\n🔍 Testing input validation (negative weight)")
        
        request_data = {
            "direction": "in",
            "truck": "REAL002",
            "containers": "REAL_C003",
            "weight": -1000,  # Invalid negative weight
            "unit": "kg"
        }
        
        print(f"📤 POST {api_client}/weight (expecting validation error)")
        print(f"📦 Request: {json.dumps(request_data, indent=2)}")
        
        response = requests.post(
            f"{api_client}/weight",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT
        )
        
        print(f"📡 HTTP {response.status_code}: {response.text}")
        
        assert response.status_code == 422  # Validation error
        error_data = response.json()
        assert "detail" in error_data

    def test_business_logic_out_without_in(self, api_client):
        """Test business logic: OUT without IN should be rejected."""
        print(f"\n🔍 Testing business logic (OUT without IN)")
        
        request_data = {
            "direction": "out",
            "truck": "NONEXISTENT_TRUCK",
            "containers": "REAL_C004",
            "weight": 7000,
            "unit": "kg"
        }
        
        print(f"📤 POST {api_client}/weight (expecting business logic error)")
        print(f"📦 Request: {json.dumps(request_data, indent=2)}")
        
        response = requests.post(
            f"{api_client}/weight",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT
        )
        
        print(f"📡 HTTP {response.status_code}: {response.text}")
        
        assert response.status_code == 400
        error_data = response.json()
        assert "Invalid weighing sequence" in error_data["detail"]

    def test_unit_conversion_lbs_to_kg(self, api_client):
        """Test unit conversion from pounds to kilograms."""
        print(f"\n🔍 Testing unit conversion (lbs to kg)")
        
        request_data = {
            "direction": "in",
            "truck": "REAL003",
            "containers": "REAL_C005",
            "weight": 2204,  # Approximately 1000 kg
            "unit": "lbs"
        }
        
        print(f"📤 POST {api_client}/weight (lbs conversion)")
        print(f"📦 Request: {json.dumps(request_data, indent=2)}")
        
        response = requests.post(
            f"{api_client}/weight",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT
        )
        
        print(f"📡 HTTP {response.status_code}: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be converted to approximately 1000 kg
        converted_weight = data["bruto"]
        print(f"🔄 Converted weight: {converted_weight} kg (from 2204 lbs)")
        assert abs(converted_weight - 1000) < 10  # Allow for conversion rounding


class TestRealAPIQueries:
    """Test real API query operations."""

    def test_query_all_transactions(self, api_client):
        """Test querying all transactions via real API."""
        print(f"\n🔍 Testing transaction query via real API")
        
        print(f"📤 GET {api_client}/weight")
        
        response = requests.get(f"{api_client}/weight", timeout=TIMEOUT)
        
        print(f"📡 HTTP {response.status_code}: Received {len(response.json())} transactions")
        
        assert response.status_code == 200
        transactions = response.json()
        assert isinstance(transactions, list)
        
        # Should have our test transactions
        real_transactions = [t for t in transactions if "REAL" in str(t.get("truck", ""))]
        print(f"📊 Found {len(real_transactions)} transactions from our API tests")
        assert len(real_transactions) >= 2  # From our previous tests

    def test_query_with_direction_filter(self, api_client):
        """Test querying with direction filter."""
        print(f"\n🔍 Testing query with direction filter")
        
        print(f"📤 GET {api_client}/weight?filter=in")
        
        response = requests.get(f"{api_client}/weight?filter=in", timeout=TIMEOUT)
        
        print(f"📡 HTTP {response.status_code}: Received transactions")
        
        assert response.status_code == 200
        transactions = response.json()
        
        # All returned transactions should be 'in' direction
        for transaction in transactions:
            assert transaction["direction"] == "in"
        
        print(f"📊 All {len(transactions)} transactions have direction 'in'")

    def test_unknown_containers_detection(self, api_client):
        """Test unknown containers detection via real API."""
        print(f"\n🔍 Testing unknown containers detection")
        
        print(f"📤 GET {api_client}/unknown")
        
        response = requests.get(f"{api_client}/unknown", timeout=TIMEOUT)
        
        print(f"📡 HTTP {response.status_code}: {response.text}")
        
        assert response.status_code == 200
        unknowns = response.json()
        assert isinstance(unknowns, list)
        
        # Should include containers from our test transactions  
        real_containers = [c for c in unknowns if "REAL_C" in c]
        print(f"📊 Found {len(real_containers)} unknown containers from our tests")
        assert len(real_containers) >= 3  # From our test transactions

    def test_item_lookup_truck(self, api_client):
        """Test looking up truck information via real API."""
        print(f"\n🔍 Testing truck item lookup")
        
        truck_id = "REAL001"  # From our first test
        print(f"📤 GET {api_client}/item/{truck_id}")
        
        response = requests.get(f"{api_client}/item/{truck_id}", timeout=TIMEOUT)
        
        print(f"📡 HTTP {response.status_code}: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == truck_id
        assert isinstance(data["sessions"], list)
        assert len(data["sessions"]) >= 1  # Should have our test session
        
        print(f"📊 Truck {truck_id} has {len(data['sessions'])} sessions")

    def test_nonexistent_item_returns_404(self, api_client):
        """Test that non-existent items return 404."""
        print(f"\n🔍 Testing non-existent item lookup")
        
        fake_id = "NONEXISTENT_ITEM_12345"
        print(f"📤 GET {api_client}/item/{fake_id} (expecting 404)")
        
        response = requests.get(f"{api_client}/item/{fake_id}", timeout=TIMEOUT)
        
        print(f"📡 HTTP {response.status_code}: {response.text}")
        
        assert response.status_code == 404
        error_data = response.json()
        assert "not found" in error_data["detail"]


class TestRealAPIPerformance:
    """Test real API performance characteristics."""

    def test_response_time_health_check(self, api_client):
        """Test health check response time."""
        print(f"\n🔍 Testing health check response time")
        
        start_time = time.time()
        response = requests.get(f"{api_client}/health", timeout=TIMEOUT)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        print(f"📡 HTTP {response.status_code} in {response_time:.3f}s")
        
        assert response.status_code == 200
        assert response_time < 1.0  # Should respond within 1 second
        
        print(f"⚡ Health check responded in {response_time:.3f}s (< 1.0s)")

    def test_response_time_weight_recording(self, api_client):
        """Test weight recording response time."""
        print(f"\n🔍 Testing weight recording response time")
        
        request_data = {
            "direction": "in",
            "truck": "PERF001",
            "containers": "PERF_C001,PERF_C002",
            "weight": 9000,
            "unit": "kg",
            "produce": "performance_test"
        }
        
        start_time = time.time()
        response = requests.post(
            f"{api_client}/weight",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT
        )
        end_time = time.time()
        
        response_time = end_time - start_time
        
        print(f"📡 HTTP {response.status_code} in {response_time:.3f}s")
        
        assert response.status_code == 200
        assert response_time < 2.0  # Should respond within 2 seconds
        
        print(f"⚡ Weight recording responded in {response_time:.3f}s (< 2.0s)")

    def test_concurrent_requests(self, api_client):
        """Test concurrent API requests."""
        print(f"\n🔍 Testing concurrent API requests (5 simultaneous)")
        
        def make_request(index: int) -> Dict[str, Any]:
            request_data = {
                "direction": "in",
                "truck": f"CONC{index:03d}",
                "containers": f"CONC_C{index:03d}",
                "weight": 5000 + index * 100,
                "unit": "kg",
                "produce": f"concurrent_test_{index}"
            }
            
            start_time = time.time()
            response = requests.post(
                f"{api_client}/weight",
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=TIMEOUT
            )
            end_time = time.time()
            
            return {
                "index": index,
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "response": response.json() if response.status_code == 200 else None
            }
        
        # Execute 5 concurrent requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(5)]
            results = [future.result() for future in as_completed(futures)]
        
        # Verify all succeeded
        successful_results = [r for r in results if r["status_code"] == 200]
        response_times = [r["response_time"] for r in successful_results]
        
        print(f"📊 {len(successful_results)}/5 requests succeeded")
        print(f"⚡ Response times: {[f'{t:.3f}s' for t in response_times]}")
        
        assert len(successful_results) == 5
        assert all(rt < 3.0 for rt in response_times)  # All should be fast
        
        # Verify unique session IDs
        session_ids = [r["response"]["id"] for r in successful_results]
        assert len(set(session_ids)) == 5  # All should be unique


class TestRealAPICompleteWorkflow:
    """Test complete end-to-end workflow via real API calls."""

    def test_complete_weighing_workflow(self, api_client):
        """Test complete IN → OUT workflow with real API calls."""
        print(f"\n🔍 Testing complete weighing workflow (IN → OUT)")
        
        truck_id = "WORKFLOW001"
        containers = "WF_C001,WF_C002"
        
        # Step 1: Create IN transaction
        print(f"📤 Step 1: Creating IN transaction")
        in_request = {
            "direction": "in",
            "truck": truck_id,
            "containers": containers,
            "weight": 10000,
            "unit": "kg",
            "produce": "workflow_apples"
        }
        
        in_response = requests.post(
            f"{api_client}/weight",
            json=in_request,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT
        )
        
        print(f"📡 IN transaction: HTTP {in_response.status_code}")
        assert in_response.status_code == 200
        
        in_data = in_response.json()
        session_id = in_data["id"]
        print(f"✅ Created session: {session_id}")
        
        # Step 2: Verify transaction appears in queries
        print(f"📤 Step 2: Querying transactions")
        query_response = requests.get(f"{api_client}/weight", timeout=TIMEOUT)
        
        assert query_response.status_code == 200
        transactions = query_response.json()
        
        our_transaction = next((t for t in transactions if t["id"] == session_id), None)
        assert our_transaction is not None
        print(f"✅ Transaction found in query results")
        
        # Step 3: Check truck information  
        print(f"📤 Step 3: Looking up truck info")
        truck_response = requests.get(f"{api_client}/item/{truck_id}", timeout=TIMEOUT)
        
        assert truck_response.status_code == 200
        truck_data = truck_response.json()
        assert session_id in truck_data["sessions"]
        print(f"✅ Truck {truck_id} shows session {session_id}")
        
        # Step 4: Check unknown containers
        print(f"📤 Step 4: Checking unknown containers")
        unknown_response = requests.get(f"{api_client}/unknown", timeout=TIMEOUT)
        
        assert unknown_response.status_code == 200
        unknowns = unknown_response.json()
        assert "WF_C001" in unknowns
        assert "WF_C002" in unknowns
        print(f"✅ Containers properly marked as unknown")
        
        # Step 5: Try OUT transaction (should fail due to unknown containers)
        print(f"📤 Step 5: Attempting OUT transaction (expecting failure)")
        out_request = {
            "direction": "out", 
            "truck": truck_id,
            "containers": containers,
            "weight": 9000,
            "unit": "kg"
        }
        
        out_response = requests.post(
            f"{api_client}/weight",
            json=out_request,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT
        )
        
        print(f"📡 OUT transaction: HTTP {out_response.status_code}")
        assert out_response.status_code == 400  # Should fail due to unknown containers
        
        error_data = out_response.json()
        assert "Unknown container weights" in error_data["detail"]
        print(f"✅ OUT correctly rejected due to unknown container weights")
        
        print(f"🎉 Complete workflow test successful!")

    def test_system_remains_healthy_after_operations(self, api_client):
        """Test that system remains healthy after all operations."""
        print(f"\n🔍 Final health check after all operations")

        response = requests.get(f"{api_client}/health", timeout=TIMEOUT)

        print(f"📡 HTTP {response.status_code}: {response.text}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "healthy"

        print(f"✅ System remains healthy after all E2E tests")


class TestRealAPIBatchOperations:
    """Test batch operations (limited without file system access)."""

    def test_batch_upload_file_not_found(self, api_client):
        """Test batch upload with non-existent file."""
        print(f"\n🔍 Testing batch upload (file not found)")

        request_data = {"file": "nonexistent_test_file.json"}

        print(f"📤 POST {api_client}/batch-weight (expecting file not found)")
        print(f"📦 Request: {json.dumps(request_data, indent=2)}")

        response = requests.post(
            f"{api_client}/batch-weight",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT
        )

        print(f"📡 HTTP {response.status_code}: {response.text}")

        assert response.status_code == 500
        error_data = response.json()
        assert "Internal server error" in error_data["detail"]

        print(f"✅ Batch upload correctly rejects non-existent file")


if __name__ == "__main__":
    print("🚀 Running Real E2E API Tests")
    print(f"🎯 Target: {BASE_URL}")
    print("="*50)
    
    # Run a quick connectivity test
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Weight Service  is running and healthy")
            print("🧪 Ready to run tests with: pytest test_real_e2e_api_calls.py -v -s")
        else:
            print(f"❌ Weight Service  not healthy: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to Weight Service V2: {e}")
        print("💡 Make sure Docker containers are running: docker-compose up")