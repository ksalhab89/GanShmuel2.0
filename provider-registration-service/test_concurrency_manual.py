#!/usr/bin/env python3
"""
Manual Concurrency Test for Optimistic Locking
Tests race condition prevention without pytest
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from jose import jwt

# Configuration
BASE_URL = "http://localhost:5004"
SECRET_KEY = "test-secret-key-for-testing-only"
ALGORITHM = "HS256"


def generate_admin_token():
    """Generate admin JWT token"""
    payload = {
        "sub": "admin@example.com",
        "role": "admin",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def create_candidate():
    """Create a test candidate"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/candidates",
            json={
                "company_name": f"Concurrency Test Ltd {datetime.now().timestamp()}",
                "contact_email": f"concurrent-{datetime.now().timestamp()}@example.com",
                "phone": "123-456-7890",
                "products": ["apples", "oranges"],
                "truck_count": 5,
                "capacity_tons_per_day": 100,
                "location": "Test City"
            }
        )
        response.raise_for_status()
        return response.json()["candidate_id"]


async def approve_candidate(candidate_id, token):
    """Attempt to approve a candidate"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/candidates/{candidate_id}/approve",
                headers={"Authorization": f"Bearer {token}"}
            )
            return response.status_code, response.json() if response.status_code == 200 else response.text
        except Exception as e:
            return None, str(e)


async def test_10_concurrent_approvals():
    """Test 10 concurrent approval attempts"""
    print("\n" + "="*70)
    print("TEST 1: 10 Concurrent Approvals of Same Candidate")
    print("="*70)

    # Create candidate
    print("\n1. Creating test candidate...")
    candidate_id = await create_candidate()
    print(f"   Created candidate: {candidate_id}")

    # Generate admin token
    token = generate_admin_token()

    # Attempt 10 concurrent approvals
    print("\n2. Attempting 10 concurrent approvals...")
    tasks = [approve_candidate(candidate_id, token) for _ in range(10)]
    results = await asyncio.gather(*tasks)

    # Analyze results
    successes = [r for r in results if r[0] == 200]
    conflicts = [r for r in results if r[0] in [400, 409]]
    errors = [r for r in results if r[0] not in [200, 400, 409]]

    print(f"\n3. Results:")
    print(f"   ✓ Successes (200):  {len(successes)}")
    print(f"   ⚠ Conflicts (409/400): {len(conflicts)}")
    print(f"   ✗ Errors:           {len(errors)}")

    # Validation
    print(f"\n4. Validation:")
    if len(successes) == 1:
        print(f"   ✅ PASS: Exactly 1 approval succeeded (optimistic locking working!)")
    else:
        print(f"   ❌ FAIL: Expected 1 success, got {len(successes)}")

    if len(conflicts) == 9:
        print(f"   ✅ PASS: 9 requests properly rejected")
    else:
        print(f"   ⚠  WARN: Expected 9 conflicts, got {len(conflicts)}")

    return len(successes) == 1 and len(conflicts) == 9


async def test_100_concurrent_approvals():
    """Test 100 concurrent approval attempts (stress test)"""
    print("\n" + "="*70)
    print("TEST 2: 100 Concurrent Approvals (Stress Test)")
    print("="*70)

    # Create candidate
    print("\n1. Creating test candidate...")
    candidate_id = await create_candidate()
    print(f"   Created candidate: {candidate_id}")

    # Generate admin token
    token = generate_admin_token()

    # Attempt 100 concurrent approvals
    print("\n2. Attempting 100 concurrent approvals...")
    tasks = [approve_candidate(candidate_id, token) for _ in range(100)]
    results = await asyncio.gather(*tasks)

    # Analyze results
    successes = [r for r in results if r[0] == 200]
    conflicts = [r for r in results if r[0] in [400, 409]]

    print(f"\n3. Results:")
    print(f"   ✓ Successes (200):  {len(successes)}")
    print(f"   ⚠ Conflicts (409/400): {len(conflicts)}")

    # Validation
    print(f"\n4. Validation:")
    if len(successes) == 1:
        print(f"   ✅ PASS: Exactly 1 approval succeeded under high load!")
        print(f"   🎉 Optimistic locking successfully prevented {len(conflicts)} race conditions!")
    else:
        print(f"   ❌ FAIL: Expected 1 success, got {len(successes)}")
        print(f"   ⚠  Race condition detected - multiple approvals succeeded!")

    return len(successes) == 1


async def test_version_increment():
    """Test that version increments on update"""
    print("\n" + "="*70)
    print("TEST 3: Version Increment on Update")
    print("="*70)

    # Create candidate
    print("\n1. Creating test candidate...")
    candidate_id = await create_candidate()
    print(f"   Created candidate: {candidate_id}")

    # Get initial version
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/candidates/{candidate_id}")
        initial_data = response.json()
        initial_version = initial_data["version"]
        print(f"\n2. Initial version: {initial_version}")

    # Approve
    print("\n3. Approving candidate...")
    token = generate_admin_token()
    status, _ = await approve_candidate(candidate_id, token)
    print(f"   Approval status: {status}")

    # Get updated version
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/candidates/{candidate_id}")
        updated_data = response.json()
        updated_version = updated_data["version"]
        print(f"\n4. Updated version: {updated_version}")

    # Validation
    print(f"\n5. Validation:")
    if updated_version == initial_version + 1:
        print(f"   ✅ PASS: Version incremented from {initial_version} to {updated_version}")
    else:
        print(f"   ❌ FAIL: Expected version {initial_version + 1}, got {updated_version}")

    return updated_version == initial_version + 1


async def main():
    """Run all concurrency tests"""
    print("\n" + "="*70)
    print("OPTIMISTIC LOCKING CONCURRENCY TESTS")
    print("Testing Race Condition Prevention with Version Column")
    print("="*70)

    results = []

    # Test 1: 10 concurrent approvals
    results.append(await test_10_concurrent_approvals())

    # Test 2: 100 concurrent approvals (stress test)
    results.append(await test_100_concurrent_approvals())

    # Test 3: Version increment
    results.append(await test_version_increment())

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    passed = sum(results)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Optimistic locking is working correctly!")
        print("   ✅ Race conditions prevented")
        print("   ✅ Version increments properly")
        print("   ✅ Concurrent modifications detected and rejected")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

    print("="*70 + "\n")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
