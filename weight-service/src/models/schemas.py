"""Pydantic schemas for request and response validation."""

import re
from datetime import datetime
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Request Schemas
# ============================================================================

class WeightRequest(BaseModel):
    """Schema for weight recording requests."""
    
    direction: Literal["in", "out", "none"] = Field(
        ..., description="Weighing direction"
    )
    truck: str = Field(
        default="na", max_length=20, description="Truck license plate"
    )
    containers: str = Field(
        ..., description="Comma-separated container IDs"
    )
    weight: int = Field(
        ..., gt=0, description="Weight value (must be positive)"
    )
    unit: Literal["kg", "lbs"] = Field(
        default="kg", description="Weight unit"
    )
    force: bool = Field(
        default=False, description="Force overwrite existing session"
    )
    produce: str = Field(
        default="na", max_length=50, description="Produce type"
    )
    
    @field_validator("containers")
    @classmethod
    def validate_containers(cls, v: str) -> str:
        """Validate container ID format and list."""
        if not v or v.strip() == "":
            raise ValueError("Container list cannot be empty")
        
        # Parse container IDs
        container_ids = [c.strip() for c in v.split(",") if c.strip()]
        if not container_ids:
            raise ValueError("Container list cannot be empty")
        
        # Validate each container ID
        for container_id in container_ids:
            if len(container_id) > 15:
                raise ValueError(f"Container ID '{container_id}' exceeds 15 characters")
            if not re.match(r'^[a-zA-Z0-9\-_]+$', container_id):
                raise ValueError(f"Container ID '{container_id}' contains invalid characters")
        
        return v
    
    @field_validator("truck")
    @classmethod
    def validate_truck(cls, v: str) -> str:
        """Validate truck license format."""
        if v and v != "na":
            if len(v) > 20:
                raise ValueError("Truck license exceeds 20 characters")
            # Allow alphanumeric and common license plate characters including underscore
            if not re.match(r'^[a-zA-Z0-9\-\s_]+$', v):
                raise ValueError("Invalid truck license format")
        return v


class BatchWeightRequest(BaseModel):
    """Schema for batch weight upload requests."""
    
    file: str = Field(
        ..., description="Filename for batch upload"
    )
    
    @field_validator("file")
    @classmethod
    def validate_file(cls, v: str) -> str:
        """Validate file extension and prevent path traversal."""
        if not v:
            raise ValueError("Filename cannot be empty")
        
        # Prevent path traversal
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("Invalid filename: path traversal detected")
        
        # Check file extension
        if not (v.endswith(".csv") or v.endswith(".json")):
            raise ValueError("File must be .csv or .json format")
        
        return v


class ContainerWeightData(BaseModel):
    """Schema for individual container weight data in batch uploads."""
    
    id: str = Field(
        ..., max_length=15, description="Container identifier"
    )
    weight: int = Field(
        ..., gt=0, description="Container weight (positive values only)"
    )
    unit: Literal["kg", "lbs"] = Field(
        default="kg", description="Weight unit"
    )
    
    @field_validator("id")
    @classmethod
    def validate_container_id(cls, v: str) -> str:
        """Validate container ID format."""
        if not re.match(r'^[a-zA-Z0-9\-_]+$', v):
            raise ValueError("Container ID contains invalid characters")
        return v


class WeightQueryParams(BaseModel):
    """Schema for weight query parameters."""
    
    from_time: Optional[str] = Field(
        default=None, description="Start time in yyyymmddhhmmss format"
    )
    to_time: Optional[str] = Field(
        default=None, description="End time in yyyymmddhhmmss format"
    )
    filter: str = Field(
        default="in,out,none", description="Direction filter"
    )
    
    @field_validator("from_time", "to_time")
    @classmethod
    def validate_datetime_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate datetime string format."""
        if v is None:
            return v
        
        if not re.match(r'^\d{14}$', v):
            raise ValueError("DateTime must be in yyyymmddhhmmss format")
        
        # Try to parse to ensure it's a valid date
        try:
            datetime.strptime(v, "%Y%m%d%H%M%S")
        except ValueError:
            raise ValueError("Invalid datetime value")
        
        return v
    
    @field_validator("filter")
    @classmethod
    def validate_filter(cls, v: str) -> str:
        """Validate direction filter values."""
        valid_directions = {"in", "out", "none"}
        filter_parts = [f.strip() for f in v.split(",")]
        
        for part in filter_parts:
            if part not in valid_directions:
                raise ValueError(f"Invalid filter direction: {part}")
        
        return v


class ItemQueryParams(BaseModel):
    """Schema for item query parameters."""
    
    from_time: Optional[str] = Field(
        default=None, description="Start time in yyyymmddhhmmss format"
    )
    to_time: Optional[str] = Field(
        default=None, description="End time in yyyymmddhhmmss format"
    )
    
    @field_validator("from_time", "to_time")
    @classmethod
    def validate_datetime_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate datetime string format."""
        if v is None:
            return v
        
        if not re.match(r'^\d{14}$', v):
            raise ValueError("DateTime must be in yyyymmddhhmmss format")
        
        try:
            datetime.strptime(v, "%Y%m%d%H%M%S")
        except ValueError:
            raise ValueError("Invalid datetime value")
        
        return v


