import logging
from contextlib import asynccontextmanager
from importlib.metadata import version
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from .config import settings
from .database import initialize_pool
from .routers import health, providers, rates, trucks, bills
from .metrics import get_metrics
from .utils.exceptions import (
    BillingServiceException,
    NotFoundError,
    DuplicateError,
    ValidationError,
    WeightServiceError,
    FileError
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("billing_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Billing Service...")
    try:
        initialize_pool()
        logger.info("Billing Service started successfully")
    except Exception as e:
        logger.error(f"Failed to start Billing Service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Billing Service...")


# Create FastAPI application
app = FastAPI(
    title="Gan Shmel Billing Service",
    description="Industrial weight management billing system",
    version=version("billing-service"),
    lifespan=lifespan,
    root_path="/api/billing",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(providers.router, tags=["Providers"])
app.include_router(rates.router, tags=["Rates"])
app.include_router(trucks.router, tags=["Trucks"])
app.include_router(bills.router, tags=["Bills"])

# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """API welcome endpoint."""
    return {
        "service": "Gan Shmuel Billing Service",
        "version": version("billing-service"),
        "description": "Industrial weight management billing system",
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "providers": "/providers",
            "trucks": "/trucks",
            "rates": "/rates",
            "bills": "/bills",
            "metrics": "/metrics"
        }
    }


# Add metrics endpoint
@app.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
async def metrics():
    """Prometheus metrics endpoint."""
    return get_metrics()


# Global exception handlers
@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": str(exc)}
    )


@app.exception_handler(DuplicateError)
async def duplicate_handler(request: Request, exc: DuplicateError):
    return JSONResponse(
        status_code=409,
        content={"error": str(exc)}
    )


@app.exception_handler(ValidationError)
async def validation_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": str(exc)}
    )


@app.exception_handler(WeightServiceError)
async def weight_service_handler(request: Request, exc: WeightServiceError):
    return JSONResponse(
        status_code=503,
        content={"error": str(exc)}
    )


@app.exception_handler(FileError)
async def file_handler(request: Request, exc: FileError):
    return JSONResponse(
        status_code=400,
        content={"error": str(exc)}
    )


@app.exception_handler(BillingServiceException)
async def general_billing_handler(request: Request, exc: BillingServiceException):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug
    )