"""
SQL Injection Prevention Tests
Test common SQL injection attack vectors

SECURITY TEST SUITE - Phase 1, Task 1.2
Tests MUST pass AFTER fixing SQL injection vulnerability in candidate_service.py
"""
import pytest
import time

pytestmark = pytest.mark.asyncio


class TestSQLInjectionPrevention:
    """Verify SQL injection attacks are blocked"""

    async def test_status_filter_injection_attack_drop_table(
        self, test_client, setup_test_database, sample_candidate_data
    ):
        """
        SECURITY TEST: SQL injection via status parameter - DROP TABLE attack
        Attack: "pending'; DROP TABLE candidates; --"
        Expected: Safe handling, no table drop
        """
        # Create a test candidate first
        create_response = await test_client.post("/candidates", json=sample_candidate_data)
        assert create_response.status_code == 201

        # Attempt SQL injection to drop table
        malicious_status = "pending'; DROP TABLE candidates; --"

        response = await test_client.get(f"/candidates?status={malicious_status}")

        # Should safely handle (200 or 422), NOT 500 (SQL error)
        assert response.status_code in [200, 422], (
            f"Unexpected status: {response.status_code}. "
            f"SQL injection may have caused server error!"
        )

        # Verify table still exists by making another request
        verify_response = await test_client.get("/candidates")
        assert verify_response.status_code == 200, "Table may have been dropped by SQL injection!"

        # Verify we can still see our candidate
        data = verify_response.json()
        assert "candidates" in data
        assert len(data["candidates"]) >= 1, "Data lost - possible SQL injection success!"

    async def test_product_filter_injection_attack_or_condition(
        self, test_client, setup_test_database, sample_candidate_data
    ):
        """
        SECURITY TEST: SQL injection via product parameter - OR condition bypass
        Attack: "apples' OR '1'='1"
        Expected: No unauthorized data access
        """
        # Create test candidates with different products
        candidate1 = sample_candidate_data.copy()
        candidate1["contact_email"] = "test1@fruits.com"
        candidate1["products"] = ["apples"]

        candidate2 = sample_candidate_data.copy()
        candidate2["contact_email"] = "test2@fruits.com"
        candidate2["products"] = ["oranges"]

        await test_client.post("/candidates", json=candidate1)
        await test_client.post("/candidates", json=candidate2)

        # Attempt SQL injection to bypass filter
        malicious_product = "apples' OR '1'='1"

        response = await test_client.get(f"/candidates?product={malicious_product}")

        # Should safely handle
        assert response.status_code in [200, 422], (
            f"Unexpected status: {response.status_code}"
        )

        if response.status_code == 200:
            data = response.json()
            # Should NOT return all candidates (OR 1=1 attack)
            # If injection worked, we'd see both candidates
            # If properly protected, we should see 0 candidates (no match) or proper error
            assert "candidates" in data

            # Verify response is properly filtered (should not contain oranges-only candidate)
            # If SQL injection worked, both candidates would be returned
            if len(data["candidates"]) > 0:
                # If any results returned, verify they actually match the intended filter
                # (not the injected OR condition)
                for candidate in data["candidates"]:
                    # Should not see oranges-only candidate due to proper parameterization
                    if candidate["products"] == ["oranges"]:
                        pytest.fail(
                            "SQL injection succeeded! OR condition bypassed filter. "
                            "Found oranges-only candidate when filtering for 'apples'"
                        )

    async def test_union_based_injection_attack(
        self, test_client, setup_test_database, sample_candidate_data
    ):
        """
        SECURITY TEST: UNION-based SQL injection
        Attack: "' UNION SELECT id, 'hacked' FROM candidates --"
        Expected: Safe parameterization prevents attack
        """
        # Create a test candidate
        await test_client.post("/candidates", json=sample_candidate_data)

        # Attempt UNION-based SQL injection
        attack = "pending' UNION SELECT gen_random_uuid(), 'hacked', 'hacked@evil.com', '000', '[]'::jsonb, 1, 1, 'hacked', 'hacked', NOW(), NOW(), 1 --"

        response = await test_client.get(f"/candidates?status={attack}")

        # Should safely handle
        assert response.status_code in [200, 422], (
            f"Unexpected status: {response.status_code}"
        )

        if response.status_code == 200:
            data = response.json()
            # Verify no "hacked" data in response
            response_str = str(data).lower()
            assert "hacked" not in response_str, (
                "SQL injection succeeded! Found 'hacked' in response - UNION attack worked!"
            )

    async def test_comment_injection_attack(
        self, test_client, setup_test_database, sample_candidate_data
    ):
        """
        SECURITY TEST: SQL comment injection
        Attack: "pending' --"
        Expected: Safely handled without executing injected SQL
        """
        # Create a test candidate
        await test_client.post("/candidates", json=sample_candidate_data)

        # Attempt comment-based injection
        attack = "pending' --"

        response = await test_client.get(f"/candidates?status={attack}")

        # Should safely handle
        assert response.status_code in [200, 422], (
            f"Unexpected status: {response.status_code}"
        )

        # Should not crash or return SQL error
        if response.status_code == 200:
            data = response.json()
            assert "candidates" in data

    async def test_time_based_blind_injection(
        self, test_client, setup_test_database, sample_candidate_data
    ):
        """
        SECURITY TEST: Time-based blind SQL injection
        Attack: "pending'; SELECT pg_sleep(10); --"
        Expected: Request completes quickly (not delayed 10 seconds)
        """
        # Create a test candidate
        await test_client.post("/candidates", json=sample_candidate_data)

        # Attempt time-based blind injection
        attack = "pending'; SELECT pg_sleep(10); --"

        start = time.time()
        response = await test_client.get(f"/candidates?status={attack}")
        duration = time.time() - start

        # Should complete in <2 seconds (not delayed by pg_sleep)
        assert duration < 2, (
            f"Request took {duration:.2f}s - possible SQL execution! "
            f"Time-based injection may have succeeded."
        )

        assert response.status_code in [200, 422], (
            f"Unexpected status: {response.status_code}"
        )

    async def test_nested_query_injection(
        self, test_client, setup_test_database, sample_candidate_data
    ):
        """
        SECURITY TEST: Nested query injection attempt
        Attack: "pending' AND (SELECT COUNT(*) FROM candidates) > 0 --"
        Expected: Safe handling without executing nested query
        """
        # Create a test candidate
        await test_client.post("/candidates", json=sample_candidate_data)

        # Attempt nested query injection
        attack = "pending' AND (SELECT COUNT(*) FROM candidates) > 0 --"

        response = await test_client.get(f"/candidates?status={attack}")

        # Should safely handle
        assert response.status_code in [200, 422], (
            f"Unexpected status: {response.status_code}"
        )

    async def test_multiple_statement_injection(
        self, test_client, setup_test_database, sample_candidate_data
    ):
        """
        SECURITY TEST: Multiple statement execution attempt
        Attack: "pending'; UPDATE candidates SET status='approved'; --"
        Expected: Safe handling, no unauthorized updates
        """
        # Create a test candidate
        create_response = await test_client.post("/candidates", json=sample_candidate_data)
        assert create_response.status_code == 201
        candidate_id = create_response.json()["candidate_id"]

        # Attempt multiple statement injection to approve all candidates
        attack = "pending'; UPDATE candidates SET status='approved'; --"

        response = await test_client.get(f"/candidates?status={attack}")

        # Should safely handle
        assert response.status_code in [200, 422], (
            f"Unexpected status: {response.status_code}"
        )

        # Verify candidate status was NOT changed by injection
        verify_response = await test_client.get(f"/candidates/{candidate_id}")
        assert verify_response.status_code == 200
        candidate = verify_response.json()
        assert candidate["status"] == "pending", (
            "SQL injection succeeded! Candidate status was changed to 'approved' "
            "by malicious UPDATE statement!"
        )

    async def test_product_jsonb_injection(
        self, test_client, setup_test_database, sample_candidate_data
    ):
        """
        SECURITY TEST: JSONB operator injection
        Attack: "apples']::jsonb OR '1'='1"
        Expected: Safe handling of JSONB cast and operators
        """
        # Create test candidate
        await test_client.post("/candidates", json=sample_candidate_data)

        # Attempt JSONB-specific injection
        attack = "apples']::jsonb OR '1'='1"

        response = await test_client.get(f"/candidates?product={attack}")

        # Should safely handle
        assert response.status_code in [200, 422], (
            f"Unexpected status: {response.status_code}"
        )

        if response.status_code == 200:
            data = response.json()
            assert "candidates" in data

    async def test_combined_filter_injection(
        self, test_client, setup_test_database, sample_candidate_data
    ):
        """
        SECURITY TEST: Combined status and product filter injection
        Attack: Both parameters contain malicious SQL
        Expected: Safe handling of multiple injected parameters
        """
        # Create test candidate
        await test_client.post("/candidates", json=sample_candidate_data)

        # Attempt injection on both parameters
        malicious_status = "pending' OR '1'='1"
        malicious_product = "'; DROP TABLE candidates; --"

        response = await test_client.get(
            f"/candidates?status={malicious_status}&product={malicious_product}"
        )

        # Should safely handle
        assert response.status_code in [200, 422], (
            f"Unexpected status: {response.status_code}"
        )

        # Verify table still exists
        verify_response = await test_client.get("/candidates")
        assert verify_response.status_code == 200, (
            "Table may have been dropped by combined injection attack!"
        )


