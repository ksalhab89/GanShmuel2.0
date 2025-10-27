# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Overview

This is the Gan Shmuel Industrial Weight Management System - a microservices architecture for handling truck weighing operations and billing for a juice factory. The system runs locally with Docker Compose and can be migrated to AWS using Terraform for cloud deployment.

**GitHub Repository**: https://github.com/ksalhab89/GanShmuel2.0

The system consists of five main services plus supporting infrastructure:

### Architecture Components

#### Core Services
1. **Weight Service V2** (`weight-service/`) - FastAPI service handling truck weighing operations → @weight-service/CLAUDE.md
2. **Billing Service** (`billing-service/`) - FastAPI service for provider billing and rate management → @billing-service/CLAUDE.md
3. **Shift Service** (`shift-service/`) - FastAPI service for operator shift management and performance tracking → @shift-service/CLAUDE.md
4. **Provider Registration Service** (`provider-registration-service/`) - **PRODUCTION READY** FastAPI service for provider candidate registration, approval, and rejection workflows with JWT authentication, optimistic locking, and comprehensive security
5. **Frontend** (`frontend/`) - React TypeScript application with Material-UI and real-time health monitoring → @frontend/CLAUDE.md

#### Supporting Infrastructure
- **API Gateway** (`infrastructure/gateway/`) - Traefik v3.0 as single entry point on port 80
- **Monitoring** (`infrastructure/monitoring/`) - Prometheus + Grafana stack
- **Populate Data** (`populate-data/`) - Python service for populating test data → @populate-data/README.md

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

### API Gateway Architecture (Traefik v3.0)

**Single Entry Point - Port 80 Only**

All external traffic flows through Traefik API Gateway on port 80. Backend service ports (5001-5004, 3000) are NOT exposed externally for security.

```
External Users (Browser)
         │
         ▼
   API Gateway (Traefik :80)  ◄── ONLY PORT EXPOSED
         │
    ┌────┴────┬────────┬────────┬────────┐
    ▼         ▼        ▼        ▼        ▼
  Frontend  Weight  Billing  Shift  Provider
   :3000    :5001    :5002   :5003    :5004
    │         │        │        │        │
    │    ┌───┴────────┴────────┴────────┘
    │    │  (Services communicate directly via Docker network)
    │    │
    ▼    ▼
  Browser View + Backend APIs
```

**Gateway Routes:**
- `http://localhost/` → Frontend (React app)
- `http://localhost/api/weight/*` → Weight Service (strips `/api/weight` prefix)
- `http://localhost/api/billing/*` → Billing Service (strips `/api/billing` prefix)
- `http://localhost/api/shift/*` → Shift Service (strips `/api/shift` prefix)
- `http://localhost/api/provider/*` → Provider Service (strips `/api/provider` prefix)

**CRITICAL**: All FastAPI services MUST include `root_path` parameter for OpenAPI docs to work:
```python
app = FastAPI(
    title="Service Name",
    root_path="/api/servicename",  # REQUIRED for Swagger UI behind gateway
    docs_url="/docs",
)
```

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
- **Real-time Health Monitoring**: Landing page displays live health status for all services
  - Auto-refreshes every 10 seconds without page reload
  - Color-coded status chips: Green (healthy), Red (down), Gray (checking)
  - Uses Material-UI CheckCircle, Error, and HelpOutline icons
- **Nginx Deployment**: Multi-stage Docker build with nginx serving static files
  - Build stage: Node.js compiles React/TypeScript to static assets
  - Runtime stage: nginx:alpine serves files (lightweight, production-ready)
  - Cache-busting configured: HTML never cached, JS/CSS cached forever with content hashes
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

### External Access (Via API Gateway - Port 80)
**All user traffic goes through port 80:**
- `http://localhost/` → Frontend landing page with health monitoring
- `http://localhost/api/weight/*` → Weight Service
- `http://localhost/api/billing/*` → Billing Service
- `http://localhost/api/shift/*` → Shift Service
- `http://localhost/api/provider/*` → Provider Registration Service

**API Documentation (via gateway):**
- `http://localhost/api/weight/docs` - Weight Service Swagger UI
- `http://localhost/api/billing/docs` - Billing Service Swagger UI
- `http://localhost/api/shift/docs` - Shift Service Swagger UI
- `http://localhost/api/provider/docs` - Provider Registration Swagger UI

**Monitoring & Operations:**
- `http://localhost:9999/dashboard/` - Traefik Dashboard (API Gateway)
- `http://localhost:9090` - Prometheus UI
- `http://localhost:3001` - Grafana (admin/admin)

### Internal Ports (NOT Exposed Externally - Docker Network Only)
- **Weight Service**: 5001 (internal only)
- **Billing Service**: 5002 (internal only)
- **Shift Service**: 5003 (internal only)
- **Provider Registration Service**: 5004 (internal only)
- **Frontend**: 3000 (internal only - access via gateway on port 80)
- **MySQL (Weight)**: 3306 (internal only)
- **MySQL (Billing)**: 3307 (internal only)
- **MySQL (Shift)**: 3308 (internal only)
- **PostgreSQL (Provider Registration)**: 5432 (internal only)
- **Redis (Shift Cache)**: 6379 (internal only)

