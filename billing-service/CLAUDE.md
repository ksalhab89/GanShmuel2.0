# Billing Service - CLAUDE.md

FastAPI service for provider billing and rate management.

## Development Setup

```bash
# Install dependencies with dev group
uv sync --dev

# Run development server
uv run uvicorn src.main:app --reload --port 5002

# API Documentation available at: http://localhost:5002/docs
```

## Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ -v --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_bills.py -v
```

## Code Quality

```bash
# Format code
uv run black src tests

# Sort imports
uv run isort src tests

# Lint code
uv run flake8 src tests

# Type checking
uv run mypy src
```

## Docker

```bash
# Start with database
docker-compose up -d
```

## Core Business Logic

### Billing Rate Logic
- Provider-specific rates override general rates (scope precedence)
- Bill calculation: `Neto weight × rate = payment amount`
- Only processes transactions for provider's registered trucks

### Rate Management
- Excel file upload/download for pricing rates
- Rate files: Excel format with Product, Rate, Scope columns
- Provider-specific rates override general rates based on scope

## Architecture

### Repository Pattern
- `src/routers/` - FastAPI route handlers
- `src/services/` - Business logic and orchestration
- `src/models/repositories.py` - Data access layer with repository pattern
- `src/models/schemas.py` - Pydantic models for validation
- Custom exception handling with proper HTTP status codes

### Database Design
- MySQL with connection pooling
- Stores providers, trucks, rates, and billing data
- Efficient querying with indexed relationships

## Key Features

### Excel Processing
- Comprehensive Excel file handling for rate management
- Upload/download functionality for pricing rates
- Data validation and error reporting

### API Endpoints
- `/bills` - Bill management operations
- `/providers` - Provider CRUD operations
- `/trucks` - Truck registration and management
- `/rates` - Rate management and Excel operations
- `/health` - Health check endpoint
- `/metrics` - Prometheus metrics

## Integration Points

### External Service Communication
Fetches data from Weight Service:
- `GET /weight?from={date}&to={date}` - Fetch transactions for billing
- `GET /item/{truck_id}` - Get truck details and sessions

### Retry Logic
- Exponential backoff for Weight service calls
- Graceful degradation for service communication failures

### Frontend Integration
Provides billing data to frontend via REST API endpoints.

## Important Implementation Notes

- **Rate Precedence**: Provider-specific rates override general rates based on scope
- **Excel Processing**: Comprehensive Excel file handling for rate management
- **CORS Configuration**: Properly configured for frontend-backend communication
- **Error Recovery**: Retry patterns and graceful degradation for service communication
- **Prometheus Metrics**: Exposes `/metrics` endpoint for monitoring
- **Health Checks**: `/health` endpoint for service monitoring
- **Date Range Filtering**: Efficient querying with `from`/`to` timestamp parameters

## Service Details
- **Port**: 5002
- **Database**: MySQL (port 3307)
- **API Documentation**: `/docs`
- **Metrics**: `/metrics`