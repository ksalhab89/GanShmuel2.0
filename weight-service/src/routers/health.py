"""Health check endpoints."""

from importlib.metadata import version
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    service: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check application health."""
    return HealthResponse(
        status="healthy",
        service="weight-service",
        version=version("weight-service")
    )
