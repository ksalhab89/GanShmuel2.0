"""Health check endpoints."""

from datetime import datetime
from importlib.metadata import version
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy import text

from ..dependencies import DatabaseSession
from ..models.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(db: DatabaseSession = ...):
    """Check application health."""
    # Test database connection
    try:
        await db.execute(text("SELECT 1"))
        database_status = "healthy"
    except Exception:
        database_status = "unhealthy"

    return {
        "status": "healthy" if database_status == "healthy" else "degraded",
        "service": "weight-service",
        "version": version("weight-service"),
        "database": database_status,
        "timestamp": datetime.now().isoformat()
    }
