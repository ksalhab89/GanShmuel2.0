"""Tests for database models."""

import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import ContainerRegistered, Transaction


# ============================================================================
# ContainerRegistered Model Tests
# ============================================================================

def test_container_registered_creation():
    """Test ContainerRegistered model creation."""
    container = ContainerRegistered(
        container_id="TEST001",
        weight=1000,
        unit="kg"
    )
    
    assert container.container_id == "TEST001"
    assert container.weight == 1000
    assert container.unit == "kg"


def test_container_weight_in_kg_property():
    """Test weight_in_kg property conversion."""
    # Test kg weight
    container_kg = ContainerRegistered(
        container_id="TEST001",
        weight=1000,
        unit="kg"
    )
    assert container_kg.weight_in_kg == 1000
    
    # Test lbs weight
    container_lbs = ContainerRegistered(
        container_id="TEST002", 
        weight=2205,  # ~1000kg
        unit="lbs"
    )
    assert container_lbs.weight_in_kg == 1000
    
    # Test None weight
    container_none = ContainerRegistered(
        container_id="TEST003",
        weight=None,
        unit="kg"
    )
    assert container_none.weight_in_kg is None


def test_container_is_known_weight():
    """Test is_known_weight method."""
    container_known = ContainerRegistered(
        container_id="TEST001",
        weight=1000,
        unit="kg"
    )
    assert container_known.is_known_weight() is True
    
    container_unknown = ContainerRegistered(
        container_id="TEST002",
        weight=None,
        unit="kg"
    )
    assert container_unknown.is_known_weight() is False


# ============================================================================
# Transaction Model Tests
# ============================================================================

def test_transaction_creation():
    """Test Transaction model creation."""
    transaction = Transaction(
        session_id="test-session-123",
        direction="in",
        truck="ABC-123",
        containers='["CONT001", "CONT002"]',
        bruto=5000
    )
    
    assert transaction.session_id == "test-session-123"
    assert transaction.direction == "in"
    assert transaction.truck == "ABC-123"
    assert transaction.containers == '["CONT001", "CONT002"]'
    assert transaction.bruto == 5000


def test_transaction_container_list_property():
    """Test container_list property parsing."""
    transaction = Transaction(
        session_id="test-session-123",
        direction="in",
        truck="ABC-123",
        containers='["CONT001", "CONT002"]',
        bruto=5000
    )
    
    # Test getter
    container_list = transaction.container_list
    assert container_list == ["CONT001", "CONT002"]
    
    # Test setter
    transaction.container_list = ["CONT003", "CONT004"]
    assert transaction.containers == '["CONT003", "CONT004"]'
    
    # Test invalid JSON
    transaction.containers = "invalid json"
    assert transaction.container_list == []


def test_transaction_direction_methods():
    """Test direction checking methods."""
    in_transaction = Transaction(
        session_id="test-session-123",
        direction="in",
        truck="ABC-123",
        containers='["CONT001"]',
        bruto=5000
    )
    
    assert in_transaction.is_in_transaction() is True
    assert in_transaction.is_out_transaction() is False
    
    out_transaction = Transaction(
        session_id="test-session-123",
        direction="out",
        truck="ABC-123",
        containers='["CONT001"]',
        bruto=4500,
        truck_tara=500,
        neto=4000
    )
    
    assert out_transaction.is_in_transaction() is False
    assert out_transaction.is_out_transaction() is True
    assert out_transaction.has_net_weight() is True


def test_transaction_display_methods():
    """Test display methods for truck and produce."""
    transaction = Transaction(
        session_id="test-session-123",
        direction="in",
        truck=None,
        containers='["CONT001"]',
        bruto=5000,
        produce=None
    )
    
    assert transaction.get_display_truck() == "na"
    assert transaction.get_display_produce() == "na"
    
    transaction.truck = "ABC-123"
    transaction.produce = "apples"
    
    assert transaction.get_display_truck() == "ABC-123"
    assert transaction.get_display_produce() == "apples"


# ============================================================================
# Model Relationship Tests
# ============================================================================

def test_transaction_net_weight_calculation():
    """Test net weight calculation logic."""
    # Transaction without net weight
    transaction = Transaction(
        session_id="test-session-123",
        direction="in",
        truck="ABC-123",
        containers='["CONT001"]',
        bruto=5000
    )
    
    assert transaction.has_net_weight() is False
    
    # Transaction with net weight
    transaction.neto = 4000
    assert transaction.has_net_weight() is True


def test_model_string_representations():
    """Test model __repr__ methods."""
    container = ContainerRegistered(
        container_id="TEST001",
        weight=1000,
        unit="kg"
    )
    
    repr_str = repr(container)
    assert "TEST001" in repr_str
    assert "1000" in repr_str
    assert "kg" in repr_str
    
    transaction = Transaction(
        session_id="test-session-123",
        direction="in",
        truck="ABC-123",
        containers='["CONT001"]',
        bruto=5000
    )
    
    repr_str = repr(transaction)
    assert "test-session-123" in repr_str
    assert "in" in repr_str