"""Pydantic schemas for request/response validation"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import List, Optional
from datetime import datetime
from uuid import UUID


class CandidateCreate(BaseModel):
    """Schema for creating a new candidate"""

    company_name: str = Field(..., min_length=1, max_length=255)
    contact_email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    products: List[str] = Field(..., min_items=1)
    truck_count: int = Field(..., gt=0)
    capacity_tons_per_day: int = Field(..., gt=0)
    location: Optional[str] = Field(None, max_length=255)

    @field_validator('products')
    @classmethod
    def validate_products(cls, v):
        """Validate that products are in allowed list"""
        allowed = ['apples', 'oranges', 'grapes', 'bananas', 'mangoes']
        for product in v:
            if product not in allowed:
                raise ValueError(f"Invalid product: {product}. Allowed products: {', '.join(allowed)}")
        return v


class CandidateResponse(BaseModel):
    """Schema for candidate response"""

    candidate_id: UUID
    status: str
    company_name: str
    contact_email: str
    phone: Optional[str] = None
    products: List[str]
    truck_count: int
    capacity_tons_per_day: int
    location: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    provider_id: Optional[int] = None
    version: int  # Optimistic locking version
    rejection_reason: Optional[str] = None  # Optional reason for rejection

    class Config:
        from_attributes = True


class CandidateList(BaseModel):
    """Schema for paginated candidate list"""

    candidates: List[CandidateResponse]
    pagination: dict


class ApprovalResponse(BaseModel):
    """Schema for candidate approval response"""

    candidate_id: UUID
    status: str
    provider_id: int


class RejectionRequest(BaseModel):
    """Schema for candidate rejection request"""

    reason: Optional[str] = Field(None, max_length=1000, description="Optional reason for rejection")


class RejectionResponse(BaseModel):
    """Schema for candidate rejection response"""

    candidate_id: UUID
    status: str
    rejection_reason: Optional[str] = None
