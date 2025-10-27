# Gan Shmuel Billing Service (FastAPI)

Modern FastAPI-based billing service for the Gan Shmuel industrial weight management system.

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Start the billing service and database
docker-compose up -d

# View logs
docker-compose logs billing-service

# Stop services
docker-compose down
```

### Development Setup

```bash
# Install dependencies with uv
uv sync --dev

# Run tests
uv run pytest tests/ -v

# Start development server
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 5002
```

## Service Configuration

### Database Connection
- **Host**: localhost (external), billing-db (internal)
- **Port**: 3307 (external), 3306 (internal)
- **Database**: billdb
- **User**: billinguser
- **Password**: billingpass

### API Endpoints
- **Base URL**: http://localhost:5002
- **API Documentation**: http://localhost:5002/docs (Swagger UI)
- **Alternative Docs**: http://localhost:5002/redoc

## Key Features

### Provider Management
- `POST /provider` - Create new provider
- `PUT /provider/{id}` - Update provider

### Rate Management  
- `POST /rates` - Upload rates from Excel file (multipart/form-data)
- `POST /rates/from-directory` - Upload rates from Excel file in /in directory
- `GET /rates` - Download current rates as Excel file

### Truck Management
- `POST /truck` - Register truck with provider
- `PUT /truck/{id}` - Update truck's provider
- `GET /truck/{id}` - Get truck details and sessions

### Bill Generation
- `GET /bill/{id}` - Generate provider invoice with date range

### Health Check
- `GET /health` - Service health status

## File Upload Directory

Place Excel files for rate uploads in:
- `../in/` directory (mounted to `/in` in container)

## Integration

### Weight Service Integration
- Configured via `WEIGHT_SERVICE_URL` environment variable
- Default: http://localhost:5001
- Used for truck details and transaction data

## Development

### Testing
```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ -v --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_bills.py -v
```

### Code Quality
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

## Production Deployment

1. **Environment Variables**: Set appropriate values for production
2. **Database**: Use managed MySQL service or configure backup/recovery
3. **Security**: Configure HTTPS termination and authentication
4. **Monitoring**: Set up logging and metrics collection
5. **Scaling**: Use container orchestration for high availability

## Architecture

- **FastAPI**: Modern async web framework
- **uv**: Ultra-fast Python package manager
- **Pydantic**: Data validation and serialization
- **MySQL**: Relational database with connection pooling
- **Docker**: Containerized deployment
- **Pytest**: Comprehensive test suite

## API Examples

### Create Provider
```bash
curl -X POST http://localhost:5002/provider \
  -H "Content-Type: application/json" \
  -d '{"name": "Fruit Farm Co"}'
```

### Upload Rates
```bash
# Upload Excel file directly (recommended)
curl -X POST http://localhost:5002/rates \
  -F "file=@rates.xlsx"

# Or upload from /in directory
curl -X POST http://localhost:5002/rates/from-directory \
  -H "Content-Type: application/json" \
  -d '{"file": "rates.xlsx"}'
```

### Generate Bill
```bash
curl "http://localhost:5002/bill/1?from=20240101000000&to=20240131235959"
```