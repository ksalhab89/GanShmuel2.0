"""Tests for SessionService business logic."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from src.models.schemas import SessionPair, SessionResponse, TransactionResponse
from src.models.database import Transaction
from src.services.session_service import (
    SessionService,
    SessionNotFoundError,
    SessionStateError
)


class TestSessionService:
    """Test cases for SessionService."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def session_service(self, mock_session):
        """Create SessionService instance with mocked dependencies."""
        service = SessionService(mock_session)
        service.session_repo = AsyncMock()
        service.transaction_repo = AsyncMock()
        return service

    @pytest.fixture
    def mock_transaction(self):
        """Create a mock transaction object."""
        transaction = MagicMock(spec=Transaction)
        transaction.id = 1
        transaction.session_id = "test-session-123"
        transaction.direction = "in"
        transaction.truck = "ABC123"
        transaction.containers = "C001,C002"
        transaction.container_list = ["C001", "C002"]
        transaction.bruto = 10000
        transaction.truck_tara = None
        transaction.neto = None
        transaction.produce = "orange"
        transaction.datetime = datetime(2024, 1, 1, 10, 0, 0)
        transaction.get_display_truck = MagicMock(return_value="ABC123")
        return transaction

    @pytest.fixture
    def transaction_response(self):
        """Create a valid TransactionResponse for SessionPair."""
        return TransactionResponse(
            id="test-session-123",
            direction="in",
            truck="ABC123",
            bruto=10000,
            produce="orange",
            containers=["C001", "C002"]
        )

    # ========================================================================
    # Test create_session
    # ========================================================================

    @pytest.mark.asyncio
    async def test_create_session_success(self, session_service, mock_session, mock_transaction):
        """Test successful session creation."""
        # Arrange
        direction = "in"
        truck = "ABC123"
        containers = ["C001", "C002"]
        bruto = 10000
        produce = "orange"

        session_service.transaction_repo.create.return_value = mock_transaction

        # Act
        session_id, transaction = await session_service.create_session(
            direction=direction,
            truck=truck,
            containers=containers,
            bruto=bruto,
            produce=produce
        )

        # Assert
        assert session_id is not None
        assert transaction == mock_transaction
        session_service.transaction_repo.create.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_session_generates_uuid(self, session_service, mock_session, mock_transaction):
        """Test that session creation generates a valid UUID."""
        # Arrange
        session_service.transaction_repo.create.return_value = mock_transaction

        # Act
        session_id, _ = await session_service.create_session(
            direction="in",
            truck="ABC123",
            containers=["C001"],
            bruto=10000
        )

        # Assert
        # Verify it's a valid UUID
        assert uuid.UUID(session_id)

    @pytest.mark.asyncio
    async def test_create_session_without_produce(self, session_service, mock_session, mock_transaction):
        """Test session creation without produce parameter."""
        # Arrange
        session_service.transaction_repo.create.return_value = mock_transaction

        # Act
        session_id, transaction = await session_service.create_session(
            direction="in",
            truck="ABC123",
            containers=["C001"],
            bruto=10000
        )

        # Assert
        assert session_id is not None
        assert transaction == mock_transaction
        call_args = session_service.transaction_repo.create.call_args
        assert call_args.kwargs.get("produce") is None

    # ========================================================================
    # Test complete_session
    # ========================================================================

    @pytest.mark.asyncio
    async def test_complete_session_success(self, session_service, mock_session, mock_transaction):
        """Test successful session completion."""
        # Arrange
        session_id = "test-session-123"
        out_transaction = MagicMock()
        out_transaction.direction = "out"

        session_service.transaction_repo.get_by_session_id.return_value = [mock_transaction]
        session_service.transaction_repo.create.return_value = out_transaction
        session_service.transaction_repo.get_by_session_and_direction.return_value = mock_transaction

        # Act
        result = await session_service.complete_session(
            session_id=session_id,
            direction="out",
            truck="ABC123",
            containers=["C001", "C002"],
            bruto=8000,
            truck_tara=500,
            neto=7500,
            produce="orange"
        )

        # Assert
        assert result == out_transaction
        session_service.transaction_repo.get_by_session_id.assert_called_once_with(session_id)
        session_service.transaction_repo.create.assert_called_once()
        session_service.transaction_repo.update_out_transaction.assert_called()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_session_not_found(self, session_service, mock_session):
        """Test completing a non-existent session."""
        # Arrange
        session_id = "nonexistent-session"
        session_service.transaction_repo.get_by_session_id.return_value = []

        # Act & Assert
        with pytest.raises(SessionNotFoundError) as exc_info:
            await session_service.complete_session(
                session_id=session_id,
                direction="out",
                truck="ABC123",
                containers=["C001"],
                bruto=8000,
                truck_tara=500,
                neto=7500
            )

        assert f"Session {session_id} not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_complete_session_updates_in_transaction(self, session_service, mock_session, mock_transaction):
        """Test that completing OUT session also updates IN transaction."""
        # Arrange
        session_id = "test-session-123"
        out_transaction = MagicMock()
        out_transaction.direction = "out"

        session_service.transaction_repo.get_by_session_id.return_value = [mock_transaction]
        session_service.transaction_repo.create.return_value = out_transaction
        session_service.transaction_repo.get_by_session_and_direction.return_value = mock_transaction

        # Act
        await session_service.complete_session(
            session_id=session_id,
            direction="out",
            truck="ABC123",
            containers=["C001"],
            bruto=8000,
            truck_tara=500,
            neto=7500
        )

        # Assert
        assert session_service.transaction_repo.update_out_transaction.call_count == 2
        session_service.transaction_repo.get_by_session_and_direction.assert_called_once_with(session_id, "in")

    @pytest.mark.asyncio
    async def test_complete_session_without_in_transaction(self, session_service, mock_session, mock_transaction):
        """Test completing session when IN transaction doesn't exist."""
        # Arrange
        session_id = "test-session-123"
        out_transaction = MagicMock()

        session_service.transaction_repo.get_by_session_id.return_value = [mock_transaction]
        session_service.transaction_repo.create.return_value = out_transaction
        session_service.transaction_repo.get_by_session_and_direction.return_value = None

        # Act
        result = await session_service.complete_session(
            session_id=session_id,
            direction="out",
            truck="ABC123",
            containers=["C001"],
            bruto=8000,
            truck_tara=500,
            neto=7500
        )

        # Assert
        assert result == out_transaction
        # Should only update OUT transaction, not IN
        assert session_service.transaction_repo.update_out_transaction.call_count == 1

    # ========================================================================
    # Test get_session_details
    # ========================================================================

    @pytest.mark.asyncio
    async def test_get_session_details_success(self, session_service):
        """Test getting session details successfully."""
        # Arrange
        session_id = "test-session-123"
        in_trans = TransactionResponse(
            id=session_id,
            direction="in",
            truck="ABC123",
            bruto=10000,
            produce="orange",
            containers=["C001"]
        )
        out_trans = TransactionResponse(
            id=session_id,
            direction="out",
            truck="ABC123",
            bruto=8000,
            produce="orange",
            containers=["C001"]
        )
        mock_session_pair = SessionPair(
            session_id=session_id,
            in_transaction=in_trans,
            out_transaction=out_trans,
            is_complete=True
        )
        session_service.session_repo.get_session_details.return_value = mock_session_pair

        # Act
        result = await session_service.get_session_details(session_id)

        # Assert
        assert result == mock_session_pair
        session_service.session_repo.get_session_details.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_get_session_details_not_found(self, session_service):
        """Test getting details for non-existent session."""
        # Arrange
        session_service.session_repo.get_session_details.return_value = None

        # Act
        result = await session_service.get_session_details("nonexistent")

        # Assert
        assert result is None

    # ========================================================================
    # Test get_session_response
    # ========================================================================

    @pytest.mark.asyncio
    async def test_get_session_response_with_out_transaction(self, session_service):
        """Test getting session response with OUT transaction."""
        # Arrange
        session_id = "test-session-123"
        in_trans = TransactionResponse(
            id=session_id,
            direction="in",
            truck="ABC123",
            bruto=10000,
            produce="orange",
            containers=["C001"]
        )
        out_trans = TransactionResponse(
            id=session_id,
            direction="out",
            truck="ABC123",
            bruto=8000,
            neto=7500,
            produce="orange",
            containers=["C001"]
        )

        # Need to mock the transaction to have get_display_truck method
        mock_out = MagicMock()
        mock_out.get_display_truck.return_value = "ABC123"
        mock_out.bruto = 8000
        mock_out.truck_tara = 500
        mock_out.neto = 7500

        mock_session_pair = MagicMock()
        mock_session_pair.out_transaction = mock_out
        mock_session_pair.in_transaction = None

        with patch.object(session_service, 'get_session_details', return_value=mock_session_pair):
            # Act
            result = await session_service.get_session_response(session_id)

            # Assert
            assert result is not None
            assert result.id == session_id
            assert result.truck == "ABC123"
            assert result.neto == 7500

    @pytest.mark.asyncio
    async def test_get_session_response_with_only_in_transaction(self, session_service):
        """Test getting session response with only IN transaction."""
        # Arrange
        session_id = "test-session-123"

        mock_in = MagicMock()
        mock_in.get_display_truck.return_value = "ABC123"
        mock_in.bruto = 10000
        mock_in.truck_tara = None
        mock_in.neto = None

        mock_session_pair = MagicMock()
        mock_session_pair.out_transaction = None
        mock_session_pair.in_transaction = mock_in

        with patch.object(session_service, 'get_session_details', return_value=mock_session_pair):
            # Act
            result = await session_service.get_session_response(session_id)

            # Assert
            assert result is not None
            assert result.id == session_id
            assert result.neto == "na"

    @pytest.mark.asyncio
    async def test_get_session_response_not_found(self, session_service):
        """Test getting response for non-existent session."""
        # Arrange
        with patch.object(session_service, 'get_session_details', return_value=None):
            # Act
            result = await session_service.get_session_response("nonexistent")

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_get_session_response_no_transactions(self, session_service):
        """Test getting response when session has no transactions."""
        # Arrange
        mock_session_pair = MagicMock()
        mock_session_pair.out_transaction = None
        mock_session_pair.in_transaction = None

        with patch.object(session_service, 'get_session_details', return_value=mock_session_pair):
            # Act
            result = await session_service.get_session_response("test-session")

            # Assert
            assert result is None

    # ========================================================================
    # Test find_active_sessions
    # ========================================================================

    @pytest.mark.asyncio
    async def test_find_active_sessions_no_filters(self, session_service):
        """Test finding active sessions without filters."""
        # Arrange - use real TransactionResponse object
        from src.models.schemas import TransactionResponse
        real_transaction = TransactionResponse(
            id="session-1",
            direction="in",
            truck="ABC123",
            bruto=10000,
            neto=None,
            produce="Apples",
            containers=["C001"]
        )
        session_service.transaction_repo.get_transactions_in_range.return_value = [real_transaction]
        session_service.transaction_repo.get_by_session_and_direction.return_value = None

        # Act
        result = await session_service.find_active_sessions()

        # Assert
        assert len(result) == 1
        # The result items are SessionPair objects with is_complete property
        assert hasattr(result[0], 'session_id')
        assert hasattr(result[0], 'is_complete')

    @pytest.mark.asyncio
    async def test_find_active_sessions_with_truck_filter(self, session_service):
        """Test finding active sessions filtered by truck."""
        # Arrange - use real TransactionResponse object
        from src.models.schemas import TransactionResponse
        real_transaction = TransactionResponse(
            id="session-1",
            direction="in",
            truck="ABC123",
            bruto=10000,
            neto=None,
            produce="Apples",
            containers=["C001"]
        )
        session_service.transaction_repo.get_transactions_in_range.return_value = [real_transaction]
        session_service.transaction_repo.get_by_session_and_direction.return_value = None

        # Act
        result = await session_service.find_active_sessions(truck="ABC123")

        # Assert
        assert len(result) == 1
        # Verify it has session structure
        assert hasattr(result[0], 'in_transaction')

    @pytest.mark.asyncio
    async def test_find_active_sessions_excludes_completed(self, session_service, mock_transaction):
        """Test that completed sessions are not included in active sessions."""
        # Arrange
        session_service.transaction_repo.get_transactions_in_range.return_value = [mock_transaction]
        session_service.transaction_repo.get_by_session_and_direction.return_value = MagicMock()

        # Act
        result = await session_service.find_active_sessions()

        # Assert
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_find_active_sessions_with_time_range(self, session_service):
        """Test finding active sessions with time range filter."""
        # Arrange - use real TransactionResponse object
        from src.models.schemas import TransactionResponse
        from_time = datetime(2024, 1, 1, 0, 0, 0)
        to_time = datetime(2024, 12, 31, 23, 59, 59)

        real_transaction = TransactionResponse(
            id="session-1",
            direction="in",
            truck="ABC123",
            bruto=10000,
            neto=None,
            produce="Apples",
            containers=["C001"]
        )
        session_service.transaction_repo.get_transactions_in_range.return_value = [real_transaction]
        session_service.transaction_repo.get_by_session_and_direction.return_value = None

        # Act
        result = await session_service.find_active_sessions(from_time=from_time, to_time=to_time)

        # Assert
        assert len(result) == 1
        # Verify the repo method was called
        assert session_service.transaction_repo.get_transactions_in_range.called

    # ========================================================================
    # Test get_sessions_by_truck
    # ========================================================================

    @pytest.mark.asyncio
    async def test_get_sessions_by_truck_success(self, session_service, mock_transaction):
        """Test getting sessions by truck."""
        # Arrange
        truck = "ABC123"
        in_transaction = MagicMock()
        in_transaction.session_id = "session-1"
        in_transaction.direction = "in"

        out_transaction = MagicMock()
        out_transaction.session_id = "session-1"
        out_transaction.direction = "out"

        session_service.transaction_repo.get_transactions_by_truck.return_value = [
            in_transaction, out_transaction
        ]

        # Act
        result = await session_service.get_sessions_by_truck(truck)

        # Assert
        assert len(result) == 1
        assert result[0].session_id == "session-1"
        assert result[0].is_complete is True

    @pytest.mark.asyncio
    async def test_get_sessions_by_truck_incomplete_session(self, session_service, mock_transaction):
        """Test getting incomplete session by truck."""
        # Arrange
        mock_transaction.direction = "in"
        session_service.transaction_repo.get_transactions_by_truck.return_value = [mock_transaction]

        # Act
        result = await session_service.get_sessions_by_truck("ABC123")

        # Assert
        assert len(result) == 1
        assert result[0].is_complete is False
        assert result[0].in_transaction is not None
        assert result[0].out_transaction is None

    @pytest.mark.asyncio
    async def test_get_sessions_by_truck_with_time_range(self, session_service, mock_transaction):
        """Test getting sessions by truck with time range."""
        # Arrange
        from_time = datetime(2024, 1, 1, 0, 0, 0)
        to_time = datetime(2024, 12, 31, 23, 59, 59)

        session_service.transaction_repo.get_transactions_by_truck.return_value = [mock_transaction]

        # Act
        result = await session_service.get_sessions_by_truck(
            truck="ABC123",
            from_time=from_time,
            to_time=to_time
        )

        # Assert
        assert len(result) == 1
        session_service.transaction_repo.get_transactions_by_truck.assert_called_once_with(
            "ABC123", from_time, to_time
        )

    # ========================================================================
    # Test get_sessions_by_time_range
    # ========================================================================

    @pytest.mark.asyncio
    async def test_get_sessions_by_time_range_success(self, session_service, mock_transaction):
        """Test getting sessions by time range."""
        # Arrange
        from_time = datetime(2024, 1, 1, 0, 0, 0)
        to_time = datetime(2024, 12, 31, 23, 59, 59)

        session_service.transaction_repo.get_transactions_in_range.return_value = [mock_transaction]

        # Act
        result = await session_service.get_sessions_by_time_range(from_time, to_time)

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_sessions_by_time_range_with_directions(self, session_service, mock_transaction):
        """Test getting sessions by time range with direction filter."""
        # Arrange
        from_time = datetime(2024, 1, 1, 0, 0, 0)
        to_time = datetime(2024, 12, 31, 23, 59, 59)
        directions = ["in"]

        session_service.transaction_repo.get_transactions_in_range.return_value = [mock_transaction]

        # Act
        result = await session_service.get_sessions_by_time_range(
            from_time, to_time, directions=directions
        )

        # Assert
        assert len(result) == 1
        session_service.transaction_repo.get_transactions_in_range.assert_called_once_with(
            from_time=from_time,
            to_time=to_time,
            directions=directions
        )

    @pytest.mark.asyncio
    async def test_get_sessions_by_time_range_groups_by_session(self, session_service):
        """Test that transactions are properly grouped by session."""
        # Arrange
        from_time = datetime(2024, 1, 1, 0, 0, 0)
        to_time = datetime(2024, 12, 31, 23, 59, 59)

        in_trans = MagicMock()
        in_trans.session_id = "session-1"
        in_trans.direction = "in"

        out_trans = MagicMock()
        out_trans.session_id = "session-1"
        out_trans.direction = "out"

        session_service.transaction_repo.get_transactions_in_range.return_value = [in_trans, out_trans]

        # Act
        result = await session_service.get_sessions_by_time_range(from_time, to_time)

        # Assert
        assert len(result) == 1
        assert result[0].in_transaction == in_trans
        assert result[0].out_transaction == out_trans
        assert result[0].is_complete is True

    # ========================================================================
    # Test get_sessions_by_produce_type
    # ========================================================================

    @pytest.mark.asyncio
    async def test_get_sessions_by_produce_type_success(self, session_service, mock_transaction):
        """Test getting sessions by produce type."""
        # Arrange
        mock_transaction.produce = "orange"
        session_service.transaction_repo.get_transactions_in_range.return_value = [mock_transaction]

        # Act
        result = await session_service.get_sessions_by_produce_type("orange")

        # Assert
        assert len(result) == 1
        assert result[0].in_transaction.produce == "orange"

    @pytest.mark.asyncio
    async def test_get_sessions_by_produce_type_na(self, session_service, mock_transaction):
        """Test getting sessions with 'na' produce type."""
        # Arrange
        mock_transaction.produce = None
        session_service.transaction_repo.get_transactions_in_range.return_value = [mock_transaction]

        # Act
        result = await session_service.get_sessions_by_produce_type("na")

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_sessions_by_produce_type_with_time_range(self, session_service, mock_transaction):
        """Test getting sessions by produce type with time range."""
        # Arrange
        from_time = datetime(2024, 1, 1, 0, 0, 0)
        to_time = datetime(2024, 12, 31, 23, 59, 59)
        mock_transaction.produce = "apple"

        session_service.transaction_repo.get_transactions_in_range.return_value = [mock_transaction]

        # Act
        result = await session_service.get_sessions_by_produce_type(
            "apple", from_time=from_time, to_time=to_time
        )

        # Assert
        assert len(result) == 1
        session_service.transaction_repo.get_transactions_in_range.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_sessions_by_produce_type_filters_correctly(self, session_service):
        """Test that produce type filter works correctly."""
        # Arrange
        orange_trans = MagicMock()
        orange_trans.session_id = "session-1"
        orange_trans.produce = "orange"
        orange_trans.direction = "in"

        apple_trans = MagicMock()
        apple_trans.session_id = "session-2"
        apple_trans.produce = "apple"
        apple_trans.direction = "in"

        session_service.transaction_repo.get_transactions_in_range.return_value = [
            orange_trans, apple_trans
        ]

        # Act
        result = await session_service.get_sessions_by_produce_type("orange")

        # Assert
        assert len(result) == 1
        assert result[0].in_transaction.produce == "orange"

    @pytest.mark.asyncio
    async def test_get_sessions_by_produce_type_with_out_direction(self, session_service):
        """Test that produce type handles both IN and OUT directions."""
        # Arrange
        in_trans = MagicMock()
        in_trans.session_id = "session-1"
        in_trans.produce = "orange"
        in_trans.direction = "in"

        out_trans = MagicMock()
        out_trans.session_id = "session-1"
        out_trans.produce = "orange"
        out_trans.direction = "out"

        session_service.transaction_repo.get_transactions_in_range.return_value = [
            in_trans, out_trans
        ]

        # Act
        result = await session_service.get_sessions_by_produce_type("orange")

        # Assert
        assert len(result) == 1
        # Session should have both IN and OUT transactions
        assert result[0].in_transaction == in_trans
        assert result[0].out_transaction == out_trans

    # ========================================================================
    # Test filter_sessions_by_completion_status
    # ========================================================================

    @pytest.mark.asyncio
    async def test_filter_sessions_completed_only(self, session_service):
        """Test filtering for completed sessions only."""
        # Arrange
        in_trans1 = TransactionResponse(
            id="s1", direction="in", truck="T1", bruto=1000, produce="orange", containers=["C1"]
        )
        out_trans1 = TransactionResponse(
            id="s1", direction="out", truck="T1", bruto=800, produce="orange", containers=["C1"]
        )
        completed = SessionPair(
            session_id="session-1",
            in_transaction=in_trans1,
            out_transaction=out_trans1,
            is_complete=True
        )

        in_trans2 = TransactionResponse(
            id="s2", direction="in", truck="T2", bruto=1000, produce="apple", containers=["C2"]
        )
        incomplete = SessionPair(
            session_id="session-2",
            in_transaction=in_trans2,
            out_transaction=None,
            is_complete=False
        )
        sessions = [completed, incomplete]

        # Act
        result = await session_service.filter_sessions_by_completion_status(
            sessions, completed_only=True
        )

        # Assert
        assert len(result) == 1
        assert result[0].is_complete is True

    @pytest.mark.asyncio
    async def test_filter_sessions_incomplete_only(self, session_service):
        """Test filtering for incomplete sessions only."""
        # Arrange
        in_trans1 = TransactionResponse(
            id="s1", direction="in", truck="T1", bruto=1000, produce="orange", containers=["C1"]
        )
        out_trans1 = TransactionResponse(
            id="s1", direction="out", truck="T1", bruto=800, produce="orange", containers=["C1"]
        )
        completed = SessionPair(
            session_id="session-1",
            in_transaction=in_trans1,
            out_transaction=out_trans1,
            is_complete=True
        )

        in_trans2 = TransactionResponse(
            id="s2", direction="in", truck="T2", bruto=1000, produce="apple", containers=["C2"]
        )
        incomplete = SessionPair(
            session_id="session-2",
            in_transaction=in_trans2,
            out_transaction=None,
            is_complete=False
        )
        sessions = [completed, incomplete]

        # Act
        result = await session_service.filter_sessions_by_completion_status(
            sessions, incomplete_only=True
        )

        # Assert
        assert len(result) == 1
        assert result[0].is_complete is False

    @pytest.mark.asyncio
    async def test_filter_sessions_no_filter(self, session_service):
        """Test filtering with no filter returns all sessions."""
        # Arrange
        sessions = [
            SessionPair(session_id="s1", is_complete=True),
            SessionPair(session_id="s2", is_complete=False)
        ]

        # Act
        result = await session_service.filter_sessions_by_completion_status(sessions)

        # Assert
        assert len(result) == 2

    # ========================================================================
    # Test calculate_session_metrics
    # ========================================================================

    @pytest.mark.asyncio
    async def test_calculate_session_metrics_success(self, session_service):
        """Test calculating session metrics."""
        # Arrange
        stats = {
            "total": 10,
            "in": 5,
            "out": 4,
            "none": 1
        }
        session_service.transaction_repo.get_session_statistics.return_value = stats

        in_trans = MagicMock()
        in_trans.session_id = "session-1"
        in_trans.direction = "in"

        out_trans = MagicMock()
        out_trans.session_id = "session-1"
        out_trans.direction = "out"

        session_service.transaction_repo.get_transactions_in_range.return_value = [in_trans, out_trans]

        # Act
        result = await session_service.calculate_session_metrics()

        # Assert
        assert result["total_transactions"] == 10
        assert result["in_transactions"] == 5
        assert result["out_transactions"] == 4
        assert result["total_sessions"] == 1
        assert result["completed_sessions"] == 1
        assert result["incomplete_sessions"] == 0
        assert result["completion_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_calculate_session_metrics_with_incomplete(self, session_service):
        """Test metrics calculation with incomplete sessions."""
        # Arrange
        stats = {"total": 5, "in": 3, "out": 2, "none": 0}
        session_service.transaction_repo.get_session_statistics.return_value = stats

        # Session 1: complete
        in_trans1 = MagicMock()
        in_trans1.session_id = "session-1"
        in_trans1.direction = "in"

        out_trans1 = MagicMock()
        out_trans1.session_id = "session-1"
        out_trans1.direction = "out"

        # Session 2: incomplete (only IN)
        in_trans2 = MagicMock()
        in_trans2.session_id = "session-2"
        in_trans2.direction = "in"

        session_service.transaction_repo.get_transactions_in_range.return_value = [
            in_trans1, out_trans1, in_trans2
        ]

        # Act
        result = await session_service.calculate_session_metrics()

        # Assert
        assert result["total_sessions"] == 2
        assert result["completed_sessions"] == 1
        assert result["incomplete_sessions"] == 1
        assert result["completion_rate"] == 0.5

    @pytest.mark.asyncio
    async def test_calculate_session_metrics_empty(self, session_service):
        """Test metrics calculation with no sessions."""
        # Arrange
        stats = {"total": 0, "in": 0, "out": 0, "none": 0}
        session_service.transaction_repo.get_session_statistics.return_value = stats
        session_service.transaction_repo.get_transactions_in_range.return_value = []

        # Act
        result = await session_service.calculate_session_metrics()

        # Assert
        assert result["total_sessions"] == 0
        assert result["completed_sessions"] == 0
        assert result["incomplete_sessions"] == 0
        assert result["completion_rate"] == 0

    @pytest.mark.asyncio
    async def test_calculate_session_metrics_with_time_range(self, session_service):
        """Test metrics calculation with time range filter."""
        # Arrange
        from_time = datetime(2024, 1, 1, 0, 0, 0)
        to_time = datetime(2024, 12, 31, 23, 59, 59)

        stats = {"total": 2, "in": 1, "out": 1, "none": 0}
        session_service.transaction_repo.get_session_statistics.return_value = stats
        session_service.transaction_repo.get_transactions_in_range.return_value = []

        # Act
        result = await session_service.calculate_session_metrics(from_time, to_time)

        # Assert
        session_service.transaction_repo.get_session_statistics.assert_called_once_with(from_time, to_time)
        assert result["total_transactions"] == 2

    # ========================================================================
    # Test cleanup_abandoned_sessions
    # ========================================================================

    @pytest.mark.asyncio
    async def test_cleanup_abandoned_sessions_found(self, session_service, mock_transaction):
        """Test finding abandoned sessions."""
        # Arrange
        old_transaction = MagicMock()
        old_transaction.session_id = "old-session"
        old_transaction.datetime = datetime.now() - timedelta(hours=48)
        old_transaction.get_display_truck.return_value = "ABC123"
        old_transaction.container_list = ["C001", "C002"]

        session_service.transaction_repo.get_transactions_in_range.return_value = [old_transaction]
        session_service.transaction_repo.get_by_session_and_direction.return_value = None

        # Act
        result = await session_service.cleanup_abandoned_sessions(older_than_hours=24)

        # Assert
        assert result["total_abandoned"] == 1
        assert result["cutoff_hours"] == 24
        assert len(result["abandoned_sessions"]) == 1
        assert result["abandoned_sessions"][0]["session_id"] == "old-session"

    @pytest.mark.asyncio
    async def test_cleanup_abandoned_sessions_none_found(self, session_service):
        """Test cleanup when no abandoned sessions exist."""
        # Arrange
        session_service.transaction_repo.get_transactions_in_range.return_value = []

        # Act
        result = await session_service.cleanup_abandoned_sessions(older_than_hours=24)

        # Assert
        assert result["total_abandoned"] == 0
        assert len(result["abandoned_sessions"]) == 0

    @pytest.mark.asyncio
    async def test_cleanup_abandoned_sessions_excludes_completed(self, session_service):
        """Test that completed sessions are not marked as abandoned."""
        # Arrange
        old_transaction = MagicMock()
        old_transaction.session_id = "old-session"
        old_transaction.datetime = datetime.now() - timedelta(hours=48)

        session_service.transaction_repo.get_transactions_in_range.return_value = [old_transaction]
        # This session has an OUT transaction (completed)
        session_service.transaction_repo.get_by_session_and_direction.return_value = MagicMock()

        # Act
        result = await session_service.cleanup_abandoned_sessions(older_than_hours=24)

        # Assert
        assert result["total_abandoned"] == 0

    @pytest.mark.asyncio
    async def test_cleanup_abandoned_sessions_custom_hours(self, session_service):
        """Test cleanup with custom hours threshold."""
        # Arrange
        session_service.transaction_repo.get_transactions_in_range.return_value = []

        # Act
        result = await session_service.cleanup_abandoned_sessions(older_than_hours=72)

        # Assert
        assert result["cutoff_hours"] == 72

    # ========================================================================
    # Test validate_session_state
    # ========================================================================

    @pytest.mark.asyncio
    async def test_validate_session_state_exists(self, session_service):
        """Test validating session exists."""
        # Arrange
        in_trans = TransactionResponse(
            id="test-session", direction="in", truck="T1", bruto=1000, produce="orange", containers=["C1"]
        )
        session_pair = SessionPair(
            session_id="test-session",
            in_transaction=in_trans,
            is_complete=False
        )

        with patch.object(session_service, 'get_session_details', return_value=session_pair):
            # Act
            is_valid, error = await session_service.validate_session_state(
                "test-session", "exists"
            )

            # Assert
            assert is_valid is True
            assert error is None

    @pytest.mark.asyncio
    async def test_validate_session_state_not_found(self, session_service):
        """Test validating non-existent session."""
        # Arrange
        with patch.object(session_service, 'get_session_details', return_value=None):
            # Act
            is_valid, error = await session_service.validate_session_state(
                "nonexistent", "exists"
            )

            # Assert
            assert is_valid is False
            assert "not found" in error

    @pytest.mark.asyncio
    async def test_validate_session_state_active_valid(self, session_service):
        """Test validating active session state."""
        # Arrange
        in_trans = TransactionResponse(
            id="test-session", direction="in", truck="T1", bruto=1000, produce="orange", containers=["C1"]
        )
        session_pair = SessionPair(
            session_id="test-session",
            in_transaction=in_trans,
            out_transaction=None,
            is_complete=False
        )

        with patch.object(session_service, 'get_session_details', return_value=session_pair):
            # Act
            is_valid, error = await session_service.validate_session_state(
                "test-session", "active"
            )

            # Assert
            assert is_valid is True
            assert error is None

    @pytest.mark.asyncio
    async def test_validate_session_state_active_but_completed(self, session_service):
        """Test validating active state when session is completed."""
        # Arrange
        in_trans = TransactionResponse(
            id="test-session", direction="in", truck="T1", bruto=1000, produce="orange", containers=["C1"]
        )
        out_trans = TransactionResponse(
            id="test-session", direction="out", truck="T1", bruto=800, produce="orange", containers=["C1"]
        )
        session_pair = SessionPair(
            session_id="test-session",
            in_transaction=in_trans,
            out_transaction=out_trans,
            is_complete=True
        )

        with patch.object(session_service, 'get_session_details', return_value=session_pair):
            # Act
            is_valid, error = await session_service.validate_session_state(
                "test-session", "active"
            )

            # Assert
            assert is_valid is False
            assert "already completed" in error

    @pytest.mark.asyncio
    async def test_validate_session_state_completed_valid(self, session_service):
        """Test validating completed session state."""
        # Arrange
        in_trans = TransactionResponse(
            id="test-session", direction="in", truck="T1", bruto=1000, produce="orange", containers=["C1"]
        )
        out_trans = TransactionResponse(
            id="test-session", direction="out", truck="T1", bruto=800, produce="orange", containers=["C1"]
        )
        session_pair = SessionPair(
            session_id="test-session",
            in_transaction=in_trans,
            out_transaction=out_trans,
            is_complete=True
        )

        with patch.object(session_service, 'get_session_details', return_value=session_pair):
            # Act
            is_valid, error = await session_service.validate_session_state(
                "test-session", "completed"
            )

            # Assert
            assert is_valid is True
            assert error is None

    @pytest.mark.asyncio
    async def test_validate_session_state_completed_but_incomplete(self, session_service):
        """Test validating completed state when session is not completed."""
        # Arrange
        in_trans = TransactionResponse(
            id="test-session", direction="in", truck="T1", bruto=1000, produce="orange", containers=["C1"]
        )
        session_pair = SessionPair(
            session_id="test-session",
            in_transaction=in_trans,
            out_transaction=None,
            is_complete=False
        )

        with patch.object(session_service, 'get_session_details', return_value=session_pair):
            # Act
            is_valid, error = await session_service.validate_session_state(
                "test-session", "completed"
            )

            # Assert
            assert is_valid is False
            assert "not completed" in error

    # ========================================================================
    # Test _generate_session_id
    # ========================================================================

    def test_generate_session_id_format(self, session_service):
        """Test that generated session IDs are valid UUIDs."""
        # Act
        session_id = session_service._generate_session_id()

        # Assert
        assert session_id is not None
        # Should be a valid UUID
        uuid_obj = uuid.UUID(session_id)
        assert str(uuid_obj) == session_id

    def test_generate_session_id_unique(self, session_service):
        """Test that generated session IDs are unique."""
        # Act
        id1 = session_service._generate_session_id()
        id2 = session_service._generate_session_id()

        # Assert
        assert id1 != id2
