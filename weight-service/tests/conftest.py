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
    async def _setup():
        await init_db()
        # Seed common test containers
        await _seed_containers()

    async def _seed_containers():
        """Seed test containers with weights."""
        from src.models.database import ContainerRegistered
        from src.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            # Common test containers with weights
            test_containers = [
                ContainerRegistered(container_id="C001", weight=50, unit="kg"),
                ContainerRegistered(container_id="C002", weight=60, unit="kg"),
                ContainerRegistered(container_id="C003", weight=55, unit="kg"),
                ContainerRegistered(container_id="C100", weight=45, unit="kg"),
                ContainerRegistered(container_id="C101", weight=48, unit="kg"),
                ContainerRegistered(container_id="C200", weight=52, unit="kg"),
                ContainerRegistered(container_id="C201", weight=53, unit="kg"),
                ContainerRegistered(container_id="C300", weight=50, unit="kg"),
                ContainerRegistered(container_id="C301", weight=50, unit="kg"),
                ContainerRegistered(container_id="C302", weight=50, unit="kg"),
                ContainerRegistered(container_id="C400", weight=55, unit="kg"),
                ContainerRegistered(container_id="C401", weight=55, unit="kg"),
                ContainerRegistered(container_id="C500", weight=60, unit="kg"),
                ContainerRegistered(container_id="C501", weight=60, unit="kg"),
                ContainerRegistered(container_id="C600", weight=50, unit="kg"),
                ContainerRegistered(container_id="C601", weight=50, unit="kg"),
                ContainerRegistered(container_id="C700", weight=45, unit="kg"),
                ContainerRegistered(container_id="C800", weight=48, unit="kg"),
                ContainerRegistered(container_id="C900", weight=52, unit="kg"),
            ]

            session.add_all(test_containers)
            await session.commit()

    event_loop.run_until_complete(_setup())
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
