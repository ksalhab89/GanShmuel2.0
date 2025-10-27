"""Pydantic models for shift service."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class OperatorBase(BaseModel):
    """Base operator schema."""
    name: str = Field(..., min_length=1, max_length=100)
    employee_id: str = Field(..., min_length=1, max_length=50)
    role: str = Field(default="weigher", pattern="^(weigher|supervisor|admin)$")


class OperatorCreate(OperatorBase):
    """Schema for creating a new operator."""
    pass


class OperatorResponse(OperatorBase):
    """Schema for operator response."""
    id: int
    created_at: datetime
    is_active: bool = True

    class Config:
        from_attributes = True


class ShiftBase(BaseModel):
    """Base shift schema."""
    operator_id: int
    shift_type: str = Field(..., pattern="^(morning|afternoon|night)$")


class ShiftStart(ShiftBase):
    """Schema for starting a shift."""
    pass


class ShiftEnd(BaseModel):
    """Schema for ending a shift."""
    notes: Optional[str] = Field(None, max_length=500)


class ShiftResponse(ShiftBase):
    """Schema for shift response."""
    id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    transactions_processed: int = 0
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class ShiftListResponse(BaseModel):
    """Schema for list of shifts."""
    shifts: list[ShiftResponse]
    total: int


class OperatorListResponse(BaseModel):
    """Schema for list of operators."""
    operators: list[OperatorResponse]
    total: int
