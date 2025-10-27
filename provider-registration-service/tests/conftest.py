"""
Provider Registration Service - Test Configuration
Shift-Left: Test infrastructure created BEFORE implementation
"""

import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

# Implemented by Backend-1
from src.main import app
from src.config import settings
import src.database

# Create separate test engine with NullPool to avoid connection pooling issues
test_engine = create_async_engine(
    settings.database_url,
    echo=False,
    poolclass=NullPool,  # No connection pooling for tests - each connection is fresh
)


@pytest.fixture(scope="session", autouse=True)
def override_database_engine():
    """Override the application's database engine with test engine."""
    # Store original engine
    original_engine = src.database.engine
    original_session_local = src.database.AsyncSessionLocal

    # Replace with test engine
    src.database.engine = test_engine
    src.database.AsyncSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    yield

    # Restore original (not really needed as tests end, but for completeness)
    src.database.engine = original_engine
    src.database.AsyncSessionLocal = original_session_local


@pytest_asyncio.fixture
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Test client fixture for API testing.

    Connected to the actual FastAPI app for integration testing.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def setup_test_database():
    """
    Set up test database before each test, tear down after.

    Ensures clean database state for each test.
    NOTE: Tests that need database should explicitly request this fixture.
    """
    # Recreate tables fresh for each test
    async with test_engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS candidates CASCADE"))

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS candidates (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                company_name VARCHAR(255) NOT NULL,
                contact_email VARCHAR(255) NOT NULL UNIQUE,
                phone VARCHAR(50),
                products JSONB,
                truck_count INTEGER CHECK (truck_count > 0),
                capacity_tons_per_day INTEGER CHECK (capacity_tons_per_day > 0),
                location VARCHAR(255),
                status VARCHAR(20) DEFAULT 'pending' NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                provider_id INTEGER,
                version INTEGER DEFAULT 1 NOT NULL,
                rejection_reason TEXT,
                CONSTRAINT status_check CHECK (status IN ('pending', 'approved', 'rejected'))
            )
        """))

        # Create trigger for version increment
        await conn.execute(text("""
            CREATE OR REPLACE FUNCTION update_candidates_metadata()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                NEW.version = OLD.version + 1;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """))

        await conn.execute(text("DROP TRIGGER IF EXISTS update_candidates_metadata ON candidates"))

        await conn.execute(text("""
            CREATE TRIGGER update_candidates_metadata BEFORE UPDATE ON candidates
            FOR EACH ROW EXECUTE FUNCTION update_candidates_metadata()
        """))

    yield

    # Clean up: truncate data for next test
    # Ignore errors as they can occur after high-concurrency tests
    try:
        async with test_engine.begin() as conn:
            await conn.execute(text("TRUNCATE TABLE candidates CASCADE"))
    except Exception:
        pass  # Ignore cleanup errors - next test will drop/recreate anyway


@pytest.fixture
def sample_candidate_data():
    """Sample valid candidate data for testing."""
    return {
        "company_name": "Test Fruits Ltd",
        "contact_email": "test@fruits.com",
        "phone": "123-456-7890",
        "products": ["apples", "oranges"],
        "truck_count": 5,
        "capacity_tons_per_day": 100,
        "location": "Test City"
    }


@pytest.fixture
def invalid_candidate_data():
    """Sample invalid candidate data for validation testing."""
    return {
        "company_name": "",  # Empty name - should fail
        "contact_email": "not-an-email",  # Invalid email
        "products": ["invalid_product"],  # Invalid product
        "truck_count": -1,  # Negative count - should fail
        "capacity_tons_per_day": 0,  # Zero capacity - should fail
    }


@pytest.fixture(autouse=True)
def mock_billing_service(request, monkeypatch):
    """Mock billing service for all tests to prevent external calls.

    Can be disabled by using @pytest.mark.no_billing_mock or in test files
    that test the billing client itself
    """
    # Check if test module or test is marked to skip billing mock
    if request.node.get_closest_marker("no_billing_mock"):
        yield
        return

    from unittest.mock import AsyncMock
    from src.services.billing_client import BillingClient

    # Mock the create_provider method to return a fake provider ID
    async def mock_create_provider(self, company_name: str) -> int:
        # Return a fake provider ID based on company name hash for consistency
        return abs(hash(company_name)) % 1000000

    monkeypatch.setattr(BillingClient, "create_provider", mock_create_provider)
    yield


# Authentication fixtures for JWT testing
SECRET_KEY = "test-secret-key-for-testing-only"
ALGORITHM = "HS256"


@pytest.fixture
def admin_token():
    """Generate admin JWT token for testing"""
    from datetime import datetime, timedelta
    from jose import jwt

    payload = {
        "sub": "admin@example.com",
        "role": "admin",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@pytest.fixture
def user_token():
    """Generate regular user JWT token for testing"""
    from datetime import datetime, timedelta
    from jose import jwt

    payload = {
        "sub": "user@example.com",
        "role": "user",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# Note: httpx_mock fixture is automatically provided by pytest-httpx plugin
# No need to define it here - it's available in all tests
