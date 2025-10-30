from fastapi import HTTPException

from .database import get_db_connection


async def get_database():
    """Dependency to provide database connection."""
    try:
        async with get_db_connection() as connection:
            yield connection
    except Exception:
        raise HTTPException(status_code=500, detail="Database connection failed")
