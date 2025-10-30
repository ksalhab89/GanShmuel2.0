"""Tests for WeightService business logic."""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from pydantic import ValidationError

from src.models.schemas import WeightRequest, WeightResponse
from src.services.weight_service import WeightService
from src.utils.exceptions import (
    WeighingSequenceError,
    InvalidWeightError,
    ContainerNotFoundError
)


class TestWeightService:
    """Test cases for WeightService."""
    
    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session
    
    @pytest.fixture
    def weight_service(self, mock_session):
        """Create WeightService instance with mocked dependencies."""
        service = WeightService(mock_session)
        
        # Mock repositories
        service.container_repo = AsyncMock()
        service.transaction_repo = AsyncMock()
        service.session_repo = AsyncMock()
        
        return service
    
    @pytest.mark.asyncio
    async def test_record_weight_in_direction_success(self, weight_service):
        """Test successful IN direction weight recording."""
        # Arrange
        request = WeightRequest(
            direction="in",
            truck="ABC123",
            containers="C001,C002",
            weight=5000,
            unit="kg",
            produce="apples"
        )
        
        # Mock no existing IN transaction
        weight_service.transaction_repo.find_matching_in_transaction.return_value = None
        
        # Mock transaction creation
        mock_transaction = MagicMock()
        mock_transaction.session_id = str(uuid.uuid4())
        weight_service.transaction_repo.create.return_value = mock_transaction
        
        # Act
        response, error = await weight_service.record_weight(request)
        
        # Assert
        assert error is None
        assert isinstance(response, WeightResponse)
        assert response.truck == "ABC123"
        assert response.bruto == 5000
        assert response.truck_tara is None
        assert response.neto == "na"  # IN direction doesn't have net weight yet
        
        # Verify transaction was created
        weight_service.transaction_repo.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_record_weight_in_direction_duplicate_without_force(self, weight_service):
        """Test IN direction with existing transaction and no force flag."""
        # Arrange
        request = WeightRequest(
            direction="in",
            truck="ABC123", 
            containers="C001,C002",
            weight=5000,
            force=False
        )
        
        # Mock existing IN transaction
        mock_existing = MagicMock()
        weight_service.transaction_repo.find_matching_in_transaction.return_value = mock_existing
        
        # Act & Assert
        with pytest.raises(WeighingSequenceError):
            await weight_service.record_weight(request)
    
    @pytest.mark.asyncio
    async def test_record_weight_out_direction_success(self, weight_service):
        """Test successful OUT direction weight recording."""
        # Arrange
        request = WeightRequest(
            direction="out",
            truck="ABC123",
            containers="C001,C002", 
            weight=4500,
            unit="kg"
        )
        
        # Mock matching IN transaction
        mock_in_transaction = MagicMock()
        mock_in_transaction.session_id = str(uuid.uuid4())
        mock_in_transaction.bruto = 5000
        weight_service.transaction_repo.find_matching_in_transaction.return_value = mock_in_transaction
        
        # Mock container weights
        from src.models.schemas import ContainerWeightInfo
        container_info = [
            ContainerWeightInfo(container_id="C001", weight=50, unit="kg", is_known=True),
            ContainerWeightInfo(container_id="C002", weight=60, unit="kg", is_known=True)
        ]
        weight_service.container_repo.get_container_weight_info.return_value = container_info
        
        # Mock transaction creation and updates
        mock_out_transaction = MagicMock()
        weight_service.transaction_repo.create.return_value = mock_out_transaction
        weight_service.transaction_repo.update_out_transaction = AsyncMock()
        
        # Act
        response, error = await weight_service.record_weight(request)
        
        # Assert
        assert error is None
        assert isinstance(response, WeightResponse)
        assert response.bruto == 4500
        assert response.truck_tara is not None
        assert response.neto is not None
        
        # Verify calculations were performed
        weight_service.transaction_repo.update_out_transaction.assert_called()
    
    @pytest.mark.asyncio
    async def test_record_weight_out_direction_no_matching_in(self, weight_service):
        """Test OUT direction with no matching IN transaction."""
        # Arrange
        request = WeightRequest(
            direction="out",
            truck="ABC123",
            containers="C001,C002",
            weight=4500,
            force=False
        )
        
        # Mock no matching IN transaction
        weight_service.transaction_repo.find_matching_in_transaction.return_value = None
        
        # Act & Assert
        with pytest.raises(WeighingSequenceError):
            await weight_service.record_weight(request)
    
    @pytest.mark.asyncio
    async def test_record_weight_out_direction_unknown_containers(self, weight_service):
        """Test OUT direction with unknown containers."""
        # Arrange
        request = WeightRequest(
            direction="out",
            truck="ABC123",
            containers="C001,C999",  # C999 is unknown
            weight=4500
        )
        
        # Mock matching IN transaction
        mock_in_transaction = MagicMock()
        weight_service.transaction_repo.find_matching_in_transaction.return_value = mock_in_transaction
        
        # Mock container weights with unknown container
        from src.models.schemas import ContainerWeightInfo
        container_info = [
            ContainerWeightInfo(container_id="C001", weight=50, unit="kg", is_known=True),
            ContainerWeightInfo(container_id="C999", weight=None, unit="kg", is_known=False)
        ]
        weight_service.container_repo.get_container_weight_info.return_value = container_info
        
        # Act & Assert
        with pytest.raises(ContainerNotFoundError):
            await weight_service.record_weight(request)
    
    @pytest.mark.asyncio
    async def test_record_weight_none_direction(self, weight_service):
        """Test NONE direction weight recording."""
        # Arrange
        request = WeightRequest(
            direction="none",
            truck="ABC123",
            containers="C001",
            weight=1000
        )
        
        # Mock transaction creation
        mock_transaction = MagicMock()
        mock_transaction.session_id = str(uuid.uuid4())
        weight_service.transaction_repo.create.return_value = mock_transaction
        
        # Act
        response, error = await weight_service.record_weight(request)
        
        # Assert
        assert error is None
        assert isinstance(response, WeightResponse)
        assert response.bruto == 1000
        assert response.truck_tara is None
        assert response.neto == "na"  # NONE transactions don't calculate net weight
    
    @pytest.mark.asyncio
    async def test_record_weight_invalid_weight_range(self, weight_service):
        """Test weight recording with invalid weight range."""
        # Arrange
        request = WeightRequest(
            direction="in",
            truck="ABC123",
            containers="C001",
            weight=200000,  # Too heavy
            unit="kg"
        )
        
        # Act & Assert
        with pytest.raises(InvalidWeightError):
            await weight_service.record_weight(request)
    
    @pytest.mark.asyncio
    async def test_record_weight_empty_containers(self, weight_service):
        """Test weight recording with empty container list."""
        # Act & Assert - Pydantic validation should catch this before service layer
        with pytest.raises(ValidationError):
            request = WeightRequest(
                direction="in",
                truck="ABC123",
                containers="",  # Empty
                weight=5000
            )
    
    @pytest.mark.asyncio
    async def test_validate_weighing_sequence_valid_in(self, weight_service):
        """Test weighing sequence validation for valid IN."""
        # Arrange
        weight_service.transaction_repo.find_matching_in_transaction.return_value = None
        
        # Act
        is_valid, error = await weight_service.validate_weighing_sequence(
            "in", "ABC123", ["C001", "C002"]
        )
        
        # Assert
        assert is_valid is True
        assert error is None
    
    @pytest.mark.asyncio
    async def test_validate_weighing_sequence_invalid_out(self, weight_service):
        """Test weighing sequence validation for invalid OUT."""
        # Arrange
        weight_service.transaction_repo.find_matching_in_transaction.return_value = None
        
        # Act
        is_valid, error = await weight_service.validate_weighing_sequence(
            "out", "ABC123", ["C001", "C002"]
        )
        
        # Assert
        assert is_valid is False
        assert "No matching IN transaction found" in error
    
    @pytest.mark.asyncio
    async def test_calculate_net_weight_success(self, weight_service):
        """Test net weight calculation with valid data."""
        # Arrange
        from src.models.schemas import ContainerWeightInfo
        container_info = [
            ContainerWeightInfo(container_id="C001", weight=50, unit="kg", is_known=True),
            ContainerWeightInfo(container_id="C002", weight=60, unit="kg", is_known=True)
        ]
        weight_service.container_repo.get_container_weight_info.return_value = container_info
        
        # Act
        truck_tara, neto, error = await weight_service.calculate_net_weight(
            bruto_in=5000,
            bruto_out=4500, 
            container_ids=["C001", "C002"]
        )
        
        # Assert
        assert error is None
        assert truck_tara is not None
        assert neto is not None
        assert truck_tara >= 0
        assert neto >= 0
    
    @pytest.mark.asyncio
    async def test_calculate_net_weight_unknown_containers(self, weight_service):
        """Test net weight calculation with unknown containers."""
        # Arrange
        from src.models.schemas import ContainerWeightInfo
        container_info = [
            ContainerWeightInfo(container_id="C001", weight=50, unit="kg", is_known=True),
            ContainerWeightInfo(container_id="C999", weight=None, unit="kg", is_known=False)
        ]
        weight_service.container_repo.get_container_weight_info.return_value = container_info
        
        # Act
        truck_tara, neto, error = await weight_service.calculate_net_weight(
            bruto_in=5000,
            bruto_out=4500,
            container_ids=["C001", "C999"]
        )
        
        # Assert
        assert truck_tara is None
        assert neto is None
        assert "Unknown container weights" in error
    
    @pytest.mark.asyncio
    async def test_generate_session(self, weight_service):
        """Test session ID generation."""
        # Act
        session_id = await weight_service.generate_session()
        
        # Assert
        assert session_id is not None
        assert len(session_id) > 0
        # Should be valid UUID format
        uuid.UUID(session_id)  # Will raise ValueError if invalid