# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Overview

This is the Gan Shmuel Industrial Weight Management System - a microservices architecture for handling truck weighing operations and billing for a juice factory. The system runs locally with Docker Compose and can be migrated to AWS using Terraform for cloud deployment. The system consists of six main components:

### Architecture Components

1. **Weight Service V2** (`weight-service/`) - FastAPI service handling truck weighing operations → @weight-service/CLAUDE.md
2. **Billing Service** (`billing-service/`) - FastAPI service for provider billing and rate management → @billing-service/CLAUDE.md
3. **Shift Service** (`shift-service/`) - FastAPI service for operator shift management and performance tracking → @shift-service/CLAUDE.md
4. **Provider Registration Service** (`provider-registration-service/`) - **PRODUCTION READY** FastAPI service for provider candidate registration, approval, and rejection workflows with JWT authentication, optimistic locking, and comprehensive security
5. **Frontend** (`frontend/`) - React TypeScript application with Material-UI → @frontend/CLAUDE.md
6. **Populate Data** (`populate-data/`) - Python service for populating test data across all services → @populate-data/README.md

## Quick Start Commands

For detailed development commands, refer to each service's specific CLAUDE.md file:
- Weight Service: @weight-service/CLAUDE.md
- Billing Service: @billing-service/CLAUDE.md
- Shift Service: @shift-service/CLAUDE.md
- Provider Registration Service: See documentation in `provider-registration-service/` (DEPLOYMENT.md, API.md, OPERATIONS.md, SECURITY.md)
- Frontend: @frontend/CLAUDE.md
- Populate Data: @populate-data/README.md

### System-wide Commands
```bash
# Start all services with Docker Compose
docker-compose up -d

# Populate test data (fast mode)
docker-compose --profile populate up populate-data

# Populate test data (realistic mode with timing delays)
docker-compose --profile populate run populate-data --realistic

# Start monitoring stack
docker-compose up -d prometheus grafana
```

### Cloud Migration
The system is designed for easy cloud migration to AWS using Terraform. Basic cloud deployment uses EC2 instances with ALB for simple, compatible infrastructure that works across different AWS account types.

## Core Business Logic

### Weight Calculation Formula
The system implements the core weighing business rule:
```
Bruto (Gross Weight) = Neto (Net Fruit) + Truck Tara + Σ(Container Tara)
```

### Weighing Process Flow (Session-Based)
1. **Truck enters** → POST /weight (direction=in) → Records gross weight, creates session
2. **Truck unloads** containers with fruit  
3. **Truck exits** → POST /weight (direction=out) → Records tare weight, calculates net fruit
4. **System calculates** net fruit weight using container weights and links transactions via session ID

### Billing Rate Logic
- Provider-specific rates override general rates (scope precedence)
- Bill calculation: `Neto weight × rate = payment amount`
- Only processes transactions for provider's registered trucks

### Shift Management Logic
- **Operator Tracking**: Associates weighing operations with specific operators
- **Performance Metrics**: Real-time calculation of throughput, processing times, and error rates
- **Shift Handoffs**: Comprehensive reports for seamless operator transitions
- **Redis Caching**: Current shift state cached for fast lookups

### Provider Registration Logic
- **Candidate Workflow**: Register → Approve/Reject → Provider created in billing
- **JWT Authentication**: Admin-only access with role-based access control (RBAC)
- **Optimistic Locking**: Version-based concurrency control prevents race conditions
- **Dual Pagination**: Supports both page/page_size and limit/offset formats
- **Rejection Workflow**: Optional rejection reason with audit trail
- **Database Migrations**: Alembic for schema version control
- **Production Ready**: 69/69 tests passing, >90% coverage, comprehensive documentation

## Architecture Patterns

### Service Architecture
```
Weight Service ←→ Billing Service ←→ Provider Registration ←→ Frontend
     ↓                 ↓                      ↓                    ↓
   MySQL            MySQL              PostgreSQL             Browser
   (5001)           (5002)                (5004)               (3000)
     ↑                 ↑                      ↑                    ↑
Shift Service ←→ Redis Cache                  │                   │
     ↓                                        │                   │
   MySQL                                      │                   │
   (5003)                                     │                   │
     ↑                                        │                   │
     └─── Prometheus ←──────────── Grafana ←─┴───────────────────┘
          (9090)                    (3001)
```

### Data Flow Integration
- **Weight Service** → Provides weighing data via REST API
- **Billing Service** → Fetches weight data for bill generation and manages providers
- **Provider Registration Service** → Candidate registration, approval creates providers in billing service
- **Shift Service** → Tracks operator performance and shift management with Redis caching
- **Frontend** → Communicates with all services via API calls
- **Prometheus** → Scrapes metrics from all services for monitoring and alerting
- **Grafana** → Visualizes metrics and provides operational dashboards
- Services use FastAPI with automatic OpenAPI documentation at `/docs`

### Repository Pattern
All Python services implement clean architecture:
- `src/routers/` - FastAPI route handlers
- `src/services/` - Business logic and orchestration
- `src/models/repositories.py` - Data access layer with repository pattern
- `src/models/schemas.py` - Pydantic models for validation
- Custom exception handling with proper HTTP status codes

### Frontend Architecture
- **React 18** with TypeScript and Vite build system
- **Material-UI (MUI)** for consistent design system
- **TanStack Query** for API state management, caching, and optimistic updates
- **React Router v6** for client-side routing
- Modular component structure organized by feature (`src/components/weight/`, `src/components/billing/`, `src/components/shift/`)

## Key Technical Implementation Details

