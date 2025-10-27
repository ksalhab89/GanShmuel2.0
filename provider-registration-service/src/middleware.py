"""Middleware for request tracing and observability"""

import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
import time


logger = structlog.get_logger()


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request tracing with correlation IDs

    Features:
    - Generates or extracts X-Request-ID from request headers
    - Binds correlation ID to structlog context for all logs
    - Adds X-Request-ID to response headers
    - Logs request/response with timing information
    - Clears context after request completes

    Usage in main.py:
        app.add_middleware(RequestTracingMiddleware)
    """

    async def dispatch(self, request: Request, call_next):
        """Process request and add tracing"""

        # Get or generate request ID (correlation ID)
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Bind request context to structlog (will appear in all logs)
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown"
        )

        # Log incoming request
        start_time = time.time()
        logger.info(
            "request_started",
            user_agent=request.headers.get("user-agent", "unknown")
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Add request ID to response headers for client tracking
            response.headers["X-Request-ID"] = request_id

            # Log successful response
            logger.info(
                "request_completed",
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2)
            )

            return response

        except Exception as exc:
            # Calculate processing time even for errors
            process_time = time.time() - start_time

            # Log error with context
            logger.error(
                "request_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                process_time_ms=round(process_time * 1000, 2)
            )

            # Re-raise exception to be handled by FastAPI
            raise

        finally:
            # Clear context vars for next request
            structlog.contextvars.clear_contextvars()
