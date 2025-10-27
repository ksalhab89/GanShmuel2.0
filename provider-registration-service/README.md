# Provider Registration Service

FastAPI service for provider candidate registration and approval in the Gan Shmuel Industrial Weight Management System.

## 📋 Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [API Endpoints](#api-endpoints)
- [Development](#development)
- [Testing](#testing)
- [Production Deployment](#production-deployment)
- [Architecture](#architecture)

## ✨ Features

### Core Functionality
- **Candidate Registration**: Public endpoint for provider candidates to register
- **Candidate Management**: List, filter, and search candidates with dual pagination support
- **Approval Workflow**: Admin-only candidate approval with billing service integration
- **Rejection Workflow**: Admin-only candidate rejection with reasons (Phase 3)

### Security (Phase 1)
- **JWT Authentication**: Token-based authentication with HS256 algorithm
- **Role-Based Access Control**: Admin-only endpoints with authorization middleware
- **SQL Injection Protection**: Parameterized queries with SQLAlchemy
- **Password Hashing**: Bcrypt with automatic salt generation
- **Optimistic Locking**: Version-based concurrency control

### Reliability (Phase 2)
- **Retry Logic**: Exponential backoff for billing service integration (0.5s, 1s, 2s)
- **Structured Logging**: JSON logging with structured events
- **Health Checks**: Database connectivity verification
- **DRY Code**: Refactored for maintainability

### Data Management (Phase 3)
- **Database Migrations**: Alembic for schema version control
- **Rejection Tracking**: Store rejection reasons for audit trail
- **Version History**: Full migration history and rollback support

### Observability
- **Prometheus Metrics**: Request counters and service uptime
- **OpenAPI Documentation**: Auto-generated API docs at `/docs`
- **Health Endpoint**: Service and database health monitoring

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Docker (optional, for containerized deployment)
- Access to Billing Service (http://localhost:5002)

### 1. Install Dependencies

```bash
# Install uv package manager (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --dev
```

### 2. Configure Environment

Create `.env` file:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://provider_user:provider_pass@localhost:5432/provider_registration

# External Services
BILLING_SERVICE_URL=http://localhost:5002

# Application
APP_HOST=0.0.0.0
APP_PORT=5004
LOG_LEVEL=INFO

# JWT Authentication (REQUIRED)
JWT_SECRET_KEY=$(openssl rand -hex 32)
```

### 3. Setup Database

```bash
# Create database
psql -U postgres -c "CREATE DATABASE provider_registration;"
psql -U postgres -c "CREATE USER provider_user WITH PASSWORD 'provider_pass';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE provider_registration TO provider_user;"

# Run database migrations
alembic upgrade head
```

### 4. Run Service

```bash
# Development mode with auto-reload
uv run uvicorn src.main:app --reload --port 5004

# Production mode
uv run uvicorn src.main:app --host 0.0.0.0 --port 5004 --workers 4
```

### 5. Verify Installation

```bash
# Check health
curl http://localhost:5004/health
# Expected: {"status":"healthy","database":"connected","timestamp":"..."}

# View API documentation
open http://localhost:5004/docs
```

## 📚 Documentation

Comprehensive documentation for all aspects of the service:

- **[API.md](./API.md)** - Complete API reference with curl examples
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Production deployment guide
- **[OPERATIONS.md](./OPERATIONS.md)** - Operations runbook and troubleshooting
- **[SECURITY.md](./SECURITY.md)** - Security features and best practices
- **[CHANGELOG.md](./CHANGELOG.md)** - Version history and changes
- **[MIGRATIONS.md](./MIGRATIONS.md)** - Database migration guide

## 🔌 API Endpoints

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check with database status |
| GET | `/metrics` | Prometheus metrics |
| POST | `/auth/login` | Login and receive JWT token |
| POST | `/candidates` | Register new candidate |
| GET | `/candidates` | List candidates (with filters) |
| GET | `/candidates/{id}` | Get candidate by ID |

### Protected Endpoints (Admin Only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/candidates/{id}/approve` | Approve candidate |
| POST | `/candidates/{id}/reject` | Reject candidate (Phase 3) |

### Example Usage

```bash
# Register candidate
curl -X POST http://localhost:5004/candidates \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Fresh Fruit Ltd",
    "contact_email": "contact@freshfruit.com",
    "products": ["apples", "oranges"],
    "truck_count": 10,
    "capacity_tons_per_day": 500
  }'

# Login as admin
TOKEN=$(curl -X POST http://localhost:5004/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=admin123" \
  | jq -r '.access_token')

# Approve candidate
curl -X POST http://localhost:5004/candidates/{id}/approve \
  -H "Authorization: Bearer $TOKEN"
```

See **[API.md](./API.md)** for complete API documentation.

## 💻 Development

### Project Structure

```
provider-registration-service/
├── src/
│   ├── main.py                    # FastAPI application
│   ├── config.py                  # Configuration settings
│   ├── database.py                # Database connection
│   ├── metrics.py                 # Prometheus metrics
│   ├── logging_config.py          # Structured logging
│   ├── auth/
│   │   └── jwt_handler.py         # JWT authentication
│   ├── models/
│   │   ├── schemas.py             # Pydantic models
│   │   └── orm.py                 # SQLAlchemy ORM models
│   ├── routers/
│   │   ├── candidates.py          # Candidate endpoints
│   │   ├── auth.py                # Auth endpoints
│   │   └── health.py              # Health check
│   └── services/
│       ├── candidate_service.py   # Business logic
│       └── billing_client.py      # Billing integration
├── tests/
│   ├── conftest.py                # Test fixtures
│   ├── test_api_contract.py      # API contract tests
│   ├── test_auth_security.py     # Auth security tests
│   ├── test_sql_injection.py     # SQL injection tests
│   ├── test_concurrency.py       # Optimistic locking tests
│   └── test_billing_retry.py     # Retry logic tests
├── alembic/                       # Database migrations
│   ├── env.py                     # Alembic environment
│   └── versions/                  # Migration files
├── schema.sql                     # Database schema (legacy)
├── Dockerfile                     # Container image
├── pyproject.toml                 # Dependencies
├── alembic.ini                    # Alembic configuration
└── README.md                      # This file
```

### Development Workflow

```bash
# Install dev dependencies
uv sync --dev

# Run database migrations
alembic upgrade head

# Run service in development mode
uv run uvicorn src.main:app --reload --port 5004

# Run tests
uv run pytest tests/ -v

# Run tests with coverage
uv run pytest tests/ -v --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html

# Type checking
uv run mypy src
```

### Code Quality Tools

```bash
# Format code
uv run black src tests

# Sort imports
uv run isort src tests

# Lint code
uv run flake8 src tests

# Security scan
uv run bandit -r src
```

## 🧪 Testing

### Test Coverage

Comprehensive test coverage across all layers:

- **API Contract Tests**: Verify API endpoints match specifications
- **Authentication Tests**: JWT token generation and validation
- **Security Tests**: SQL injection protection
- **Concurrency Tests**: Optimistic locking behavior
- **Integration Tests**: Billing service integration and retry logic
- **Edge Cases**: Error handling and validation

### Run Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage report
uv run pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# Run specific test category
uv run pytest tests/test_api_contract.py -v
uv run pytest tests/test_auth_security.py -v
uv run pytest tests/test_sql_injection.py -v

# Run tests matching pattern
uv run pytest tests/ -v -k "test_create_candidate"
```

## 🚢 Production Deployment

### Docker Deployment

```bash
# Build image
docker build -t provider-registration-service:latest .

# Run container
docker run -d \
  --name provider-registration-service \
  --env-file .env \
  -p 5004:5004 \
  --network gan-shmuel-network \
  provider-registration-service:latest

# Verify health
curl http://localhost:5004/health
```

### Production Checklist

- [ ] Generate secure JWT_SECRET_KEY (`openssl rand -hex 32`)
- [ ] Set strong database passwords
- [ ] Run database migrations (`alembic upgrade head`)
- [ ] Configure HTTPS/TLS with reverse proxy
- [ ] Set up Prometheus monitoring
- [ ] Configure log aggregation
- [ ] Set up database backups
- [ ] Replace hardcoded admin with database users
- [ ] Enable rate limiting
- [ ] Configure CORS for production domains

See **[DEPLOYMENT.md](./DEPLOYMENT.md)** for detailed deployment guide.

## 🏗️ Architecture

### Technology Stack

- **Framework**: FastAPI 0.104+
- **Database**: PostgreSQL 14+ with asyncpg driver
- **Migrations**: Alembic 1.13+ with async support
- **Authentication**: JWT with python-jose and bcrypt
- **Validation**: Pydantic 2.4+
- **HTTP Client**: httpx with retry logic
- **Logging**: structlog (structured JSON logging)
- **Metrics**: prometheus-client
- **Testing**: pytest with pytest-asyncio

### Database Schema

```sql
CREATE TABLE candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(50),
    products JSONB,  -- Array of products (GIN indexed)
    truck_count INTEGER CHECK (truck_count > 0),
    capacity_tons_per_day INTEGER CHECK (capacity_tons_per_day > 0),
    location VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    provider_id INTEGER,  -- Reference to billing service
    version INTEGER DEFAULT 1 NOT NULL,  -- Optimistic locking
    rejection_reason TEXT,  -- Optional rejection reason
    CONSTRAINT status_check CHECK (status IN ('pending', 'approved', 'rejected'))
);
```

See **[MIGRATIONS.md](./MIGRATIONS.md)** for migration history and guide.

### Business Logic

#### Allowed Products
- apples, oranges, grapes, bananas, mangoes

#### Validation Rules
- `company_name`: Required, 1-255 characters
- `contact_email`: Required, valid email, unique
- `products`: At least 1 product from allowed list
- `truck_count`: Must be > 0
- `capacity_tons_per_day`: Must be > 0

#### Approval Workflow
1. Candidate registers (status='pending')
2. Admin reviews candidate details
3. Admin approves via POST /candidates/{id}/approve
4. Service creates provider in billing service
5. Service updates candidate status to 'approved' with provider_id
6. Returns approval response

#### Optimistic Locking
- Each candidate has a `version` field
- On update, version must match expected value
- Database trigger auto-increments version
- Prevents lost updates from concurrent modifications

### External Integrations

#### Billing Service Integration
- **Endpoint**: POST {BILLING_SERVICE_URL}/provider
- **Request**: `{"name": "Company Name"}`
- **Response**: `{"id": 123}`
- **Retry Logic**: Exponential backoff (0.5s, 1s, 2s)
- **Error Handling**: Returns 502 if billing service fails

### Observability

#### Prometheus Metrics
```promql
# Service uptime
provider_service_up

# Request rate
rate(provider_service_requests_total[5m])
```

#### Structured Logging
```json
{
  "event": "billing_service_request",
  "action": "create_provider",
  "company": "Fresh Fruit Ltd",
  "level": "info",
  "timestamp": "2025-10-27T10:00:00.000Z"
}
```

See **[OPERATIONS.md](./OPERATIONS.md)** for monitoring setup.

## 🔐 Security

### Authentication
- JWT tokens with HS256 algorithm
- 30-minute token expiration
- Admin role required for approval/rejection

### Default Admin Credentials (Development)
- **Username**: admin@example.com
- **Password**: admin123

⚠️ **WARNING**: Replace with database-backed user management in production.

### Security Features
- SQL injection protection (parameterized queries)
- Password hashing with bcrypt
- Optimistic locking for concurrency
- Secrets in environment variables
- Input validation with Pydantic

See **[SECURITY.md](./SECURITY.md)** for complete security documentation.

## 🐛 Troubleshooting

See **[OPERATIONS.md](./OPERATIONS.md)** for comprehensive troubleshooting guide including:

- Database connection issues
- JWT authentication failures
- Billing service integration problems
- Performance tuning
- Common deployment issues

## 📝 Version History

See **[CHANGELOG.md](./CHANGELOG.md)** for detailed version history.

**Current Version**: 1.0.0

## 📄 License

Part of the Gan Shmuel Industrial Weight Management System.

## 🔗 Related Services

- **Billing Service** - Provider billing and rate management (port 5002)
- **Weight Service** - Truck weighing operations (port 5001)
- **Shift Service** - Operator shift management (port 5003)
- **Frontend** - React application (port 3000)

## 📞 Support

- **API Documentation**: http://localhost:5004/docs
- **Health Check**: http://localhost:5004/health
- **Operations Guide**: [OPERATIONS.md](./OPERATIONS.md)
- **Security Issues**: security@gan-shmuel.com

---

**Last Updated**: 2025-10-27
**Maintained by**: Gan Shmuel DevOps Team
