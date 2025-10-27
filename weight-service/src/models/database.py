"""SQLAlchemy database models for the Weight Service V2."""

import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ContainerRegistered(Base):
    """Container registration model for storing container tare weights."""
    
    __tablename__ = "containers_registered"
    
    # Primary key - container identifier (max 15 chars)
    container_id: Mapped[str] = mapped_column(String(15), primary_key=True)
    
    # Weight in specified unit (nullable for unknown weights)
    weight: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Unit of measurement ('kg' or 'lbs')
    unit: Mapped[str] = mapped_column(String(3), nullable=False, default="kg")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_containers_weight", "weight"),
        Index("idx_containers_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<ContainerRegistered(id={self.container_id!r}, weight={self.weight}, unit={self.unit!r})>"
    
    @property
    def weight_in_kg(self) -> Optional[int]:
        """Get weight converted to kilograms."""
        if self.weight is None:
            return None
        if self.unit == "lbs":
            return int(self.weight * 0.453592)  # Convert lbs to kg
        return self.weight
    
    def is_known_weight(self) -> bool:
        """Check if container has a known weight."""
        return self.weight is not None


class Transaction(Base):
    """Transaction model for storing weighing operations."""
    
    __tablename__ = "transactions"
    
    # Primary key - auto-incrementing ID
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Session identifier (UUID format)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    
    # Transaction timestamp
    datetime: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    
    # Weighing direction ('in', 'out', 'none')
    direction: Mapped[str] = mapped_column(String(4), nullable=False, index=True)
    
    # Truck license plate (nullable)
    truck: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    
    # Container IDs as JSON array
    containers: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Gross weight in kg
    bruto: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Truck tare weight in kg (nullable, calculated for OUT transactions)
    truck_tara: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Net fruit weight in kg (nullable, calculated for OUT transactions)
    neto: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Produce type (nullable)
    produce: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Creation timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    
    # Composite and performance indexes
    __table_args__ = (
        Index("idx_session_direction", "session_id", "direction"),
        Index("idx_datetime", "datetime"),
        Index("idx_direction", "direction"),
        Index("idx_truck", "truck"),
    )
    
    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, session_id={self.session_id!r}, direction={self.direction!r})>"
    
    @property
    def container_list(self) -> List[str]:
        """Parse containers JSON field into list of container IDs."""
        try:
            return json.loads(self.containers)
        except (json.JSONDecodeError, TypeError):
            return []
    
    @container_list.setter
    def container_list(self, value: List[str]) -> None:
        """Set containers from list of container IDs."""
        self.containers = json.dumps(value)
    
    def is_in_transaction(self) -> bool:
        """Check if this is an IN transaction."""
        return self.direction == "in"
    
    def is_out_transaction(self) -> bool:
        """Check if this is an OUT transaction."""
        return self.direction == "out"
    
    def has_net_weight(self) -> bool:
        """Check if transaction has calculated net weight."""
        return self.neto is not None
    
    def get_display_truck(self) -> str:
        """Get truck for display (returns 'na' if None)."""
        return self.truck if self.truck else "na"
    
    def get_display_produce(self) -> str:
        """Get produce for display (returns 'na' if None)."""
        return self.produce if self.produce else "na"