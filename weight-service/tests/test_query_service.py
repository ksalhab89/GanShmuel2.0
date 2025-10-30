"""Comprehensive tests for QueryService - targeting 90%+ coverage."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.query_service import QueryService
from src.models.schemas import (
    WeightQueryParams,
    ItemQueryParams,
    TransactionResponse,
    ItemResponse,
    ContainerWeightInfo,
)
from src.models.database import Transaction
from src.utils.exceptions import InvalidDateRangeError


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def query_service(mock_session):
    """Create QueryService instance with mocked dependencies."""
    return QueryService(mock_session)


@pytest.fixture
def mock_transaction():
    """Create mock transaction."""
    transaction = MagicMock(spec=Transaction)
    transaction.session_id = "session-123"
    transaction.direction = "in"
    transaction.truck = "ABC123"
    transaction.bruto = 5000
    transaction.neto = 4500
    transaction.truck_tara = 500
    transaction.produce = "apples"
    transaction.container_list = ["C001", "C002"]
    transaction.get_display_produce.return_value = "apples"
    return transaction


@pytest.fixture
def mock_transaction_out():
    """Create mock OUT transaction."""
    transaction = MagicMock(spec=Transaction)
    transaction.session_id = "session-123"
    transaction.direction = "out"
    transaction.truck = "ABC123"
    transaction.bruto = 500
    transaction.neto = 4500
    transaction.truck_tara = 500
    transaction.produce = "apples"
    transaction.container_list = ["C001", "C002"]
    transaction.get_display_produce.return_value = "apples"
    return transaction


class TestQueryTransactions:
    """Test query_transactions method."""

    @pytest.mark.asyncio
    async def test_query_transactions_no_filters(self, query_service, mock_transaction):
        """Test querying transactions without filters."""
        # Arrange
        query_service.transaction_repo.get_transactions_in_range = AsyncMock(
            return_value=[mock_transaction]
        )
        params = WeightQueryParams()

        # Act
        result = await query_service.query_transactions(params)

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TransactionResponse)
        assert result[0].id == "session-123"
        assert result[0].truck == "ABC123"

    @pytest.mark.asyncio
    async def test_query_transactions_with_from_time(self, query_service, mock_transaction):
        """Test querying with from_time filter."""
        # Arrange
        query_service.transaction_repo.get_transactions_in_range = AsyncMock(
            return_value=[mock_transaction]
        )
        params = WeightQueryParams(from_time="20250101120000")

        # Act
        result = await query_service.query_transactions(params)

        # Assert
        assert len(result) == 1
        query_service.transaction_repo.get_transactions_in_range.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_transactions_with_to_time(self, query_service, mock_transaction):
        """Test querying with to_time filter."""
        # Arrange
        query_service.transaction_repo.get_transactions_in_range = AsyncMock(
            return_value=[mock_transaction]
        )
        params = WeightQueryParams(to_time="20250201120000")

        # Act
        result = await query_service.query_transactions(params)

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_query_transactions_with_date_range(self, query_service, mock_transaction):
        """Test querying with both from_time and to_time."""
        # Arrange
        query_service.transaction_repo.get_transactions_in_range = AsyncMock(
            return_value=[mock_transaction]
        )
        params = WeightQueryParams(
            from_time="20250101120000",
            to_time="20250201120000"
        )

        # Act
        result = await query_service.query_transactions(params)

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_query_transactions_invalid_date_range(self, query_service):
        """Test querying with invalid date range (from > to)."""
        # Arrange
        params = WeightQueryParams(
            from_time="20250201120000",
            to_time="20250101120000"
        )

        # Act & Assert
        with pytest.raises(InvalidDateRangeError) as exc_info:
            await query_service.query_transactions(params)
        assert "From date cannot be after To date" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_query_transactions_with_direction_filter(self, query_service, mock_transaction):
        """Test querying with direction filter."""
        # Arrange
        query_service.transaction_repo.get_transactions_in_range = AsyncMock(
            return_value=[mock_transaction]
        )
        params = WeightQueryParams(filter="in")

        # Act
        result = await query_service.query_transactions(params)

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_query_transactions_with_multiple_directions(self, query_service, mock_transaction, mock_transaction_out):
        """Test querying with multiple direction filters."""
        # Arrange
        query_service.transaction_repo.get_transactions_in_range = AsyncMock(
            return_value=[mock_transaction, mock_transaction_out]
        )
        params = WeightQueryParams(filter="in,out")

        # Act
        result = await query_service.query_transactions(params)

        # Assert
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_query_transactions_empty_result(self, query_service):
        """Test querying with no results."""
        # Arrange
        query_service.transaction_repo.get_transactions_in_range = AsyncMock(
            return_value=[]
        )
        params = WeightQueryParams()

        # Act
        result = await query_service.query_transactions(params)

        # Assert
        assert len(result) == 0


class TestQueryByTimeRange:
    """Test query_by_time_range method."""

    @pytest.mark.asyncio
    async def test_query_by_time_range(self, query_service, mock_transaction):
        """Test querying by time range."""
        # Arrange
        query_service.transaction_repo.get_transactions_in_range = AsyncMock(
            return_value=[mock_transaction]
        )
        from_time = datetime(2025, 1, 1, 0, 0, 0)
        to_time = datetime(2025, 1, 31, 23, 59, 59)

        # Act
        result = await query_service.query_by_time_range(from_time, to_time)

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TransactionResponse)

    @pytest.mark.asyncio
    async def test_query_by_time_range_with_directions(self, query_service, mock_transaction):
        """Test querying by time range with direction filter."""
        # Arrange
        query_service.transaction_repo.get_transactions_in_range = AsyncMock(
            return_value=[mock_transaction]
        )
        from_time = datetime(2025, 1, 1, 0, 0, 0)
        to_time = datetime(2025, 1, 31, 23, 59, 59)

        # Act
        result = await query_service.query_by_time_range(
            from_time, to_time, directions=["in"]
        )

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_query_by_time_range_with_limit(self, query_service, mock_transaction):
        """Test querying by time range with limit."""
        # Arrange
        query_service.transaction_repo.get_transactions_in_range = AsyncMock(
            return_value=[mock_transaction]
        )
        from_time = datetime(2025, 1, 1, 0, 0, 0)
        to_time = datetime(2025, 1, 31, 23, 59, 59)

        # Act
        result = await query_service.query_by_time_range(
            from_time, to_time, limit=10
        )

        # Assert
        assert len(result) == 1


class TestQueryByDirection:
    """Test query_by_direction method."""

    @pytest.mark.asyncio
    async def test_query_by_direction_in(self, query_service, mock_transaction):
        """Test querying by direction 'in'."""
        # Arrange
        query_service.transaction_repo.get_transactions_in_range = AsyncMock(
            return_value=[mock_transaction]
        )

        # Act
        result = await query_service.query_by_direction("in")

        # Assert
        assert len(result) == 1
        assert result[0].direction == "in"

    @pytest.mark.asyncio
    async def test_query_by_direction_with_time_range(self, query_service, mock_transaction):
        """Test querying by direction with time range."""
        # Arrange
        query_service.transaction_repo.get_transactions_in_range = AsyncMock(
            return_value=[mock_transaction]
        )
        from_time = datetime(2025, 1, 1, 0, 0, 0)
        to_time = datetime(2025, 1, 31, 23, 59, 59)

        # Act
        result = await query_service.query_by_direction("out", from_time, to_time)

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_query_by_direction_with_limit(self, query_service, mock_transaction):
        """Test querying by direction with limit."""
        # Arrange
        query_service.transaction_repo.get_transactions_in_range = AsyncMock(
            return_value=[mock_transaction]
        )

        # Act
        result = await query_service.query_by_direction("in", limit=5)

        # Assert
        assert len(result) == 1


class TestQueryByTruck:
    """Test query_by_truck method."""

    @pytest.mark.asyncio
    async def test_query_by_truck(self, query_service, mock_transaction):
        """Test querying by truck."""
        # Arrange
        query_service.transaction_repo.get_transactions_by_truck = AsyncMock(
            return_value=[mock_transaction]
        )

        # Act
        result = await query_service.query_by_truck("ABC123")

        # Assert
        assert len(result) == 1
        assert result[0].truck == "ABC123"

    @pytest.mark.asyncio
    async def test_query_by_truck_with_time_range(self, query_service, mock_transaction):
        """Test querying by truck with time range."""
        # Arrange
        query_service.transaction_repo.get_transactions_by_truck = AsyncMock(
            return_value=[mock_transaction]
        )
        from_time = datetime(2025, 1, 1, 0, 0, 0)
        to_time = datetime(2025, 1, 31, 23, 59, 59)

        # Act
        result = await query_service.query_by_truck("ABC123", from_time, to_time)

        # Assert
        assert len(result) == 1
        query_service.transaction_repo.get_transactions_by_truck.assert_called_once_with(
            truck="ABC123", from_time=from_time, to_time=to_time
        )

    @pytest.mark.asyncio
    async def test_query_by_truck_empty_result(self, query_service):
        """Test querying by truck with no results."""
        # Arrange
        query_service.transaction_repo.get_transactions_by_truck = AsyncMock(
            return_value=[]
        )

        # Act
        result = await query_service.query_by_truck("NONEXISTENT")

        # Assert
        assert len(result) == 0


class TestGetTruckInfo:
    """Test get_truck_info method."""

    @pytest.mark.asyncio
    async def test_get_truck_info_basic(self, query_service, mock_transaction):
        """Test getting truck info without params."""
        # Arrange
        mock_transaction.truck_tara = 500
        query_service.transaction_repo.get_transactions_by_truck = AsyncMock(
            return_value=[mock_transaction]
        )

        # Act
        result = await query_service.get_truck_info("ABC123")

        # Assert
        assert isinstance(result, ItemResponse)
        assert result.id == "ABC123"
        assert result.item_type == "truck"
        assert result.tara == 500
        assert len(result.sessions) == 1

    @pytest.mark.asyncio
    async def test_get_truck_info_with_params(self, query_service, mock_transaction):
        """Test getting truck info with query params."""
        # Arrange
        mock_transaction.truck_tara = 500
        query_service.transaction_repo.get_transactions_by_truck = AsyncMock(
            return_value=[mock_transaction]
        )
        params = ItemQueryParams(
            from_time="20250101120000",
            to_time="20250201120000"
        )

        # Act
        result = await query_service.get_truck_info("ABC123", params)

        # Assert
        assert result.id == "ABC123"
        assert result.item_type == "truck"

    @pytest.mark.asyncio
    async def test_get_truck_info_no_tara(self, query_service, mock_transaction):
        """Test getting truck info with no tara weight."""
        # Arrange
        mock_transaction.truck_tara = None
        query_service.transaction_repo.get_transactions_by_truck = AsyncMock(
            return_value=[mock_transaction]
        )

        # Act
        result = await query_service.get_truck_info("ABC123")

        # Assert
        assert result.tara == "na"

    @pytest.mark.asyncio
    async def test_get_truck_info_multiple_transactions(self, query_service):
        """Test getting truck info with multiple transactions."""
        # Arrange
        transaction1 = MagicMock(spec=Transaction)
        transaction1.session_id = "session-1"
        transaction1.truck_tara = 500

        transaction2 = MagicMock(spec=Transaction)
        transaction2.session_id = "session-2"
        transaction2.truck_tara = 600

        query_service.transaction_repo.get_transactions_by_truck = AsyncMock(
            return_value=[transaction1, transaction2]
        )

        # Act
        result = await query_service.get_truck_info("ABC123")

        # Assert
        assert result.tara == 550  # Average of 500 and 600
        assert len(result.sessions) == 2


class TestGetContainerInfo:
    """Test get_container_info method."""

    @pytest.mark.asyncio
    async def test_get_container_info_known_container(self, query_service):
        """Test getting info for known container."""
        # Arrange
        container_info = ContainerWeightInfo(
            container_id="C001",
            weight=100,
            is_known=True
        )
        query_service.container_service.get_container_weight = AsyncMock(
            return_value=container_info
        )
        query_service.transaction_repo.get_sessions_with_container = AsyncMock(
            return_value=["session-1", "session-2"]
        )

        # Act
        result = await query_service.get_container_info("C001")

        # Assert
        assert isinstance(result, ItemResponse)
        assert result.id == "C001"
        assert result.item_type == "container"
        assert result.tara == 100
        assert len(result.sessions) == 2

    @pytest.mark.asyncio
    async def test_get_container_info_unknown_container(self, query_service):
        """Test getting info for unknown container."""
        # Arrange
        container_info = ContainerWeightInfo(
            container_id="C999",
            weight=0,
            is_known=False
        )
        query_service.container_service.get_container_weight = AsyncMock(
            return_value=container_info
        )
        query_service.transaction_repo.get_sessions_with_container = AsyncMock(
            return_value=[]
        )

        # Act
        result = await query_service.get_container_info("C999")

        # Assert
        assert result.tara == "na"

    @pytest.mark.asyncio
    async def test_get_container_info_with_params(self, query_service):
        """Test getting container info with query params."""
        # Arrange
        container_info = ContainerWeightInfo(
            container_id="C001",
            weight=100,
            is_known=True
        )
        query_service.container_service.get_container_weight = AsyncMock(
            return_value=container_info
        )
        query_service.transaction_repo.get_sessions_with_container = AsyncMock(
            return_value=["session-1"]
        )
        params = ItemQueryParams(
            from_time="20250101120000",
            to_time="20250201120000"
        )

        # Act
        result = await query_service.get_container_info("C001", params)

        # Assert
        assert result.id == "C001"
        query_service.transaction_repo.get_sessions_with_container.assert_called_once()


class TestGetItemInfo:
    """Test get_item_info method."""

    @pytest.mark.asyncio
    async def test_get_item_info_truck(self, query_service, mock_transaction):
        """Test getting item info for truck."""
        # Arrange
        query_service._detect_item_type = AsyncMock(return_value="truck")
        query_service.get_item_sessions = AsyncMock(return_value=["session-1"])
        query_service.container_repo.get_by_id = AsyncMock(return_value=None)

        # Act
        result = await query_service.get_item_info("ABC123")

        # Assert
        assert result.id == "ABC123"
        assert result.item_type == "truck"
        assert result.tara == "na"

    @pytest.mark.asyncio
    async def test_get_item_info_container(self, query_service):
        """Test getting item info for container."""
        # Arrange
        mock_container = MagicMock()
        mock_container.weight = 100
        query_service._detect_item_type = AsyncMock(return_value="container")
        query_service.get_item_sessions = AsyncMock(return_value=["session-1"])
        query_service.container_repo.get_by_id = AsyncMock(return_value=mock_container)

        # Act
        result = await query_service.get_item_info("C001")

        # Assert
        assert result.id == "C001"
        assert result.item_type == "container"
        assert result.tara == "100"

    @pytest.mark.asyncio
    async def test_get_item_info_unknown(self, query_service):
        """Test getting item info for unknown item."""
        # Arrange
        query_service._detect_item_type = AsyncMock(return_value="unknown")

        # Act
        result = await query_service.get_item_info("UNKNOWN123")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_item_info_with_datetime_params(self, query_service):
        """Test getting item info with datetime parameters."""
        # Arrange
        query_service._detect_item_type = AsyncMock(return_value="truck")
        query_service.get_item_sessions = AsyncMock(return_value=["session-1"])
        query_service.container_repo.get_by_id = AsyncMock(return_value=None)

        # Act
        result = await query_service.get_item_info(
            "ABC123",
            from_datetime="20250101120000",
            to_datetime="20250201120000"
        )

        # Assert
        assert result is not None
        query_service.get_item_sessions.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_item_info_container_exception(self, query_service):
        """Test getting item info when container lookup raises exception."""
        # Arrange
        query_service._detect_item_type = AsyncMock(return_value="container")
        query_service.get_item_sessions = AsyncMock(return_value=["session-1"])
        query_service.container_repo.get_by_id = AsyncMock(side_effect=Exception("DB error"))

        # Act
        result = await query_service.get_item_info("C001")

        # Assert
        assert result.tara == "na"  # Should handle exception gracefully


class TestGetItemSessions:
    """Test get_item_sessions method."""

    @pytest.mark.asyncio
    async def test_get_item_sessions_auto_detect_container(self, query_service):
        """Test getting sessions with auto-detection for container."""
        # Arrange
        query_service._detect_item_type = AsyncMock(return_value="container")
        query_service.transaction_repo.get_sessions_with_container = AsyncMock(
            return_value=["session-1", "session-2"]
        )

        # Act
        result = await query_service.get_item_sessions("C001", item_type="auto")

        # Assert
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_item_sessions_auto_detect_truck(self, query_service, mock_transaction):
        """Test getting sessions with auto-detection for truck."""
        # Arrange
        transaction1 = MagicMock(spec=Transaction)
        transaction1.session_id = "session-1"
        transaction2 = MagicMock(spec=Transaction)
        transaction2.session_id = "session-2"

        query_service._detect_item_type = AsyncMock(return_value="truck")
        query_service.transaction_repo.get_transactions_by_truck = AsyncMock(
            return_value=[transaction1, transaction2]
        )

        # Act
        result = await query_service.get_item_sessions("ABC123", item_type="auto")

        # Assert
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_item_sessions_explicit_container(self, query_service):
        """Test getting sessions with explicit container type."""
        # Arrange
        query_service.transaction_repo.get_sessions_with_container = AsyncMock(
            return_value=["session-1"]
        )

        # Act
        result = await query_service.get_item_sessions("C001", item_type="container")

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_item_sessions_explicit_truck(self, query_service):
        """Test getting sessions with explicit truck type."""
        # Arrange
        transaction1 = MagicMock(spec=Transaction)
        transaction1.session_id = "session-1"

        query_service.transaction_repo.get_transactions_by_truck = AsyncMock(
            return_value=[transaction1]
        )

        # Act
        result = await query_service.get_item_sessions("ABC123", item_type="truck")

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_item_sessions_unknown_type(self, query_service):
        """Test getting sessions for unknown type."""
        # Arrange
        query_service._detect_item_type = AsyncMock(return_value="unknown")

        # Act
        result = await query_service.get_item_sessions("UNKNOWN", item_type="auto")

        # Assert
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_item_sessions_with_time_range(self, query_service):
        """Test getting sessions with time range filter."""
        # Arrange
        query_service.transaction_repo.get_sessions_with_container = AsyncMock(
            return_value=["session-1"]
        )
        from_time = datetime(2025, 1, 1, 0, 0, 0)
        to_time = datetime(2025, 1, 31, 23, 59, 59)

        # Act
        result = await query_service.get_item_sessions(
            "C001",
            item_type="container",
            from_time=from_time,
            to_time=to_time
        )

        # Assert
        assert len(result) == 1
        query_service.transaction_repo.get_sessions_with_container.assert_called_once_with(
            container_id="C001",
            from_time=from_time,
            to_time=to_time
        )


class TestCalculateItemStatistics:
    """Test calculate_item_statistics method."""

    @pytest.mark.asyncio
    async def test_calculate_item_statistics_container(self, query_service):
        """Test calculating statistics for container."""
        # Arrange
        query_service._detect_item_type = AsyncMock(return_value="container")
        query_service._calculate_container_statistics = AsyncMock(
            return_value={
                "item_id": "C001",
                "item_type": "container",
                "total_sessions": 5
            }
        )

        # Act
        result = await query_service.calculate_item_statistics("C001", item_type="auto")

        # Assert
        assert result["item_id"] == "C001"
        assert result["item_type"] == "container"

    @pytest.mark.asyncio
    async def test_calculate_item_statistics_truck(self, query_service):
        """Test calculating statistics for truck."""
        # Arrange
        query_service._detect_item_type = AsyncMock(return_value="truck")
        query_service._calculate_truck_statistics = AsyncMock(
            return_value={
                "item_id": "ABC123",
                "item_type": "truck",
                "total_sessions": 10
            }
        )

        # Act
        result = await query_service.calculate_item_statistics("ABC123", item_type="auto")

        # Assert
        assert result["item_id"] == "ABC123"
        assert result["item_type"] == "truck"

    @pytest.mark.asyncio
    async def test_calculate_item_statistics_unknown(self, query_service):
        """Test calculating statistics for unknown item."""
        # Arrange
        query_service._detect_item_type = AsyncMock(return_value="unknown")

        # Act
        result = await query_service.calculate_item_statistics("UNKNOWN", item_type="auto")

        # Assert
        assert result["item_id"] == "UNKNOWN"
        assert result["item_type"] == "unknown"
        assert result["total_sessions"] == 0
        assert result["total_transactions"] == 0


class TestGetQueryPerformanceInfo:
    """Test get_query_performance_info method."""

    @pytest.mark.asyncio
    async def test_get_query_performance_info(self, query_service):
        """Test getting query performance info."""
        # Arrange
        mock_stats = {"total_transactions": 100, "total_sessions": 50}
        query_service.transaction_repo.get_session_statistics = AsyncMock(
            return_value=mock_stats
        )
        mock_container = MagicMock()
        query_service.container_repo.get_all_with_weights = AsyncMock(
            return_value=[mock_container, mock_container]
        )
        query_service.container_repo.get_unknown_containers = AsyncMock(
            return_value=[MagicMock()]
        )

        # Act
        result = await query_service.get_query_performance_info()

        # Assert
        assert "time_range" in result
        assert "transaction_stats" in result
        assert "container_stats" in result
        assert "database_info" in result
        assert result["container_stats"]["registered_containers"] == 2
        assert result["container_stats"]["unknown_containers"] == 1

    @pytest.mark.asyncio
    async def test_get_query_performance_info_with_time_range(self, query_service):
        """Test getting performance info with time range."""
        # Arrange
        mock_stats = {"total_transactions": 50, "total_sessions": 25}
        query_service.transaction_repo.get_session_statistics = AsyncMock(
            return_value=mock_stats
        )
        query_service.container_repo.get_all_with_weights = AsyncMock(
            return_value=[]
        )
        query_service.container_repo.get_unknown_containers = AsyncMock(
            return_value=[]
        )
        from_time = datetime(2025, 1, 1, 0, 0, 0)
        to_time = datetime(2025, 1, 31, 23, 59, 59)

        # Act
        result = await query_service.get_query_performance_info(from_time, to_time)

        # Assert
        assert result["time_range"]["from_time"] is not None
        assert result["time_range"]["to_time"] is not None


class TestSearchTransactions:
    """Test search_transactions method."""

    @pytest.mark.asyncio
    async def test_search_transactions_by_truck(self, query_service, mock_transaction):
        """Test searching transactions by truck."""
        # Arrange
        mock_transaction.truck = "ABC123"
        query_service.transaction_repo.get_transactions_in_range = AsyncMock(
            return_value=[mock_transaction]
        )

        # Act
        result = await query_service.search_transactions("ABC", search_fields=["truck"])

        # Assert
        assert len(result) == 1
        assert result[0].truck == "ABC123"

    @pytest.mark.asyncio
    async def test_search_transactions_by_produce(self, query_service, mock_transaction):
        """Test searching transactions by produce."""
        # Arrange
        mock_transaction.produce = "apples"
        query_service.transaction_repo.get_transactions_in_range = AsyncMock(
            return_value=[mock_transaction]
        )

        # Act
        result = await query_service.search_transactions("apple", search_fields=["produce"])

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_transactions_by_containers(self, query_service, mock_transaction):
        """Test searching transactions by containers."""
        # Arrange
        mock_transaction.container_list = ["C001", "C002"]
        query_service.transaction_repo.get_transactions_in_range = AsyncMock(
            return_value=[mock_transaction]
        )

        # Act
        result = await query_service.search_transactions("C001", search_fields=["containers"])

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_transactions_default_fields(self, query_service, mock_transaction):
        """Test searching with default search fields."""
        # Arrange
        mock_transaction.truck = "ABC123"
        query_service.transaction_repo.get_transactions_in_range = AsyncMock(
            return_value=[mock_transaction]
        )

        # Act
        result = await query_service.search_transactions("ABC")

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_transactions_with_limit(self, query_service):
        """Test searching with limit."""
        # Arrange
        transactions = [MagicMock(spec=Transaction) for _ in range(150)]
        for i, t in enumerate(transactions):
            t.truck = f"TRUCK{i:03d}"
            t.produce = "apples"
            t.container_list = []
            t.session_id = f"session-{i}"
            t.direction = "in"
            t.bruto = 5000
            t.neto = 4500
            t.get_display_produce = MagicMock(return_value="apples")

        query_service.transaction_repo.get_transactions_in_range = AsyncMock(
            return_value=transactions
        )

        # Act
        result = await query_service.search_transactions("TRUCK", limit=50)

        # Assert
        assert len(result) <= 50

    @pytest.mark.asyncio
    async def test_search_transactions_no_match(self, query_service, mock_transaction):
        """Test searching with no matching results."""
        # Arrange
        mock_transaction.truck = "ABC123"
        mock_transaction.produce = "apples"
        mock_transaction.container_list = ["C001"]
        query_service.transaction_repo.get_transactions_in_range = AsyncMock(
            return_value=[mock_transaction]
        )

        # Act
        result = await query_service.search_transactions("NOMATCH")

        # Assert
        assert len(result) == 0


class TestDetectItemType:
    """Test _detect_item_type method."""

    @pytest.mark.asyncio
    async def test_detect_item_type_registered_container(self, query_service):
        """Test detecting registered container."""
        # Arrange
        container_info = ContainerWeightInfo(
            container_id="C001",
            weight=100,
            is_known=True
        )
        query_service.container_service.get_container_weight = AsyncMock(
            return_value=container_info
        )

        # Act
        result = await query_service._detect_item_type("C001")

        # Assert
        assert result == "container"

    @pytest.mark.asyncio
    async def test_detect_item_type_truck_only(self, query_service, mock_transaction):
        """Test detecting truck (has truck transactions but no container usage)."""
        # Arrange
        container_info = ContainerWeightInfo(
            container_id="ABC123",
            weight=0,
            is_known=False
        )
        query_service.container_service.get_container_weight = AsyncMock(
            return_value=container_info
        )
        query_service.transaction_repo.get_transactions_by_truck = AsyncMock(
            return_value=[mock_transaction]
        )
        query_service.transaction_repo.get_sessions_with_container = AsyncMock(
            return_value=[]
        )

        # Act
        result = await query_service._detect_item_type("ABC123")

        # Assert
        assert result == "truck"

    @pytest.mark.asyncio
    async def test_detect_item_type_container_only(self, query_service):
        """Test detecting container (has container usage but no truck transactions)."""
        # Arrange
        container_info = ContainerWeightInfo(
            container_id="C001",
            weight=0,
            is_known=False
        )
        query_service.container_service.get_container_weight = AsyncMock(
            return_value=container_info
        )
        query_service.transaction_repo.get_transactions_by_truck = AsyncMock(
            return_value=[]
        )
        query_service.transaction_repo.get_sessions_with_container = AsyncMock(
            return_value=["session-1"]
        )

        # Act
        result = await query_service._detect_item_type("C001")

        # Assert
        assert result == "container"

    @pytest.mark.asyncio
    async def test_detect_item_type_both_prefer_container(self, query_service, mock_transaction):
        """Test detecting when used as both - should prefer container."""
        # Arrange
        container_info = ContainerWeightInfo(
            container_id="ITEM123",
            weight=0,
            is_known=False
        )
        query_service.container_service.get_container_weight = AsyncMock(
            return_value=container_info
        )
        query_service.transaction_repo.get_transactions_by_truck = AsyncMock(
            return_value=[mock_transaction]
        )
        query_service.transaction_repo.get_sessions_with_container = AsyncMock(
            return_value=["session-1"]
        )

        # Act
        result = await query_service._detect_item_type("ITEM123")

        # Assert
        assert result == "container"

    @pytest.mark.asyncio
    async def test_detect_item_type_truck_fallback(self, query_service, mock_transaction):
        """Test detecting truck when no container sessions but has truck transactions."""
        # Arrange
        container_info = ContainerWeightInfo(
            container_id="ABC123",
            weight=0,
            is_known=False
        )
        query_service.container_service.get_container_weight = AsyncMock(
            return_value=container_info
        )
        query_service.transaction_repo.get_transactions_by_truck = AsyncMock(
            return_value=[mock_transaction]
        )
        query_service.transaction_repo.get_sessions_with_container = AsyncMock(
            return_value=[]
        )

        # Act
        result = await query_service._detect_item_type("ABC123")

        # Assert
        assert result == "truck"

    @pytest.mark.asyncio
    async def test_detect_item_type_unknown(self, query_service):
        """Test detecting unknown item."""
        # Arrange
        container_info = ContainerWeightInfo(
            container_id="UNKNOWN",
            weight=0,
            is_known=False
        )
        query_service.container_service.get_container_weight = AsyncMock(
            return_value=container_info
        )
        query_service.transaction_repo.get_transactions_by_truck = AsyncMock(
            return_value=[]
        )
        query_service.transaction_repo.get_sessions_with_container = AsyncMock(
            return_value=[]
        )

        # Act
        result = await query_service._detect_item_type("UNKNOWN")

        # Assert
        assert result == "unknown"


class TestCalculateContainerStatistics:
    """Test _calculate_container_statistics method."""

    @pytest.mark.asyncio
    async def test_calculate_container_statistics(self, query_service, mock_transaction, mock_transaction_out):
        """Test calculating container statistics."""
        # Arrange
        container_info = ContainerWeightInfo(
            container_id="C001",
            weight=100,
            is_known=True
        )
        query_service.container_service.get_container_weight = AsyncMock(
            return_value=container_info
        )
        query_service.transaction_repo.get_sessions_with_container = AsyncMock(
            return_value=["session-1", "session-2"]
        )

        mock_transaction.container_list = ["C001"]
        mock_transaction.direction = "in"
        mock_transaction_out.container_list = ["C001"]
        mock_transaction_out.direction = "out"

        query_service.transaction_repo.get_transactions_in_range = AsyncMock(
            return_value=[mock_transaction, mock_transaction_out]
        )

        # Act
        result = await query_service._calculate_container_statistics("C001", None, None)

        # Assert
        assert result["item_id"] == "C001"
        assert result["item_type"] == "container"
        assert result["is_registered"] is True
        assert result["weight"] == 100
        assert result["total_sessions"] == 2
        assert result["total_transactions"] == 2
        assert "direction_breakdown" in result

    @pytest.mark.asyncio
    async def test_calculate_container_statistics_unknown_container(self, query_service):
        """Test calculating statistics for unknown container."""
        # Arrange
        container_info = ContainerWeightInfo(
            container_id="C999",
            weight=0,
            is_known=False
        )
        query_service.container_service.get_container_weight = AsyncMock(
            return_value=container_info
        )
        query_service.transaction_repo.get_sessions_with_container = AsyncMock(
            return_value=[]
        )
        query_service.transaction_repo.get_transactions_in_range = AsyncMock(
            return_value=[]
        )

        # Act
        result = await query_service._calculate_container_statistics("C999", None, None)

        # Assert
        assert result["is_registered"] is False
        assert result["weight"] == 0


class TestCalculateTruckStatistics:
    """Test _calculate_truck_statistics method."""

    @pytest.mark.asyncio
    async def test_calculate_truck_statistics(self, query_service, mock_transaction, mock_transaction_out):
        """Test calculating truck statistics."""
        # Arrange
        mock_transaction.session_id = "session-1"
        mock_transaction.direction = "in"
        mock_transaction.truck_tara = 500

        mock_transaction_out.session_id = "session-1"
        mock_transaction_out.direction = "out"
        mock_transaction_out.truck_tara = 500

        query_service.transaction_repo.get_transactions_by_truck = AsyncMock(
            return_value=[mock_transaction, mock_transaction_out]
        )

        # Act
        result = await query_service._calculate_truck_statistics("ABC123", None, None)

        # Assert
        assert result["item_id"] == "ABC123"
        assert result["item_type"] == "truck"
        assert result["total_sessions"] == 1
        assert result["total_transactions"] == 2
        assert result["average_tara"] == 500
        assert "direction_breakdown" in result

    @pytest.mark.asyncio
    async def test_calculate_truck_statistics_no_tara(self, query_service, mock_transaction):
        """Test calculating truck statistics with no tara weights."""
        # Arrange
        mock_transaction.truck_tara = None
        query_service.transaction_repo.get_transactions_by_truck = AsyncMock(
            return_value=[mock_transaction]
        )

        # Act
        result = await query_service._calculate_truck_statistics("ABC123", None, None)

        # Assert
        assert result["average_tara"] is None


class TestTransactionToResponse:
    """Test _transaction_to_response method."""

    def test_transaction_to_response_with_neto(self, query_service, mock_transaction):
        """Test converting transaction with neto value."""
        # Arrange
        mock_transaction.neto = 4500

        # Act
        result = query_service._transaction_to_response(mock_transaction)

        # Assert
        assert isinstance(result, TransactionResponse)
        assert result.id == "session-123"
        assert result.direction == "in"
        assert result.truck == "ABC123"
        assert result.bruto == 5000
        assert result.neto == 4500

    def test_transaction_to_response_without_neto(self, query_service, mock_transaction):
        """Test converting transaction without neto value."""
        # Arrange
        mock_transaction.neto = None

        # Act
        result = query_service._transaction_to_response(mock_transaction)

        # Assert
        assert result.neto == "na"

    def test_transaction_to_response_with_produce(self, query_service, mock_transaction):
        """Test converting transaction with produce."""
        # Arrange
        mock_transaction.get_display_produce.return_value = "apples"

        # Act
        result = query_service._transaction_to_response(mock_transaction)

        # Assert
        assert result.produce == "apples"

    def test_transaction_to_response_containers(self, query_service, mock_transaction):
        """Test converting transaction with containers."""
        # Arrange
        mock_transaction.container_list = ["C001", "C002", "C003"]

        # Act
        result = query_service._transaction_to_response(mock_transaction)

        # Assert
        assert len(result.containers) == 3
        assert "C001" in result.containers
