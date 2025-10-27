"""Tests for Pydantic schemas."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.models.schemas import (
    WeightRequest,
    BatchWeightRequest,
    ContainerWeightData,
    WeightQueryParams,
    ItemQueryParams,
    WeightResponse,
    BatchUploadResponse,
    TransactionResponse,
    ItemResponse,
    SessionResponse,
    HealthResponse,
    ErrorResponse,
    ContainerWeightInfo,
    SessionPair
)


# ============================================================================
# Request Schema Tests
# ============================================================================

def test_weight_request_valid():
    """Test valid WeightRequest creation."""
    request = WeightRequest(
        direction="in",
        truck="ABC-123",
        containers="CONT001,CONT002",
        weight=5000,
        unit="kg",
        force=False,
        produce="apples"
    )
    
    assert request.direction == "in"
    assert request.truck == "ABC-123"
    assert request.containers == "CONT001,CONT002"
    assert request.weight == 5000
    assert request.unit == "kg"
    assert request.force is False
    assert request.produce == "apples"


def test_weight_request_defaults():
    """Test WeightRequest with default values."""
    request = WeightRequest(
        direction="out",
        containers="CONT001",
        weight=4500
    )
    
    assert request.truck == "na"
    assert request.unit == "kg"
    assert request.force is False
    assert request.produce == "na"


def test_weight_request_validation_errors():
    """Test WeightRequest validation failures."""
    # Invalid direction
    with pytest.raises(ValidationError):
        WeightRequest(
            direction="invalid",
            containers="CONT001",
            weight=5000
        )
    
    # Empty containers
    with pytest.raises(ValidationError):
        WeightRequest(
            direction="in",
            containers="",
            weight=5000
        )
    
    # Invalid weight (zero)
    with pytest.raises(ValidationError):
        WeightRequest(
            direction="in",
            containers="CONT001",
            weight=0
        )
    
    # Invalid unit
    with pytest.raises(ValidationError):
        WeightRequest(
            direction="in",
            containers="CONT001",
            weight=5000,
            unit="invalid"
        )


def test_container_validation():
    """Test container ID validation."""
    # Valid containers
    request = WeightRequest(
        direction="in",
        containers="CONT001,CONT-002,CONT_003",
        weight=5000
    )
    assert request.containers == "CONT001,CONT-002,CONT_003"
    
    # Container too long
    with pytest.raises(ValidationError):
        WeightRequest(
            direction="in",
            containers="VERYLONGCONTAINERID123",  # > 15 chars
            weight=5000
        )
    
    # Invalid characters
    with pytest.raises(ValidationError):
        WeightRequest(
            direction="in",
            containers="CONT@001",  # Invalid character
            weight=5000
        )


def test_truck_validation():
    """Test truck license validation."""
    # Valid truck
    request = WeightRequest(
        direction="in",
        truck="ABC-123",
        containers="CONT001",
        weight=5000
    )
    assert request.truck == "ABC-123"
    
    # Truck too long
    with pytest.raises(ValidationError):
        WeightRequest(
            direction="in",
            truck="VERYLONGTRUCKLICENSEPLATE123",  # > 20 chars
            containers="CONT001",
            weight=5000
        )


def test_batch_weight_request():
    """Test BatchWeightRequest validation."""
    # Valid CSV file
    request = BatchWeightRequest(file="containers.csv")
    assert request.file == "containers.csv"
    
    # Valid JSON file
    request = BatchWeightRequest(file="containers.json")
    assert request.file == "containers.json"
    
    # Invalid extension
    with pytest.raises(ValidationError):
        BatchWeightRequest(file="containers.txt")
    
    # Path traversal attempt
    with pytest.raises(ValidationError):
        BatchWeightRequest(file="../../../etc/passwd")


def test_container_weight_data():
    """Test ContainerWeightData validation."""
    data = ContainerWeightData(
        id="CONT001",
        weight=1000,
        unit="kg"
    )
    
    assert data.id == "CONT001"
    assert data.weight == 1000
    assert data.unit == "kg"
    
    # Invalid weight
    with pytest.raises(ValidationError):
        ContainerWeightData(id="CONT001", weight=-100)


def test_query_params_validation():
    """Test query parameter validation."""
    # Valid datetime
    params = WeightQueryParams(
        from_time="20240115120000",
        to_time="20240115180000",
        filter="in,out"
    )
    
    assert params.from_time == "20240115120000"
    assert params.to_time == "20240115180000"
    assert params.filter == "in,out"
    
    # Invalid datetime format
    with pytest.raises(ValidationError):
        WeightQueryParams(from_time="2024-01-15")
    
    # Invalid filter
    with pytest.raises(ValidationError):
        WeightQueryParams(filter="invalid")


# ============================================================================
# Response Schema Tests
# ============================================================================

def test_weight_response():
    """Test WeightResponse creation."""
    response = WeightResponse(
        id="session-123",
        session_id="session-123",
        direction="out",
        truck="ABC-123",
        bruto=5000,
        gross_weight=5000,
        truck_tara=500,
        neto=4000,
        net_weight=4000
    )

    assert response.id == "session-123"
    assert response.session_id == "session-123"
    assert response.direction == "out"
    assert response.truck == "ABC-123"
    assert response.bruto == 5000
    assert response.gross_weight == 5000
    assert response.truck_tara == 500
    assert response.neto == 4000
    assert response.net_weight == 4000


def test_batch_upload_response():
    """Test BatchUploadResponse creation."""
    response = BatchUploadResponse(
        message="Processed 10 containers",
        processed_count=10,
        skipped_count=2,
        errors=["Container CONT001 already exists"]
    )
    
    assert response.message == "Processed 10 containers"
    assert response.processed_count == 10
    assert response.skipped_count == 2
    assert len(response.errors) == 1


def test_transaction_response():
    """Test TransactionResponse creation."""
    response = TransactionResponse(
        id="session-123",
        direction="in",
        bruto=5000,
        neto="na",
        produce="apples",
        containers=["CONT001", "CONT002"]
    )
    
    assert response.id == "session-123"
    assert response.direction == "in"
    assert response.bruto == 5000
    assert response.neto == "na"
    assert response.produce == "apples"
    assert response.containers == ["CONT001", "CONT002"]


def test_health_response():
    """Test HealthResponse creation."""
    now = datetime.now()
    response = HealthResponse(
        status="OK",
        database="Connected",
        timestamp=now
    )
    
    assert response.status == "OK"
    assert response.database == "Connected"
    assert response.timestamp == now


def test_error_response():
    """Test ErrorResponse creation."""
    response = ErrorResponse(
        error="VALIDATION_ERROR",
        message="Invalid input data",
        code="VAL_001"
    )
    
    assert response.error == "VALIDATION_ERROR"
    assert response.message == "Invalid input data"
    assert response.code == "VAL_001"
    assert isinstance(response.timestamp, datetime)


# ============================================================================
# Internal Schema Tests
# ============================================================================

def test_container_weight_info():
    """Test ContainerWeightInfo schema."""
    # Known weight
    info = ContainerWeightInfo(
        container_id="CONT001",
        weight=1000,
        unit="kg",
        is_known=True
    )
    
    assert info.container_id == "CONT001"
    assert info.weight == 1000
    assert info.unit == "kg"
    assert info.is_known is True
    assert info.weight_in_kg == 1000
    
    # Weight in lbs
    info_lbs = ContainerWeightInfo(
        container_id="CONT002",
        weight=2205,
        unit="lbs",
        is_known=True
    )
    
    assert info_lbs.weight_in_kg == 1000  # Converted to kg
    
    # Unknown weight
    info_unknown = ContainerWeightInfo(
        container_id="CONT003",
        weight=None,
        unit="kg",
        is_known=False
    )
    
    assert info_unknown.weight_in_kg is None


def test_session_pair():
    """Test SessionPair schema."""
    from src.models.schemas import TransactionResponse
    
    pair = SessionPair(session_id="session-123")
    
    assert pair.session_id == "session-123"
    assert pair.in_transaction is None
    assert pair.out_transaction is None
    assert pair.is_complete is False
    assert pair.has_both_transactions is False
    
    # Add transactions
    pair.in_transaction = TransactionResponse(
        id="session-123",
        direction="in",
        bruto=5000,
        neto="na",
        produce="apples",
        containers=["CONT001"]
    )
    
    pair.out_transaction = TransactionResponse(
        id="session-123",
        direction="out",
        bruto=4500,
        neto=4000,
        produce="apples",
        containers=["CONT001"]
    )
    
    assert pair.has_both_transactions is True


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_datetime_validation_edge_cases():
    """Test datetime validation edge cases."""
    # Valid leap year date
    params = WeightQueryParams(from_time="20240229120000")
    assert params.from_time == "20240229120000"
    
    # Invalid date (February 30th)
    with pytest.raises(ValidationError):
        WeightQueryParams(from_time="20240230120000")
    
    # Invalid time (25 hours)
    with pytest.raises(ValidationError):
        WeightQueryParams(from_time="20240215250000")


def test_weight_request_container_edge_cases():
    """Test container validation edge cases."""
    # Whitespace handling
    request = WeightRequest(
        direction="in",
        containers=" CONT001 , CONT002 ",
        weight=5000
    )
    assert request.containers == " CONT001 , CONT002 "
    
    # Single container
    request = WeightRequest(
        direction="in",
        containers="CONT001",
        weight=5000
    )
    assert request.containers == "CONT001"