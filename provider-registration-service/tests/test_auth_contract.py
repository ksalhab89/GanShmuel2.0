"""
Authentication Contract Tests - Written BEFORE Implementation
These tests define the EXACT behavior the security system must have
"""
import pytest
from datetime import datetime, timedelta
from jose import jwt

pytestmark = pytest.mark.asyncio


class TestAuthenticationContract:
    """JWT Authentication Contract - Define behavior before implementation"""

    async def test_login_success_returns_jwt(self, test_client):
        """SECURITY: Valid credentials must return JWT token with required claims"""
        response = await test_client.post("/auth/login", data={
            "username": "admin@example.com",
            "password": "admin123"  # Test password
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    async def test_login_invalid_credentials(self, test_client):
        """SECURITY: Invalid credentials must return 401"""
        response = await test_client.post("/auth/login", data={
            "username": "admin@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401

    async def test_login_invalid_username(self, test_client):
        """SECURITY: Invalid username must return 401"""
        response = await test_client.post("/auth/login", data={
            "username": "nonexistent@example.com",
            "password": "admin123"
        })
        assert response.status_code == 401

    async def test_protected_endpoint_requires_token(self, test_client, sample_candidate_data, setup_test_database):
        """SECURITY: Approval endpoint must reject requests without token"""
        # Create candidate first
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        assert create_resp.status_code == 201
        candidate_id = create_resp.json()["candidate_id"]

        # Try to approve without token
        response = await test_client.post(f"/candidates/{candidate_id}/approve")
        assert response.status_code == 401

    async def test_admin_can_approve(self, test_client, admin_token, sample_candidate_data, setup_test_database):
        """SECURITY: Admin role can approve candidates"""
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        assert create_resp.status_code == 201
        candidate_id = create_resp.json()["candidate_id"]

        # Approve with admin token
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await test_client.post(f"/candidates/{candidate_id}/approve", headers=headers)
        assert response.status_code == 200

        # Verify response structure
        data = response.json()
        assert data["status"] == "approved"
        assert "provider_id" in data

    async def test_non_admin_cannot_approve(self, test_client, user_token, sample_candidate_data, setup_test_database):
        """SECURITY: Regular user cannot approve candidates"""
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        assert create_resp.status_code == 201
        candidate_id = create_resp.json()["candidate_id"]

        # Try to approve with user token
        headers = {"Authorization": f"Bearer {user_token}"}
        response = await test_client.post(f"/candidates/{candidate_id}/approve", headers=headers)
        assert response.status_code == 403

    async def test_jwt_token_contains_required_claims(self, test_client):
        """SECURITY: JWT token must contain sub, role, and exp claims"""
        response = await test_client.post("/auth/login", data={
            "username": "admin@example.com",
            "password": "admin123"
        })

        assert response.status_code == 200
        token = response.json()["access_token"]

        # Decode token without verification to check claims
        SECRET_KEY = "test-secret-key-for-testing-only"
        ALGORITHM = "HS256"
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert "sub" in payload
        assert "role" in payload
        assert "exp" in payload
        assert payload["sub"] == "admin@example.com"
        assert payload["role"] == "admin"

    async def test_malformed_token_rejected(self, test_client, sample_candidate_data, setup_test_database):
        """SECURITY: Malformed tokens must be rejected"""
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        assert create_resp.status_code == 201
        candidate_id = create_resp.json()["candidate_id"]

        # Try with malformed token
        headers = {"Authorization": "Bearer not-a-valid-jwt-token"}
        response = await test_client.post(f"/candidates/{candidate_id}/approve", headers=headers)
        assert response.status_code == 401

    async def test_missing_authorization_header_rejected(self, test_client, sample_candidate_data, setup_test_database):
        """SECURITY: Missing authorization header must be rejected"""
        # Create candidate
        create_resp = await test_client.post("/candidates", json=sample_candidate_data)
        assert create_resp.status_code == 201
        candidate_id = create_resp.json()["candidate_id"]

        # Try without authorization header
        response = await test_client.post(f"/candidates/{candidate_id}/approve")
        assert response.status_code == 401
