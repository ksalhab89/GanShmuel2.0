"""FastAPI dependency injection."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_db
from .services.container_service import ContainerService
from .services.file_service import FileService
from .services.query_service import QueryService
from .services.session_service import SessionService
from .services.weight_service import WeightService

# Database session dependency
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


# Service dependencies
def get_weight_service(db: DatabaseSession) -> WeightService:
    """Get WeightService instance with database session."""
    return WeightService(db)


def get_container_service(db: DatabaseSession) -> ContainerService:
    """Get ContainerService instance with database session."""
    return ContainerService(db)


def get_session_service(db: DatabaseSession) -> SessionService:
    """Get SessionService instance with database session."""
    return SessionService(db)


def get_file_service(db: DatabaseSession) -> FileService:
    """Get FileService instance with database session."""
    return FileService(db, upload_dir=settings.upload_dir)


def get_query_service(db: DatabaseSession) -> QueryService:
    """Get QueryService instance with database session."""
    return QueryService(db)