# ============================================================================
# Response Schemas
# ============================================================================

class WeightResponse(BaseModel):
    """Schema for weight operation responses."""

    id: str = Field(..., description="Session UUID")
    session_id: str = Field(..., description="Session UUID")
    direction: str = Field(..., description="Weighing direction (in/out/none)")
    truck: str = Field(..., description="Truck license or 'na'")
    bruto: int = Field(..., description="Gross weight in kg")
    gross_weight: int = Field(..., description="Gross weight in kg")
    truck_tara: Optional[int] = Field(
        default=None, description="Truck tare weight (OUT only)"
    )
    neto: Optional[Union[int, str]] = Field(
        default="na", description="Net weight or 'na'"
    )
    net_weight: Optional[Union[int, str]] = Field(
        default="na", description="Net weight or 'na'"
    )


class BatchUploadResponse(BaseModel):
    """Schema for batch upload operation responses."""
    
    message: str = Field(..., description="Operation summary")
    processed_count: int = Field(..., description="Successfully processed records")
    skipped_count: int = Field(..., description="Skipped/duplicate records")
    errors: List[str] = Field(default_factory=list, description="Error messages")


class TransactionResponse(BaseModel):
    """Schema for transaction query responses."""

    id: str = Field(..., description="Session UUID")
    direction: str = Field(..., description="Weighing direction")
    truck: Optional[str] = Field(default=None, description="Truck license plate")
    bruto: int = Field(..., description="Gross weight in kg")
    gross_weight: Optional[int] = Field(default=None, description="Gross weight in kg (alias for bruto)")
    neto: Optional[Union[int, str]] = Field(
        default=None, description="Net weight or 'na'"
    )
    produce: str = Field(..., description="Produce type")
    containers: List[str] = Field(..., description="Container IDs")

    def __init__(self, **data):
        # Set gross_weight to bruto if not provided
        if 'gross_weight' not in data or data['gross_weight'] is None:
            data['gross_weight'] = data.get('bruto')
        super().__init__(**data)


class ItemResponse(BaseModel):
    """Schema for item query responses."""

    id: str = Field(..., description="Item identifier")
    item_id: Optional[str] = Field(default=None, description="Item identifier (alias for id)")
    item_type: Optional[str] = Field(default=None, description="Type of item (truck or container)")
    tara: Union[int, str] = Field(..., description="Tare weight or 'na'")
    sessions: List[str] = Field(..., description="Session UUIDs")

    def __init__(self, **data):
        # Set item_id to id if not provided
        if 'item_id' not in data or data['item_id'] is None:
            data['item_id'] = data.get('id')
        super().__init__(**data)


class SessionResponse(BaseModel):
    """Schema for session query responses."""

    id: str = Field(..., description="Session UUID")
    session_id: Optional[str] = Field(default=None, description="Session UUID (alias for id)")
    truck: str = Field(..., description="Truck license or 'na'")
    bruto: int = Field(..., description="Gross weight in kg")
    truck_tara: Optional[int] = Field(
        default=None, description="Truck tare weight (OUT only)"
    )
    neto: Optional[Union[int, str]] = Field(
        default=None, description="Net weight or 'na'"
    )

    def __init__(self, **data):
        # Set session_id to id if not provided
        if 'session_id' not in data or data['session_id'] is None:
            data['session_id'] = data.get('id')
        super().__init__(**data)


class HealthResponse(BaseModel):
    """Schema for health check responses."""
    
    status: str = Field(..., description="Service status")
    database: str = Field(..., description="Database connection status")
    timestamp: datetime = Field(..., description="Check timestamp")


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    code: str = Field(..., description="Internal error code")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


# ============================================================================
# Internal Data Transfer Objects
# ============================================================================

class ContainerWeightInfo(BaseModel):
    """Internal schema for container weight information."""
    
    container_id: str
    weight: Optional[int]
    unit: str = "kg"
    is_known: bool = True
    
    @property
    def weight_in_kg(self) -> Optional[int]:
        """Get weight converted to kilograms."""
        if self.weight is None:
            return None
        if self.unit == "lbs":
            return int(self.weight * 0.453592)
        return self.weight


class SessionPair(BaseModel):
    """Internal schema for IN/OUT session pairs."""
    
    session_id: str
    in_transaction: Optional["TransactionResponse"] = None
    out_transaction: Optional["TransactionResponse"] = None
    is_complete: bool = False
    
    @property
    def has_both_transactions(self) -> bool:
        """Check if session has both IN and OUT transactions."""
        return self.in_transaction is not None and self.out_transaction is not None