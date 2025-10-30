"""Tests for ContainerService business logic."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.models.schemas import ContainerWeightData, ContainerWeightInfo
from src.models.database import ContainerRegistered
from src.services.container_service import (
    ContainerService,
    ContainerValidationError,
    DuplicateContainerError
)


class TestContainerService:
    """Test cases for ContainerService."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.delete = AsyncMock()
        return session

    @pytest.fixture
    def container_service(self, mock_session):
        """Create ContainerService instance with mocked dependencies."""
        service = ContainerService(mock_session)
        service.container_repo = AsyncMock()
        return service

    # ========================================================================
    # Test register_container
    # ========================================================================

    @pytest.mark.asyncio
    async def test_register_container_success_new(self, container_service, mock_session):
        """Test successful registration of new container."""
        # Arrange
        container_id = "C001"
        weight = 50
        unit = "kg"

        container_service.container_repo.get_by_id.return_value = None
        mock_container = MagicMock()
        mock_container.container_id = container_id
        mock_container.weight = weight
        container_service.container_repo.create.return_value = mock_container

        # Act
        result, was_updated = await container_service.register_container(
            container_id, weight, unit
        )

        # Assert
        assert was_updated is False
        assert result.container_id == container_id
        container_service.container_repo.create.assert_called_once_with(container_id, weight, unit)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_container_success_update(self, container_service, mock_session):
        """Test successful update of existing container with allow_update=True."""
        # Arrange
        container_id = "C001"
        weight = 60
        unit = "kg"

        existing_container = MagicMock()
        existing_container.container_id = container_id
        existing_container.weight = 50
        container_service.container_repo.get_by_id.return_value = existing_container

        updated_container = MagicMock()
        updated_container.weight = weight
        container_service.container_repo.update_weight.return_value = updated_container

        # Act
        result, was_updated = await container_service.register_container(
            container_id, weight, unit, allow_update=True
        )

        # Assert
        assert was_updated is True
        container_service.container_repo.update_weight.assert_called_once_with(container_id, weight, unit)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_container_duplicate_error(self, container_service):
        """Test duplicate container registration without allow_update."""
        # Arrange
        container_id = "C001"
        existing_container = MagicMock()
        container_service.container_repo.get_by_id.return_value = existing_container

        # Act & Assert
        with pytest.raises(DuplicateContainerError) as exc_info:
            await container_service.register_container(container_id, 50, allow_update=False)

        assert f"Container {container_id} already registered" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_register_container_invalid_id_empty(self, container_service):
        """Test registration with empty container ID."""
        # Act & Assert
        with pytest.raises(ContainerValidationError) as exc_info:
            await container_service.register_container("", 50)

        assert "Container ID cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_register_container_invalid_id_too_long(self, container_service):
        """Test registration with container ID exceeding 15 characters."""
        # Act & Assert
        with pytest.raises(ContainerValidationError) as exc_info:
            await container_service.register_container("C" * 16, 50)

        assert "exceeds 15 characters" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_register_container_invalid_id_special_chars(self, container_service):
        """Test registration with invalid characters in container ID."""
        # Act & Assert
        with pytest.raises(ContainerValidationError) as exc_info:
            await container_service.register_container("C@01#", 50)

        assert "invalid characters" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_register_container_invalid_weight_out_of_range(self, container_service):
        """Test registration with weight out of valid range."""
        # Arrange
        container_service.container_repo.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ContainerValidationError) as exc_info:
            await container_service.register_container("C001", 200000, "kg")

        assert "out of valid range" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_register_container_with_lbs_unit(self, container_service, mock_session):
        """Test registration with lbs unit conversion."""
        # Arrange
        container_id = "C001"
        weight_lbs = 110  # ~50 kg

        container_service.container_repo.get_by_id.return_value = None
        mock_container = MagicMock()
        container_service.container_repo.create.return_value = mock_container

        # Act
        result, was_updated = await container_service.register_container(
            container_id, weight_lbs, "lbs"
        )

        # Assert
        assert was_updated is False
        # Verify that create was called with converted weight (should be ~50 kg)
        call_args = container_service.container_repo.create.call_args
        assert call_args[0][0] == container_id
        assert 45 < call_args[0][1] < 55  # Rough conversion check
        assert call_args[0][2] == "kg"

    # ========================================================================
    # Test batch_register_containers
    # ========================================================================

    @pytest.mark.asyncio
    async def test_batch_register_containers_all_new(self, container_service, mock_session):
        """Test batch registration of all new containers."""
        # Arrange
        containers_data = [
            ContainerWeightData(id="C001", weight=50, unit="kg"),
            ContainerWeightData(id="C002", weight=60, unit="kg"),
            ContainerWeightData(id="C003", weight=55, unit="kg")
        ]

        container_service.container_repo.get_by_id.return_value = None
        mock_container = MagicMock()
        container_service.container_repo.create.return_value = mock_container

        # Act
        results = await container_service.batch_register_containers(containers_data)

        # Assert
        assert results["processed"] == 3
        assert results["updated"] == 0
        assert results["skipped"] == 0
        assert len(results["errors"]) == 0
        assert len(results["successful_containers"]) == 3
        assert mock_session.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_batch_register_containers_with_updates(self, container_service, mock_session):
        """Test batch registration with updates allowed."""
        # Arrange
        containers_data = [
            ContainerWeightData(id="C001", weight=50, unit="kg"),
            ContainerWeightData(id="C002", weight=60, unit="kg"),
        ]

        # Mock C001 exists, C002 doesn't
        def get_by_id_side_effect(container_id):
            if container_id == "C001":
                return MagicMock()
            return None

        container_service.container_repo.get_by_id.side_effect = get_by_id_side_effect
        container_service.container_repo.update_weight.return_value = MagicMock()
        container_service.container_repo.create.return_value = MagicMock()

        # Act
        results = await container_service.batch_register_containers(
            containers_data, allow_updates=True
        )

        # Assert
        assert results["processed"] == 1
        assert results["updated"] == 1
        assert results["skipped"] == 0
        assert len(results["successful_containers"]) == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_register_containers_skip_duplicates(self, container_service, mock_session):
        """Test batch registration with skip_duplicates enabled."""
        # Arrange
        containers_data = [
            ContainerWeightData(id="C001", weight=50, unit="kg"),
            ContainerWeightData(id="C002", weight=60, unit="kg"),
        ]

        # Mock C001 exists
        def get_by_id_side_effect(container_id):
            if container_id == "C001":
                return MagicMock()
            return None

        container_service.container_repo.get_by_id.side_effect = get_by_id_side_effect
        container_service.container_repo.create.return_value = MagicMock()

        # Act
        results = await container_service.batch_register_containers(
            containers_data, allow_updates=False, skip_duplicates=True
        )

        # Assert
        assert results["processed"] == 1
        assert results["updated"] == 0
        assert results["skipped"] == 1
        assert len(results["successful_containers"]) == 1

    @pytest.mark.asyncio
    async def test_batch_register_containers_duplicate_error(self, container_service):
        """Test batch registration with duplicate error."""
        # Arrange
        containers_data = [
            ContainerWeightData(id="C001", weight=50, unit="kg"),
        ]

        container_service.container_repo.get_by_id.return_value = MagicMock()

        # Act
        results = await container_service.batch_register_containers(
            containers_data, allow_updates=False, skip_duplicates=False
        )

        # Assert
        assert results["processed"] == 0
        assert results["updated"] == 0
        assert len(results["errors"]) == 1
        assert "C001" in results["errors"][0]
        assert len(results["failed_containers"]) == 1

    @pytest.mark.asyncio
    async def test_batch_register_containers_validation_error(self, container_service):
        """Test batch registration with validation errors."""
        # Arrange - Create a container with valid Pydantic schema but invalid service logic
        # We'll use a MagicMock to bypass Pydantic but still trigger service validation
        mock_container_data = MagicMock()
        mock_container_data.id = "C" * 16  # Too long, triggers service validation
        mock_container_data.weight = 50
        mock_container_data.unit = "kg"

        containers_data = [mock_container_data]

        # Act
        results = await container_service.batch_register_containers(containers_data)

        # Assert
        assert len(results["errors"]) == 1
        assert len(results["failed_containers"]) == 1

    @pytest.mark.asyncio
    async def test_batch_register_containers_no_commit_if_all_fail(self, container_service, mock_session):
        """Test no commit when all containers fail."""
        # Arrange - Use MagicMock to bypass Pydantic and trigger service-level validation
        mock_container_data = MagicMock()
        mock_container_data.id = ""  # Empty, triggers service validation
        mock_container_data.weight = 50
        mock_container_data.unit = "kg"

        containers_data = [mock_container_data]

        # Act
        results = await container_service.batch_register_containers(containers_data)

        # Assert
        mock_session.commit.assert_not_called()

    # ========================================================================
    # Test get_container_weight
    # ========================================================================

    @pytest.mark.asyncio
    async def test_get_container_weight_known(self, container_service):
        """Test getting weight of known container."""
        # Arrange
        container_id = "C001"
        mock_container = MagicMock()
        mock_container.weight = 50
        mock_container.unit = "kg"
        container_service.container_repo.get_by_id.return_value = mock_container

        # Act
        result = await container_service.get_container_weight(container_id)

        # Assert
        assert result.container_id == container_id
        assert result.weight == 50
        assert result.unit == "kg"
        assert result.is_known is True

    @pytest.mark.asyncio
    async def test_get_container_weight_unknown(self, container_service):
        """Test getting weight of unknown container."""
        # Arrange
        container_id = "C999"
        container_service.container_repo.get_by_id.return_value = None

        # Act
        result = await container_service.get_container_weight(container_id)

        # Assert
        assert result.container_id == container_id
        assert result.weight is None
        assert result.is_known is False

    # ========================================================================
    # Test get_multiple_container_weights
    # ========================================================================

    @pytest.mark.asyncio
    async def test_get_multiple_container_weights(self, container_service):
        """Test getting weights for multiple containers."""
        # Arrange
        container_ids = ["C001", "C002"]
        mock_weights = [
            ContainerWeightInfo(container_id="C001", weight=50, unit="kg", is_known=True),
            ContainerWeightInfo(container_id="C002", weight=60, unit="kg", is_known=True)
        ]
        container_service.container_repo.get_container_weight_info.return_value = mock_weights

        # Act
        results = await container_service.get_multiple_container_weights(container_ids)

        # Assert
        assert len(results) == 2
        container_service.container_repo.get_container_weight_info.assert_called_once_with(container_ids)

    # ========================================================================
    # Test update_container_weight
    # ========================================================================

    @pytest.mark.asyncio
    async def test_update_container_weight_success(self, container_service, mock_session):
        """Test successful container weight update."""
        # Arrange
        container_id = "C001"
        new_weight = 70
        mock_container = MagicMock()
        container_service.container_repo.update_weight.return_value = mock_container

        # Act
        result = await container_service.update_container_weight(container_id, new_weight, "kg")

        # Assert
        assert result is not None
        container_service.container_repo.update_weight.assert_called_once_with(container_id, new_weight, "kg")
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_container_weight_not_found(self, container_service, mock_session):
        """Test updating non-existent container."""
        # Arrange
        container_service.container_repo.update_weight.return_value = None

        # Act
        result = await container_service.update_container_weight("C999", 50, "kg")

        # Assert
        assert result is None
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_container_weight_invalid_id(self, container_service):
        """Test updating with invalid container ID."""
        # Act & Assert
        with pytest.raises(ContainerValidationError):
            await container_service.update_container_weight("", 50, "kg")

    @pytest.mark.asyncio
    async def test_update_container_weight_invalid_weight(self, container_service):
        """Test updating with invalid weight."""
        # Act & Assert
        with pytest.raises(ContainerValidationError):
            await container_service.update_container_weight("C001", 200000, "kg")

    # ========================================================================
    # Test find_unknown_containers
    # ========================================================================

    @pytest.mark.asyncio
    async def test_find_unknown_containers_no_filter(self, container_service):
        """Test finding unknown containers without time filter."""
        # Arrange
        unknown = ["C999", "C888"]
        container_service.container_repo.get_unknown_containers.return_value = unknown

        # Act
        result = await container_service.find_unknown_containers()

        # Assert
        assert result == unknown
        container_service.container_repo.get_unknown_containers.assert_called_once_with(None, None)

    @pytest.mark.asyncio
    async def test_find_unknown_containers_with_filter(self, container_service):
        """Test finding unknown containers with time filter."""
        # Arrange
        from_time = datetime(2024, 1, 1, 0, 0, 0)
        to_time = datetime(2024, 12, 31, 23, 59, 59)
        unknown = ["C999"]
        container_service.container_repo.get_unknown_containers.return_value = unknown

        # Act
        result = await container_service.find_unknown_containers(from_time, to_time)

        # Assert
        assert result == unknown
        container_service.container_repo.get_unknown_containers.assert_called_once_with(from_time, to_time)

    # ========================================================================
    # Test get_all_registered_containers
    # ========================================================================

    @pytest.mark.asyncio
    async def test_get_all_registered_containers(self, container_service):
        """Test getting all registered containers."""
        # Arrange
        mock_containers = [MagicMock(), MagicMock()]
        container_service.container_repo.get_all_with_weights.return_value = mock_containers

        # Act
        result = await container_service.get_all_registered_containers()

        # Assert
        assert len(result) == 2
        container_service.container_repo.get_all_with_weights.assert_called_once()

    # ========================================================================
    # Test validate_containers_for_weighing
    # ========================================================================

    @pytest.mark.asyncio
    async def test_validate_containers_all_known(self, container_service):
        """Test validation with all containers known."""
        # Arrange
        container_ids = ["C001", "C002"]
        mock_info = [
            ContainerWeightInfo(container_id="C001", weight=50, unit="kg", is_known=True),
            ContainerWeightInfo(container_id="C002", weight=60, unit="kg", is_known=True)
        ]
        container_service.container_repo.get_container_weight_info.return_value = mock_info

        # Act
        all_known, known, unknown = await container_service.validate_containers_for_weighing(container_ids)

        # Assert
        assert all_known is True
        assert len(known) == 2
        assert len(unknown) == 0

    @pytest.mark.asyncio
    async def test_validate_containers_some_unknown(self, container_service):
        """Test validation with some unknown containers."""
        # Arrange
        container_ids = ["C001", "C999"]
        mock_info = [
            ContainerWeightInfo(container_id="C001", weight=50, unit="kg", is_known=True),
            ContainerWeightInfo(container_id="C999", weight=None, unit="kg", is_known=False)
        ]
        container_service.container_repo.get_container_weight_info.return_value = mock_info

        # Act
        all_known, known, unknown = await container_service.validate_containers_for_weighing(container_ids)

        # Assert
        assert all_known is False
        assert len(known) == 1
        assert len(unknown) == 1
        assert "C001" in known
        assert "C999" in unknown

    # ========================================================================
    # Test get_container_total_tare
    # ========================================================================

    @pytest.mark.asyncio
    async def test_get_container_total_tare_all_known(self, container_service):
        """Test calculating total tare with all known containers."""
        # Arrange
        container_ids = ["C001", "C002"]
        mock_info = [
            ContainerWeightInfo(container_id="C001", weight=50, unit="kg", is_known=True),
            ContainerWeightInfo(container_id="C002", weight=60, unit="kg", is_known=True)
        ]
        container_service.container_repo.get_container_weight_info.return_value = mock_info

        # Act
        total, unknown = await container_service.get_container_total_tare(container_ids)

        # Assert
        assert total == 110
        assert len(unknown) == 0

    @pytest.mark.asyncio
    async def test_get_container_total_tare_with_unknown(self, container_service):
        """Test calculating total tare with unknown containers."""
        # Arrange
        container_ids = ["C001", "C999"]
        mock_info = [
            ContainerWeightInfo(container_id="C001", weight=50, unit="kg", is_known=True),
            ContainerWeightInfo(container_id="C999", weight=None, unit="kg", is_known=False)
        ]
        container_service.container_repo.get_container_weight_info.return_value = mock_info

        # Act
        total, unknown = await container_service.get_container_total_tare(container_ids)

        # Assert
        assert total is None
        assert "C999" in unknown

    # ========================================================================
    # Test delete_container
    # ========================================================================

    @pytest.mark.asyncio
    async def test_delete_container_success(self, container_service, mock_session):
        """Test successful container deletion."""
        # Arrange
        container_id = "C001"
        mock_container = MagicMock()
        container_service.container_repo.get_by_id.return_value = mock_container

        # Act
        result = await container_service.delete_container(container_id)

        # Assert
        assert result is True
        mock_session.delete.assert_called_once_with(mock_container)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_container_not_found(self, container_service, mock_session):
        """Test deleting non-existent container."""
        # Arrange
        container_service.container_repo.get_by_id.return_value = None

        # Act
        result = await container_service.delete_container("C999")

        # Assert
        assert result is False
        mock_session.delete.assert_not_called()
        mock_session.commit.assert_not_called()

    # ========================================================================
    # Test get_container_usage_stats
    # ========================================================================

    @pytest.mark.asyncio
    async def test_get_container_usage_stats_registered(self, container_service, mock_session):
        """Test getting usage stats for registered container."""
        # Arrange
        container_id = "C001"

        # Mock transaction repo
        from src.models.repositories import TransactionRepository
        mock_transaction_repo = AsyncMock()
        mock_transaction_repo.get_sessions_with_container.return_value = ["session1", "session2"]

        # Patch the TransactionRepository instantiation
        original_init = TransactionRepository.__init__

        def mock_init(self, session):
            self.session = session
            self.get_sessions_with_container = mock_transaction_repo.get_sessions_with_container

        TransactionRepository.__init__ = mock_init

        # Mock container info
        mock_container_info = ContainerWeightInfo(
            container_id=container_id,
            weight=50,
            unit="kg",
            is_known=True
        )
        container_service.get_container_weight = AsyncMock(return_value=mock_container_info)

        # Act
        result = await container_service.get_container_usage_stats(container_id)

        # Assert
        assert result["container_id"] == container_id
        assert result["is_registered"] is True
        assert result["weight"] == 50
        assert result["unit"] == "kg"
        assert result["usage_count"] == 2
        assert len(result["session_ids"]) == 2

        # Restore original
        TransactionRepository.__init__ = original_init

    @pytest.mark.asyncio
    async def test_get_container_usage_stats_not_registered(self, container_service, mock_session):
        """Test getting usage stats for unregistered container."""
        # Arrange
        container_id = "C999"

        # Mock transaction repo
        from src.models.repositories import TransactionRepository
        mock_transaction_repo = AsyncMock()
        mock_transaction_repo.get_sessions_with_container.return_value = []

        # Patch the TransactionRepository instantiation
        original_init = TransactionRepository.__init__

        def mock_init(self, session):
            self.session = session
            self.get_sessions_with_container = mock_transaction_repo.get_sessions_with_container

        TransactionRepository.__init__ = mock_init

        # Mock container info for unknown container
        mock_container_info = ContainerWeightInfo(
            container_id=container_id,
            weight=None,
            unit="kg",
            is_known=False
        )
        container_service.get_container_weight = AsyncMock(return_value=mock_container_info)

        # Act
        result = await container_service.get_container_usage_stats(container_id)

        # Assert
        assert result["container_id"] == container_id
        assert result["is_registered"] is False
        assert result["weight"] is None
        assert result["usage_count"] == 0

        # Restore original
        TransactionRepository.__init__ = original_init

    # ========================================================================
    # Test _validate_container_id
    # ========================================================================

    @pytest.mark.asyncio
    async def test_validate_container_id_valid(self, container_service):
        """Test validation with valid container IDs."""
        # These should not raise exceptions
        container_service._validate_container_id("C001")
        container_service._validate_container_id("ABC-123")
        container_service._validate_container_id("C_001")
        container_service._validate_container_id("123")

    @pytest.mark.asyncio
    async def test_validate_container_id_whitespace_only(self, container_service):
        """Test validation with whitespace-only ID."""
        with pytest.raises(ContainerValidationError) as exc_info:
            container_service._validate_container_id("   ")

        assert "cannot be empty" in str(exc_info.value)

    # ========================================================================
    # Test _validate_container_data
    # ========================================================================

    @pytest.mark.asyncio
    async def test_validate_container_data_valid(self, container_service):
        """Test validation with valid container data."""
        # Arrange
        data = ContainerWeightData(id="C001", weight=50, unit="kg")

        # Act - should not raise
        container_service._validate_container_data(data)

    @pytest.mark.asyncio
    async def test_validate_container_data_negative_weight(self, container_service):
        """Test validation with negative weight."""
        # Note: Pydantic should catch this, but if it gets through...
        # We'll test the service logic
        data = MagicMock()
        data.id = "C001"
        data.weight = -50
        data.unit = "kg"

        with pytest.raises(ContainerValidationError) as exc_info:
            container_service._validate_container_data(data)

        assert "must be positive" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_container_data_zero_weight(self, container_service):
        """Test validation with zero weight."""
        data = MagicMock()
        data.id = "C001"
        data.weight = 0
        data.unit = "kg"

        with pytest.raises(ContainerValidationError) as exc_info:
            container_service._validate_container_data(data)

        assert "must be positive" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_container_data_invalid_unit(self, container_service):
        """Test validation with invalid unit."""
        data = MagicMock()
        data.id = "C001"
        data.weight = 50
        data.unit = "tons"

        with pytest.raises(ContainerValidationError) as exc_info:
            container_service._validate_container_data(data)

        assert "Invalid unit" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_container_data_weight_out_of_range(self, container_service):
        """Test validation with weight out of range."""
        data = MagicMock()
        data.id = "C001"
        data.weight = 200000
        data.unit = "kg"

        with pytest.raises(ContainerValidationError) as exc_info:
            container_service._validate_container_data(data)

        assert "out of valid range" in str(exc_info.value)
