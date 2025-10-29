"""Main FastAPI application for provider registration service"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from slowapi.errors import RateLimitExceeded

from .config import settings
from .database import engine
from .routers import candidates, health, auth
from .metrics import get_metrics, SERVICE_UP
from .middleware import RequestTracingMiddleware
from .rate_limiting import limiter, rate_limit_exceeded_handler

# Configure structured logging
from .logging_config import configure_logging
configure_logging()

# Also configure stdlib logging for compatibility
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("provider_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    logger.info("Starting Provider Registration Service...")
    SERVICE_UP.set(1)
    yield
    logger.info("Shutting down Provider Registration Service...")
    await engine.dispose()
    SERVICE_UP.set(0)


# Create FastAPI application
app = FastAPI(
    title="Gan Shmuel Provider Registration Service",
    description="Provider candidate registration and approval system",
    version="1.0.0",
    lifespan=lifespan,
    root_path="/api/providers",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# Add rate limiter state to app
app.state.limiter = limiter

# Add rate limit exceeded exception handler
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# CORS configuration - environment-specific origins
import os
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    allowed_origins = [
        "https://gan-shmuel.com",
        "https://app.gan-shmuel.com",
    ]
elif ENVIRONMENT == "staging":
    allowed_origins = [
        "https://staging.gan-shmuel.com",
    ]
else:  # development
    allowed_origins = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",  # Vite dev server
    ]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # SECURITY: Specific domains only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Add request tracing middleware (executes after CORS)
app.add_middleware(RequestTracingMiddleware)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, tags=["Authentication"])
app.include_router(candidates.router, tags=["Candidates"])


@app.get("/", include_in_schema=False)
async def root():
    """API welcome endpoint"""
    return {
        "service": "Gan Shmuel Provider Registration Service",
        "version": "1.0.0",
        "description": "Provider candidate registration and approval system",
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "candidates": "/candidates",
            "approve_candidate": "/candidates/{id}/approve",
            "metrics": "/metrics"
        }
    }


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus metrics endpoint"""
    return get_metrics()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.app_host, port=settings.app_port)
