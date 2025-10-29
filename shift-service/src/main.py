"""FastAPI application entry point for shift service."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from .config import settings
from .routers import health, shifts
from .metrics import get_metrics

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Employee shift tracking and scheduling service",
    debug=settings.debug,
    root_path="/api/shift",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration - environment-specific origins
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

# Include routers
app.include_router(health.router)
app.include_router(shifts.router)


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """API welcome endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "description": "Employee shift tracking and scheduling service",
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "shifts": "/shifts",
            "operators": "/shifts/operators",
            "metrics": "/metrics",
        },
    }


# Add metrics endpoint
@app.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
async def metrics():
    """Prometheus metrics endpoint."""
    return get_metrics()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5003,
        reload=True,
    )