class TestSafeQueryBehavior:
    """Verify queries work correctly with legitimate inputs after fix"""

    async def test_legitimate_status_filter(
        self, test_client, setup_test_database, sample_candidate_data
    ):
        """Verify status filtering still works correctly with valid input"""
        # Create pending candidate
        await test_client.post("/candidates", json=sample_candidate_data)

        # Query with legitimate status
        response = await test_client.get("/candidates?status=pending")

        assert response.status_code == 200
        data = response.json()
        assert len(data["candidates"]) == 1
        assert data["candidates"][0]["status"] == "pending"

    async def test_legitimate_product_filter(
        self, test_client, setup_test_database, sample_candidate_data
    ):
        """Verify product filtering still works correctly with valid input"""
        # Create candidate
        await test_client.post("/candidates", json=sample_candidate_data)

        # Query with legitimate product
        response = await test_client.get("/candidates?product=apples")

        assert response.status_code == 200
        data = response.json()
        assert len(data["candidates"]) == 1
        assert "apples" in data["candidates"][0]["products"]

    async def test_legitimate_combined_filters(
        self, test_client, setup_test_database, sample_candidate_data
    ):
        """Verify combined filtering works correctly with valid inputs"""
        # Create candidate
        await test_client.post("/candidates", json=sample_candidate_data)

        # Query with legitimate combined filters
        response = await test_client.get("/candidates?status=pending&product=apples")

        assert response.status_code == 200
        data = response.json()
        assert len(data["candidates"]) == 1
        assert data["candidates"][0]["status"] == "pending"
        assert "apples" in data["candidates"][0]["products"]

    async def test_no_filters_returns_all(
        self, test_client, setup_test_database, sample_candidate_data
    ):
        """Verify querying without filters returns all candidates"""
        # Create multiple candidates
        candidate1 = sample_candidate_data.copy()
        candidate1["contact_email"] = "test1@fruits.com"

        candidate2 = sample_candidate_data.copy()
        candidate2["contact_email"] = "test2@fruits.com"

        await test_client.post("/candidates", json=candidate1)
        await test_client.post("/candidates", json=candidate2)

        # Query without filters
        response = await test_client.get("/candidates")

        assert response.status_code == 200
        data = response.json()
        assert len(data["candidates"]) == 2