## CI/CD Pipeline (`.github/` Directory)

The repository includes comprehensive GitHub Actions workflows for continuous integration, security scanning, and deployment automation.

### Workflow Files Overview

#### 1. **Test Suite** (`.github/workflows/test.yml`)
**Triggers:** Push/PR to main/develop branches

**Jobs:**
- **weight-service**: Python 3.11, MySQL 8.0, uv package manager
  - Type checking (mypy)
  - Linting (ruff)
  - Tests with >95% coverage requirement
  - Uploads coverage to Codecov

- **billing-service**: Python 3.11, MySQL 8.0, uv package manager
  - Type checking (mypy)
  - Linting (flake8)
  - Code formatting check (black)
  - Import sorting check (isort)
  - Tests with >90% coverage requirement
  - Uploads coverage to Codecov

- **shift-service**: Python 3.11, MySQL 8.0 + Redis 7, uv package manager
  - Type checking (mypy)
  - Linting (ruff)
  - Tests with >90% coverage requirement
  - Uploads coverage to Codecov

- **frontend**: Node.js 18, npm
  - Type checking (TypeScript)
  - Linting (ESLint)
  - Tests with coverage (Vitest)
  - Uploads coverage to Codecov

- **integration-tests**: Full Docker Compose stack
  - Starts all services with Docker Compose
  - Waits for health checks
  - Runs end-to-end integration tests
  - Shows service logs on failure

- **quality-gate**: Final check that all tests passed

#### 2. **Security Scanning** (`.github/workflows/security-scan.yml`)
**Triggers:** Push/PR, Daily at 2 AM UTC, Manual dispatch

**Jobs:**
- **trivy-docker-scan**: Scans Docker images for vulnerabilities
  - Matrix build for all 5 services
  - Scans for CRITICAL and HIGH severity issues
  - Uploads SARIF reports to GitHub Security tab
  - Generates summary in job output

- **trivy-filesystem-scan**: Scans source code for vulnerabilities
  - Full repository scan
  - Uploads results to GitHub Security tab

- **python-dependency-scan**: Scans Python dependencies
  - Uses pip-audit and Safety tools
  - Matrix scan for all 4 Python services
  - Generates markdown reports
  - Uploads artifacts

- **trufflehog-secrets-scan**: Scans for leaked secrets
  - Full git history scan
  - Only reports verified secrets
  - Integrates with TruffleHog

- **gitguardian-scan**: Alternative secrets scanner
  - Requires GITGUARDIAN_API_KEY secret
  - Scans git history for exposed credentials

- **config-security-scan**: Checks configuration files
  - Scans docker-compose.yml for security issues
  - Checks for privileged containers
  - Checks for host network mode
  - Detects hardcoded secrets
  - Validates security_opt settings

- **security-summary**: Aggregates all scan results

**SARIF Integration:** All security scan results are uploaded to GitHub's Security tab for centralized vulnerability management.

#### 3. **Build and Deploy** (`.github/workflows/deploy.yml`)
**Triggers:** Push to main, version tags (v*.*.*), Manual dispatch

**Container Registry:** GitHub Container Registry (ghcr.io)

**Jobs:**
- **build-images**: Matrix build for all 5 services
  - Builds Docker images with Buildx
  - Pushes to ghcr.io
  - Smart tagging:
    - Branch name (e.g., main)
    - Semantic version (e.g., v1.0.0, v1.0, v1)
    - Git SHA (e.g., main-abc1234)
    - Latest (for default branch)
  - Layer caching for faster builds
  - Generates build summary

- **pre-deployment-tests**: Runs integration tests before deployment

- **deploy-staging**: Automatic deployment to staging
  - Triggers on main branch push
  - Environment: staging
  - SSH deployment example
  - Runs smoke tests
  - No manual approval required

- **deploy-production**: Manual approval required
  - Triggers on version tags (v*.*.*)
  - Environment: production
  - Requires manual approval in GitHub UI
  - SSH deployment example
  - Health checks after deployment
  - Notifications on success/failure

- **rollback**: Manual rollback capability
  - Workflow dispatch only
  - Can rollback staging or production
  - Uses previous git tag

- **deployment-summary**: Aggregates deployment status

**AWS Integration Ready:** Workflows include commented-out AWS configuration for future cloud deployment.

#### 4. **Coverage Report** (`.github/workflows/coverage-report.yml`)
**Purpose:** Generates and uploads test coverage reports

**Features:**
- Runs after test suite completes
- Consolidates coverage from all services
- Uploads to Codecov with service-specific flags
- Generates coverage badges for README

#### 5. **Performance Testing** (`.github/workflows/performance.yml`)
**Purpose:** Load testing and performance benchmarking