### Database Design
- **Weight Service**: Uses SQLAlchemy 2.0 with Alembic migrations, stores weighing transactions and container weights
- **Billing Service**: MySQL with connection pooling, stores providers, trucks, rates, and billing data
- **Shift Service**: MySQL with SQLAlchemy, tracks operators, shifts, and performance metrics with Redis caching
- **Provider Registration Service**: PostgreSQL with async SQLAlchemy, stores candidates with version-based optimistic locking, Alembic migrations for schema version control
- Session-based transaction linking for IN/OUT weighing pairs

### File Processing
- **Container Weights**: Batch upload via CSV/JSON files in `/in` directory
- **Rate Management**: Excel file upload/download for pricing rates
- **Error Handling**: Unknown containers tracked and reported

### API Integration Patterns
- **Retry Logic**: Billing service includes exponential backoff for Weight service calls
- **Health Checks**: All services expose `/health` endpoints for monitoring
- **Date Range Filtering**: Efficient querying with `from`/`to` timestamp parameters

## Testing Strategy

### Python Services
- **pytest** with async support (`pytest-asyncio`)
- **Coverage reporting** with `pytest-cov` and HTML reports
- **Integration tests** for API endpoints with real database fixtures
- **Business scenario tests** for complex workflows
- **Performance tests** for batch operations

### Frontend Testing
- **Vitest** as test runner with Jest-compatible API
- **React Testing Library** for component testing
- **MSW (Mock Service Worker)** for API mocking
- **Coverage reporting** with v8 coverage

### Development Workflow Requirements
- **Type checking is mandatory** (mypy for Python, TypeScript strict mode)
- **Code formatting enforced** (Ruff for Weight service, Black/isort for Billing service, ESLint for frontend)
- **Test coverage required** for new features
- **Docker environments** for consistent development setup

## Service Integration

### External Service Communication
```
Billing Service → Weight Service
GET /weight?from={date}&to={date}     # Fetch transactions for billing
GET /item/{truck_id}                  # Get truck details and sessions

Provider Registration Service → Billing Service
POST /providers                        # Create provider on candidate approval

Shift Service → Weight Service
GET /weight?from={date}&to={date}     # Fetch transactions for metrics calculation

Frontend → All Services
Weight Service: /weight, /batch, /query endpoints
Billing Service: /bills, /providers, /trucks, /rates endpoints
Provider Registration: /candidates, /auth, /approve, /reject endpoints (with JWT auth)
Shift Service: /shifts, /operators endpoints
```

### File System Integration
- Services expect `/in` directory mounted for file uploads
- Container weight files: `containers.csv`, `containers.json`
- Rate files: Excel format with Product, Rate, Scope columns

## Monitoring and Observability

### Prometheus Metrics
All services expose Prometheus metrics at `/metrics` endpoint:
- **Request counts and latencies** for all HTTP endpoints
- **Database connection pool metrics** and query performance
- **Business metrics** (transactions processed, bills generated, shift performance)
- **Custom application metrics** specific to each service's domain

### Monitoring Stack
- **Prometheus** (port 9090): Metrics collection and storage with 200h retention
- **Grafana** (port 3001): Dashboards and visualization (admin/admin credentials)
- **Service Discovery**: Prometheus auto-discovers services via Docker network

### Development Commands
```bash
# Start monitoring stack
docker-compose up -d prometheus grafana

# View metrics
curl http://localhost:5001/metrics  # Weight service metrics
curl http://localhost:5002/metrics  # Billing service metrics
curl http://localhost:5003/metrics  # Shift service metrics
curl http://localhost:5004/metrics  # Provider registration metrics

# Access monitoring
open http://localhost:9090          # Prometheus UI
open http://localhost:3001          # Grafana dashboards
```

## Service Ports and Endpoints
- **Weight Service**: 5001 (`/docs` for API documentation, `/metrics` for Prometheus)
- **Billing Service**: 5002 (`/docs` for API documentation, `/metrics` for Prometheus)
- **Shift Service**: 5003 (`/docs` for API documentation, `/metrics` for Prometheus)
- **Provider Registration Service**: 5004 (`/docs` for API documentation, `/metrics` for Prometheus, `/auth/login` for JWT)
- **Frontend**: 3000
- **Prometheus**: 9090 (metrics collection and queries)
- **Grafana**: 3001 (dashboards and visualization)
- **MySQL (Weight)**: 3306
- **MySQL (Billing)**: 3307
- **MySQL (Shift)**: 3308
- **PostgreSQL (Provider Registration)**: 5432
- **Redis (Shift Cache)**: 6379

## Important Implementation Notes
- **Session Management**: Weight transactions linked by session IDs for IN/OUT pairs
- **Force Mode**: Weight service supports bypassing business rules with `force: true`
- **Unknown Container Tracking**: System identifies and reports containers without tara weights
- **Rate Precedence**: Provider-specific rates override general rates based on scope
- **Excel Processing**: Comprehensive Excel file handling for rate management
- **CORS Configuration**: Properly configured for frontend-backend communication
- **Error Recovery**: Retry patterns and graceful degradation for service communication
- **Shift Performance**: Real-time metrics calculation with Redis caching for optimal performance
- **Operator Management**: Role-based access with weigher, supervisor, and admin permissions
- **Observability**: Comprehensive metrics collection with Prometheus and visualization via Grafana dashboards
- **Monitoring Integration**: All services expose standardized metrics for operational monitoring
- **Provider Registration**: JWT authentication with HS256, optimistic locking for concurrency, Alembic migrations for schema control
- **Production Ready**: Provider Registration Service is production-ready with 69/69 tests passing, >90% coverage, comprehensive documentation (see DEPLOYMENT.md, API.md, OPERATIONS.md, SECURITY.md)
- **Security Features**: SQL injection prevention via parameterized queries, admin-only approval/rejection, bcrypt password hashing, token expiration (30 min)