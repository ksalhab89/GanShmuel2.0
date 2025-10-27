"""Health check endpoint for monitoring and Docker healthchecks"""

from fastapi import APIRouter
from ..database import health_check

router = APIRouter()


@router.get("/health")
async def health():
    """
    Health check endpoint

    Returns service status and database connectivity status.
    Used by Docker healthcheck and monitoring systems.
    """
    db_healthy = await health_check()
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "service": "provider-registration-service",
        "version": "1.0.0",
        "database": "connected" if db_healthy else "disconnected"
    }
