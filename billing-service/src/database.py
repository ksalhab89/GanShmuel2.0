import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from mysql.connector import pooling

from .config import settings

logger = logging.getLogger(__name__)

# Database connection pool
_connection_pool: Optional[pooling.MySQLConnectionPool] = None


def initialize_pool() -> None:
    """Initialize the MySQL connection pool."""
    global _connection_pool

    try:
        pool_config = {
            "host": settings.db_host,
            "port": settings.db_port,
            "database": settings.db_name,
            "user": settings.db_user,
            "password": settings.db_password,
            "pool_name": "billing_pool",
            "pool_size": 10,
            "pool_reset_session": True,
            "charset": "utf8mb4",
            "collation": "utf8mb4_unicode_ci",
            "autocommit": True,
        }

        _connection_pool = pooling.MySQLConnectionPool(**pool_config)
        logger.info("Database connection pool initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")
        _connection_pool = None
        raise


def get_connection():
    """Get a connection from the pool."""
    if _connection_pool is None:
        raise RuntimeError("Database pool not initialized")

    try:
        return _connection_pool.get_connection()
    except Exception as e:
        logger.error(f"Failed to get database connection: {e}")
        raise


@asynccontextmanager
async def get_db_connection():
    """Async context manager for database connections."""
    connection = None
    try:
        # Run the synchronous database operation in a thread pool
        connection = await asyncio.get_event_loop().run_in_executor(
            None, get_connection
        )
        yield connection
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if connection:
            try:
                connection.close()
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")


async def execute_query(
    query: str,
    params: Optional[tuple] = None,
    fetch_one: bool = False,
    fetch_all: bool = False,
) -> Optional[Dict[str, Any] | List[Dict[str, Any]]]:
    """Execute a database query asynchronously."""
    async with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, cursor.execute, query, params or ()
            )

            if fetch_one:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, cursor.fetchone
                )
                return result
            elif fetch_all:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, cursor.fetchall
                )
                return result
            else:
                # For INSERT/UPDATE/DELETE operations
                connection.commit()
                return {
                    "affected_rows": cursor.rowcount,
                    "last_insert_id": cursor.lastrowid,
                }

        finally:
            cursor.close()


async def health_check() -> bool:
    """Check database connectivity."""
    try:
        result = await execute_query("SELECT 1", fetch_one=True)
        return result is not None
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
