"""Rate limiting configuration for API endpoints"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import redis.asyncio as redis
import structlog
from .config import settings

logger = structlog.get_logger()

# Initialize rate limiter with Redis backend
# Falls back to in-memory if Redis is not available
try:
    redis_client = redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True
    )

    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=settings.redis_url,
        default_limits=["200 per hour", "50 per minute"],  # Global defaults
        strategy="fixed-window",  # or "moving-window" for more accurate limiting
    )

    logger.info("rate_limiter_initialized", backend="redis", url=settings.redis_url)

except Exception as e:
    # Fallback to in-memory limiter if Redis is unavailable
    logger.warning("rate_limiter_fallback", error=str(e), backend="in-memory")

    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200 per hour", "50 per minute"],
        strategy="fixed-window",
    )


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Custom handler for rate limit exceeded errors"""

    # Extract rate limit info from exception
    detail = f"Rate limit exceeded: {exc.detail}"

    # Log the rate limit violation
    logger.warning(
        "rate_limit_exceeded",
        path=request.url.path,
        method=request.method,
        client_ip=request.client.host if request.client else "unknown",
        detail=exc.detail
    )

    # Return standardized error response
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": detail,
            "retry_after": exc.detail.split("in ")[-1] if "in " in exc.detail else "unknown"
        },
        headers={
            "Retry-After": "60",  # Suggest retry after 60 seconds
            "X-RateLimit-Limit": str(exc.detail.split()[0]) if exc.detail else "unknown",
            "X-RateLimit-Remaining": "0",
        }
    )


# Rate limiting tiers for different endpoint types
class RateLimits:
    """Predefined rate limit configurations for different endpoint types"""

    # Public endpoints (no authentication required)
    PUBLIC = "10 per minute"  # Very strict for public endpoints

    # Authentication endpoints
    AUTH_LOGIN = "5 per minute"  # Strict to prevent brute force
    AUTH_REGISTER = "3 per minute"  # Very strict for registration

    # Read operations (GET requests)
    READ_LIGHT = "100 per minute"  # Light reads (health checks, status)
    READ_HEAVY = "30 per minute"   # Heavy reads (lists, searches)

    # Write operations (POST, PUT, DELETE)
    WRITE_LIGHT = "50 per minute"  # Light writes (single record)
    WRITE_HEAVY = "10 per minute"  # Heavy writes (batch operations)

    # Administrative operations
    ADMIN = "20 per minute"  # Admin operations


# Helper function to get client identifier
def get_client_identifier(request: Request) -> str:
    """Get client identifier for rate limiting (IP or user ID)"""

    # Try to get authenticated user ID first
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"

    # Fall back to IP address
    client_ip = request.client.host if request.client else "unknown"

    # Check for forwarded IP (if behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

    return f"ip:{client_ip}"


# Decorator for custom rate limiting based on user authentication
def user_aware_limiter(request: Request) -> str:
    """Rate limiter that considers authenticated users differently"""
    return get_client_identifier(request)
