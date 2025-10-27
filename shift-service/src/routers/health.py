"""Health check endpoints."""

from fastapi import APIRouter
from ..database import test_db_connection
from ..config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    db_healthy = test_db_connection()

    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "database": "connected" if db_healthy else "disconnected",
    }