**Features:**
- Runs performance tests on services
- Benchmarks API response times
- Tracks performance trends over time
- Fails if performance degrades beyond threshold

#### 6. **Dependabot** (`.github/dependabot.yml`)
**Purpose:** Automated dependency updates

**Configuration:**
- Monitors Python dependencies (pip)
- Monitors npm dependencies
- Monitors Docker base images
- Monitors GitHub Actions versions
- Opens PRs for security updates

### Required GitHub Secrets

For full CI/CD functionality, configure these secrets:

```yaml
# Optional (for deployment)
AWS_ROLE_ARN                  # AWS role for staging deployment
AWS_PROD_ROLE_ARN             # AWS role for production deployment
DEPLOYMENT_SSH_KEY            # SSH key for server access

# Optional (for enhanced security scanning)
GITGUARDIAN_API_KEY           # GitGuardian API key for secret scanning

# Auto-configured by GitHub
GITHUB_TOKEN                  # Automatically provided by GitHub Actions
```

### GitHub Environments

**Staging Environment:**
- Auto-deploys on main branch push
- URL: https://staging.gan-shmuel.example.com
- No approval required
- Used for QA and testing

**Production Environment:**
- Requires manual approval
- Triggered by version tags (v*.*.*)
- URL: https://gan-shmuel.example.com
- Protected environment
- Approval from designated reviewers required

### Workflow Features

**Quality Gates:**
- All tests must pass before deployment
- Coverage thresholds enforced (90-95%)
- Security scans must complete
- Type checking required
- Code formatting validated

**Notifications:**
- Job summaries in GitHub UI
- SARIF reports in Security tab
- Coverage reports in Codecov
- Deployment status notifications

**Performance:**
- Layer caching for Docker builds
- Parallel job execution where possible
- Matrix strategy for service builds
- Cached npm/pip dependencies

### Monitoring & Observability

- **Security Tab**: View all vulnerability scans (Trivy, dependency scanning)
- **Actions Tab**: View workflow runs, logs, and job summaries
- **Packages**: View Docker images in GitHub Container Registry
- **Codecov Integration**: Track coverage trends over time

## Important Implementation Notes

### API Gateway (Traefik)
- **Single Entry Point**: All traffic via port 80 (HTTP) - backend ports not exposed
- **Path Stripping**: Gateway strips `/api/{service}` prefix before forwarding
- **FastAPI root_path**: ALL services MUST set `root_path="/api/servicename"` for Swagger docs to work
- **Service Discovery**: Auto-discovers services via Docker labels
- **Dashboard**: Real-time monitoring at http://localhost:9999/dashboard/

### Frontend
- **Real-time Health Monitoring**: Landing page auto-refreshes service health every 10s
- **Nginx Deployment**: Multi-stage Docker build (Node.js build → nginx serve)
- **Cache-Busting**: HTML never cached (no-store), JS/CSS cached forever with content hashes
- **Material-UI**: Consistent design with health status chips (green/red/gray indicators)

### Docker Build
- **Weight Service**: `.dockerignore` excludes `alembic/` directory (migrations run separately)
- **DO NOT** try to `COPY alembic/` in Dockerfile - it will fail
- All services use multi-stage builds with `uv` package manager
- Production images run as non-root `appuser` for security

### Git Repository
- **Excluded from Git**: `.env` files, `.claude/` directory, `__pycache__/`, `node_modules/`, Docker volumes
- **Included in Git**: `.env.example` templates, `.mcp.json` (uses env vars, no secrets), all source code
- **README.md**: Professional GitHub-friendly documentation with badges and quick start

### Business Logic
- **Session Management**: Weight transactions linked by session IDs for IN/OUT pairs
- **Force Mode**: Weight service supports bypassing business rules with `force: true`
- **Unknown Container Tracking**: System identifies and reports containers without tara weights
- **Rate Precedence**: Provider-specific rates override general rates based on scope
- **Excel Processing**: Comprehensive Excel file handling for rate management

### Security & Operations
- **CORS Configuration**: Properly configured for frontend-backend communication
- **Error Recovery**: Retry patterns and graceful degradation for service communication
- **Shift Performance**: Real-time metrics calculation with Redis caching for optimal performance
- **Operator Management**: Role-based access with weigher, supervisor, and admin permissions
- **Observability**: Comprehensive metrics collection with Prometheus and visualization via Grafana dashboards
- **Monitoring Integration**: All services expose standardized metrics at `/metrics` endpoint
- **Provider Registration**: JWT authentication with HS256, optimistic locking for concurrency, Alembic migrations for schema control
- **Production Ready**: Provider Registration Service is production-ready with 69/69 tests passing, >90% coverage, comprehensive documentation (see DEPLOYMENT.md, API.md, OPERATIONS.md, SECURITY.md)
- **Security Features**: SQL injection prevention via parameterized queries, admin-only approval/rejection, bcrypt password hashing, token expiration (30 min)