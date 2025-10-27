"""SQLAlchemy ORM models for database tables"""

from sqlalchemy import (
    Column, String, Integer, Text, TIMESTAMP, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from ..database import Base
import uuid


class Candidate(Base):
    """Candidate model for provider registration"""

    __tablename__ = "candidates"

    # Columns
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name = Column(String(255), nullable=False)
    contact_email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(50), nullable=True)
    products = Column(JSONB, nullable=True)
    truck_count = Column(Integer, nullable=True)
    capacity_tons_per_day = Column(Integer, nullable=True)
    location = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default='pending')
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    provider_id = Column(Integer, nullable=True)  # Reference to billing service
    version = Column(Integer, nullable=False, default=1)  # Optimistic locking
    rejection_reason = Column(Text, nullable=True)  # Reason for rejection

    # Constraints
    __table_args__ = (
        CheckConstraint('truck_count > 0', name='truck_count_positive'),
        CheckConstraint('capacity_tons_per_day > 0', name='capacity_positive'),
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name='status_check'),
        Index('idx_candidates_status', 'status'),
        Index('idx_candidates_created_at', 'created_at'),
        Index('idx_candidates_products', 'products', postgresql_using='gin'),
        Index('idx_candidates_version', 'id', 'version'),
    )

    def __repr__(self):
        return f"<Candidate(id={self.id}, company_name='{self.company_name}', status='{self.status}')>"
