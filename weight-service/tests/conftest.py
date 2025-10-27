"""
Test configuration and fixtures for weight service tests.
"""
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from typing import AsyncGenerator
import asyncio

# Set test database URL before importing app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from src.main import app
from src.database import init_db, close_db, engine


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for session-scoped async fixtures."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_database(event_loop):
    """Initialize database for all tests."""
    event_loop.run_until_complete(init_db())
    yield
    event_loop.run_until_complete(close_db())


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create test client for API testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def clean_database():
    """Clean database before and after each test."""
    from src.models.database import Base

    # Clean before test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Clean after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture(scope="session")
def anyio_backend():
    """Set async backend for pytest-asyncio."""
    return "asyncio"
