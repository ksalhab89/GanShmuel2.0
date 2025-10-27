"""
Test configuration and fixtures for billing service tests.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.main import app
from src.models.database import Provider, Truck, Rate
from src.models.repositories import ProviderRepository, TruckRepository, RateRepository
from src.database import execute_query, initialize_pool


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Initialize database pool for all tests."""
    initialize_pool()
    yield


@pytest.fixture
def db_connection():
    """Provide a database connection for tests."""
    from src.database import get_connection
    connection = get_connection()
    yield connection
    connection.close()


@pytest.fixture(scope="session")
def anyio_backend():
    """Set async backend for pytest-asyncio."""
    return "asyncio"


@pytest_asyncio.fixture
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """Create test client for API testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def clean_database():
    """Clean database before and after tests."""
    # Clean before test
    await execute_query("DELETE FROM Trucks")
    await execute_query("DELETE FROM Rates")
    await execute_query("DELETE FROM Provider")

    yield

    # Clean after test
    await execute_query("DELETE FROM Trucks")
    await execute_query("DELETE FROM Rates")
    await execute_query("DELETE FROM Provider")


@pytest_asyncio.fixture
async def sample_provider(clean_database) -> Provider:
    """Create a sample provider for testing."""
    repo = ProviderRepository()
    provider = await repo.create("Test Provider")
    return provider


@pytest_asyncio.fixture
async def sample_provider_2(clean_database) -> Provider:
    """Create a second sample provider for testing."""
    repo = ProviderRepository()
    provider = await repo.create("Test Provider 2")
    return provider


@pytest_asyncio.fixture
async def sample_truck(sample_provider) -> Truck:
    """Create a sample truck for testing."""
    repo = TruckRepository()
    truck = await repo.create_or_update("ABC123", sample_provider.id)
    return truck


@pytest_asyncio.fixture
async def sample_truck_2(sample_provider) -> Truck:
    """Create a second sample truck for testing."""
    repo = TruckRepository()
    truck = await repo.create_or_update("XYZ789", sample_provider.id)
    return truck


@pytest_asyncio.fixture
async def sample_rate(clean_database) -> Rate:
    """Create a single general rate for testing."""
    repo = RateRepository()
    rate = Rate(product_id="apples", rate=5, scope="ALL")
    await repo.create_batch([rate])
    return rate


@pytest_asyncio.fixture
async def sample_rates(clean_database) -> list[Rate]:
    """Create sample rates for testing."""
    repo = RateRepository()
    rates = [
        Rate(product_id="Apples", rate=150, scope="ALL"),
        Rate(product_id="Oranges", rate=200, scope="ALL"),
        Rate(product_id="Apples", rate=175, scope="1"),  # Provider-specific
    ]
    await repo.create_batch(rates)
    return rates


@pytest_asyncio.fixture
async def sample_provider_rate(sample_provider) -> Rate:
    """Create a provider-specific rate for testing."""
    repo = RateRepository()
    rate = Rate(product_id="apples", rate=6, scope=str(sample_provider.id))
    await repo.create_batch([rate])
    return rate


@pytest_asyncio.fixture
async def multiple_rates(sample_provider) -> list[Rate]:
    """Create multiple provider-specific rates for testing."""
    repo = RateRepository()
    rates = [
        Rate(product_id="apples", rate=6, scope=str(sample_provider.id)),
        Rate(product_id="oranges", rate=5, scope=str(sample_provider.id)),
    ]
    await repo.create_batch(rates)
    return rates


@pytest.fixture
def mock_weight_service():
    """Mock weight service client with configurable test data."""
    class MockWeightService:
        def __init__(self):
            self._transactions = []
            self._item_details = None

        def set_transactions(self, transactions):
            """Set mock transaction data."""
            self._transactions = transactions

        def set_item_details(self, details):
            """Set mock item details data."""
            self._item_details = details

        async def get_transactions(self, from_date=None, to_date=None, direction=None):
            """Get mock transactions."""
            return self._transactions

        async def get_item_details(self, truck_id):
            """Get mock item details."""
            return self._item_details

    return MockWeightService()


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient for weight service testing."""
    class MockHttpxClient:
        def __init__(self):
            self.responses = {}

        def set_response(self, path: str, data: any, status_code: int = 200):
            """Set mock response for a given path."""
            self.responses[path] = (data, status_code)

        async def request(self, method: str, url: str, **kwargs):
            """Mock request method (used by weight_client)."""
            # Find matching response
            for key in self.responses:
                if key in url or url.endswith(key.lstrip('/')):
                    data, status = self.responses[key]
                    response = MagicMock()
                    response.status_code = status
                    response.json = lambda: data  # Synchronous json() for httpx
                    response.raise_for_status = MagicMock()
                    return response

            # Default 404
            response = MagicMock()
            response.status_code = 404
            response.json = lambda: {}
            response.raise_for_status = MagicMock()
            return response

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    return MockHttpxClient()


@pytest.fixture
def sample_weight_transactions():
    """Sample weight transactions for testing."""
    return [
        {
            "id": "trans-001",
            "datetime": "20250126120000",
            "direction": "out",
            "bruto": 50000,
            "truck": "ABC123",
            "truckTara": 10000,
            "neto": 30000,
            "produce": "Apples",
            "containers": [
                {"id": "C001", "tara": 5000},
                {"id": "C002", "tara": 5000}
            ],
            "unit": "kg"
        },
        {
            "id": "trans-002",
            "datetime": "20250126130000",
            "direction": "out",
            "bruto": 40000,
            "truck": "ABC123",
            "truckTara": 10000,
            "neto": 20000,
            "produce": "Oranges",
            "containers": [
                {"id": "C003", "tara": 5000},
                {"id": "C004", "tara": 5000}
            ],
            "unit": "kg"
        }
    ]


@pytest.fixture
def sample_truck_details():
    """Sample truck details from weight service."""
    return {
        "id": "TRUCK001",
        "tara": 10000,
        "sessions": [
            "session-001",
            "session-002"
        ]
    }


@pytest.fixture
def excel_rate_file_path(tmp_path):
    """Create a temporary Excel file with rates for testing."""
    import openpyxl
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Rates"

    # Add headers
    ws.append(["Product", "Rate", "Scope"])

    # Add sample data
    ws.append(["Apples", 150, "ALL"])
    ws.append(["Oranges", 200, "ALL"])
    ws.append(["Apples", 175, "1"])

    file_path = tmp_path / "test_rates.xlsx"
    wb.save(str(file_path))

    return str(file_path)


@pytest.fixture
def mock_upload_file():
    """Create a mock UploadFile for testing."""
    from io import BytesIO
    import openpyxl

    class MockUploadFile:
        def __init__(self, filename: str, content: bytes):
            self.filename = filename
            self.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            self._file = BytesIO(content)

        async def read(self) -> bytes:
            return self._file.read()

        async def seek(self, position: int):
            self._file.seek(position)

        def __enter__(self):
            return self._file

        def __exit__(self, *args):
            pass

    # Create Excel content
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Product", "Rate", "Scope"])
    ws.append(["Apples", 150, "ALL"])
    ws.append(["Oranges", 200, "ALL"])

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    content = buffer.read()

    return MockUploadFile("rates.xlsx", content)
