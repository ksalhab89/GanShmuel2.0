from importlib.metadata import version

from fastapi import APIRouter

from ..models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_endpoint():
    """
    Health check endpoint for load balancer and monitoring.

    Returns:
    - status: "healthy"
    - service: "billing-service"
    - version: automatically read from package metadata
    """
    return HealthResponse(
        status="healthy", service="billing-service", version=version("billing-service")
    )
