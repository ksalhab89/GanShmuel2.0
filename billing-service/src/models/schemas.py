from typing import List, Optional, Union

from pydantic import BaseModel, Field


# Base response models
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


# Provider models
class ProviderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class ProviderUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class ProviderResponse(BaseModel):
    id: int
    name: str


# Rate models
class RateUpload(BaseModel):
    file: str = Field(..., description="Filename in /in directory")


class RateUploadResponse(BaseModel):
    message: str


class Rate(BaseModel):
    product_id: str
    rate: int
    scope: str


# Truck models
class TruckCreate(BaseModel):
    id: str = Field(..., max_length=10)
    provider_id: int


class TruckUpdate(BaseModel):
    provider_id: int


class TruckResponse(BaseModel):
    id: str
    provider_id: int


class TruckDetails(BaseModel):
    id: str
    tara: Union[int, str]  # Can be integer or "na"
    sessions: List[str]


# Bill models
class ProductSummary(BaseModel):
    product: str
    count: str  # String as per API spec
    amount: int  # Net weight in kg
    rate: int  # Rate in agorot
    pay: int  # Payment amount in agorot


class BillResponse(BaseModel):
    id: str  # Provider ID as string
    name: str  # Provider name
    from_: str = Field(..., alias="from")  # Start timestamp
    to: str  # End timestamp
    truckCount: int
    sessionCount: int
    products: List[ProductSummary]
    total: int  # Total payment in agorot

    class Config:
        populate_by_name = True
