"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from .config import settings
from .database import close_db, init_db
from .routers import batch, health, query, weight
from .metrics import get_metrics


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Industrial weight management system for truck/container weighing operations",
    debug=settings.debug,
    lifespan=lifespan,
    root_path="/api/weight",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Weight Operations",
            "description": "Core weighing operations (IN/OUT/NONE directions)",
        },
        {
            "name": "Batch Operations", 
            "description": "Batch upload of container weights from CSV/JSON files",
        },
        {
            "name": "Query Operations",
            "description": "Query transactions, sessions, and item details",
        },
        {
            "name": "Health",
            "description": "System health and database connectivity checks",
        },
    ],
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

# Include routers
app.include_router(weight.router)
app.include_router(batch.router)
app.include_router(query.router)
app.include_router(health.router)

# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """API welcome endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "description": "Industrial weight management system for truck/container weighing operations",
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "weighing": "/weight",
            "batch_upload": "/batch",
            "query": "/query",
            "metrics": "/metrics"
        }
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
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
