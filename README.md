# 🏭 Gan Shmuel Weight Management System

> Enterprise-grade microservices architecture for industrial weight management and billing operations

[![Portfolio Project](https://img.shields.io/badge/portfolio-demo--ready-brightgreen.svg)](https://github.com/ksalhab89/GanShmuel2.0)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?logo=github-actions&logoColor=white)](https://github.com/ksalhab89/GanShmuel2.0/actions)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.120+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Technology Stack](#-technology-stack)
- [Services](#-services)
- [API Documentation](#-api-documentation)
- [Monitoring](#-monitoring)
- [Security](#-security)
- [Testing](#-testing)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

The Gan Shmuel Weight Management System is a comprehensive solution for managing industrial weighing operations at a juice factory. It handles truck weighing sessions, provider billing, shift management, and provider registration through a secure, scalable microservices architecture.

**💼 DevOps Portfolio Project** - Demonstrates production-ready patterns with one-command local setup

### Key Capabilities

- 🚛 **Weight Management**: Session-based truck weighing with IN/OUT tracking
- 💰 **Billing System**: Automated billing with provider-specific rates
- 👥 **Shift Management**: Operator performance tracking and shift handoffs
- 🏢 **Provider Registration**: Candidate approval workflow with admin panel
- 📊 **Real-time Monitoring**: Prometheus metrics + Grafana dashboards
- 🔒 **Enterprise Security**: Rate limiting, API gateway, vulnerability scanning

---

## ✨ Features

### Core Functionality
- ✅ **Microservices Architecture** - 4 independent backend services
- ✅ **API Gateway (Traefik v3)** - Single entry point, load balancing ready
- ✅ **Real-time Health Monitoring** - Live status indicators on landing page
- ✅ **Session-based Weighing** - Links IN/OUT transactions for accurate net weight
- ✅ **Automated Billing** - Calculates payments using provider-specific rates
- ✅ **Excel Integration** - Upload/download rate sheets

### Production Features
- 🌐 **API Gateway** - Traefik v3 with automatic service discovery
- 🛡️ **Rate Limiting** - Redis-backed DDoS protection
- 📈 **Monitoring Stack** - Prometheus + Grafana with 200h retention
- 🔐 **Security Scanning** - Trivy v0.33.1, TruffleHog v3.90.11, GitGuardian v1.37.0
- 🚀 **CI/CD Pipeline** - Production-grade GitHub Actions with quality gates
- 🐳 **Container Registry** - GitHub Container Registry (ghcr.io)
- 📊 **Metrics & Alerts** - Business and infrastructure metrics
- 🔧 **Reproducible Builds** - UV package manager with version pinning

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     EXTERNAL USERS                          │
│                   (Internet / Browser)                      │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/HTTPS
                         ▼
                ┌────────────────┐
                │  API GATEWAY   │  ← ONLY PORT EXPOSED: 80
                │  (Traefik v3)  │
                └───┬────────────┘
                    │
    ┌───────────────┼───────────────┬───────────────┐
    │               │               │               │
    ▼               ▼               ▼               ▼
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ Weight  │    │ Billing │    │ Shift   │    │Provider │
│ Service │    │ Service │    │ Service │    │ Service │
│  :5001  │    │  :5002  │    │  :5003  │    │  :5004  │
└────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘
     │              │              │              │
     ▼              ▼              ▼              ▼
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│Weight DB│    │Billing  │    │Shift DB │    │Provider │
│ MySQL   │    │  DB     │    │+ Redis  │    │  DB     │
└─────────┘    │ MySQL   │    └─────────┘    │Postgres │
               └─────────┘                    └─────────┘
```

### Security Architecture

**Attack Surface Reduced from 5 Ports to 1**

- ✅ **External Access**: Only API Gateway exposed (port 80)
- ✅ **Internal Services**: Communicate via Docker network only
- ✅ **Databases**: Never exposed externally
- ✅ **Rate Limiting**: Redis-backed protection on all endpoints
- ✅ **Security Scanning**: Daily automated scans

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Git
- 8GB RAM minimum (recommended 16GB)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ksalhab89/GanShmuel2.0.git
   cd GanShmuel2.0
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start all services**
   ```bash
   docker-compose up -d
   ```

4. **Populate test data (optional)**
   ```bash
   # Fast mode
   docker-compose --profile populate up populate-data

   # Realistic mode (simulates actual operations)
   docker-compose --profile populate run populate-data --realistic
   ```

### Access the System

**Everything runs through port 80:**

```bash
# Landing Page with Real-time Health Monitoring
open http://localhost/

# Backend Health Checks
curl http://localhost/api/weight/health
curl http://localhost/api/billing/health
curl http://localhost/api/shift/health
curl http://localhost/api/provider/health

# Monitoring & Operations
open http://localhost:9999/dashboard/  # Traefik Dashboard (credentials: see below)
open http://localhost:9090             # Prometheus
open http://localhost:3001             # Grafana (admin/admin)
```

---

## 🛠️ Technology Stack

### Backend Services
- **Framework**: FastAPI (Python 3.11)
- **Package Manager**: UV (pinned v0.5.20)
- **Databases**: MySQL 8.0, PostgreSQL 15, Redis 7
- **ORM**: SQLAlchemy 2.0 with async support
- **Migrations**: Alembic
- **Testing**: pytest with pytest-asyncio, >90% coverage
- **Validation**: Pydantic v2
- **Rate Limiting**: SlowAPI + Redis

### Infrastructure
- **API Gateway**: Traefik v3.0
- **Containerization**: Docker & Docker Compose (18 services)
- **Monitoring**: Prometheus + Grafana
- **Security Scanning**: Trivy v0.33.1, TruffleHog v3.90.11, GitGuardian v1.37.0
- **CI/CD**: GitHub Actions (production-grade workflows with quality gates)
- **Container Registry**: GitHub Container Registry (ghcr.io)
- **Package Manager**: UV with version pinning for reproducible builds

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **UI Library**: Material-UI (MUI)
- **State Management**: TanStack Query (React Query)
- **Routing**: React Router v6

---

## 📦 Services

| Service | Port | Database | Gateway Route | Description |
|---------|------|----------|---------------|-------------|
| **Weight Service** | 5001* | MySQL | `/api/weight/*` | Truck weighing operations & session management |
| **Billing Service** | 5002* | MySQL | `/api/billing/*` | Provider billing & rate management |
| **Shift Service** | 5003* | MySQL + Redis | `/api/shift/*` | Operator shift management & performance |
| **Provider Service** | 5004* | PostgreSQL | `/api/provider/*` | Candidate registration & approval workflow |
| **Frontend** | 3000* | - | `/` | React app with real-time health monitoring |

\* Ports not exposed externally - access via API Gateway (port 80) only

### Service Dependencies

```
Provider Service → Billing Service → Weight Service
                                   ↑
                     Shift Service ─┘
```

---

## 📚 API Documentation

Interactive OpenAPI/Swagger documentation available for all services:

```
http://localhost/api/weight/docs
http://localhost/api/billing/docs
http://localhost/api/shift/docs
http://localhost/api/provider/docs
```

### Example API Calls

**Weight Service:**
```bash
# Create weighing session (truck entering)
curl -X POST http://localhost/api/weight/ \
  -H "Content-Type: application/json" \
  -d '{"direction":"in","bruto":15000,"truck_id":"ABC123","containers":["C1","C2"],"produce":"orange"}'

# Get weighing sessions
curl http://localhost/api/weight/?from=2025-01-01&to=2025-12-31
```

**Billing Service:**
```bash
# Upload rates from Excel
curl -X POST http://localhost/api/billing/rates/upload \
  -F "file=@rates.xlsx"

# Generate bill for provider
curl -X POST http://localhost/api/billing/bills/ \
  -H "Content-Type: application/json" \
  -d '{"provider_id":1,"from":"2025-01-01","to":"2025-01-31"}'
```

---

## 📊 Monitoring

### Prometheus Metrics

All services expose metrics at `/metrics` endpoint:

- Request counts and latencies
- Database connection pool metrics
- Business metrics (transactions, bills, shifts)
- Custom application metrics

Access Prometheus UI: **http://localhost:9090**

### Grafana Dashboards

Pre-configured dashboards for:

- Service health and uptime
- Request rates and error rates
- Database performance
- Business KPIs

Access Grafana: **http://localhost:3001** (admin/admin)

### Traefik Dashboard

Monitor API Gateway routing and traffic:

**http://localhost:9999/dashboard/**

**Login**: Username `admin` - Password in `infrastructure/gateway/TRAEFIK_CREDENTIALS.txt`

---

## 🔒 Security

### Rate Limiting Tiers

```python
PUBLIC        = "10 per minute"   # Unauthenticated endpoints
AUTH_LOGIN    = "5 per minute"    # Prevent brute force
AUTH_REGISTER = "3 per minute"    # Prevent spam
READ_LIGHT    = "100 per minute"  # Health checks, status
READ_HEAVY    = "30 per minute"   # Lists, searches
WRITE_LIGHT   = "50 per minute"   # Single record writes
WRITE_HEAVY   = "10 per minute"   # Batch operations
ADMIN         = "20 per minute"   # Admin operations
```

### Security Scanning

Automated daily scans for:

- ✅ **Docker Images**: Trivy vulnerability scanning
- ✅ **Python Dependencies**: pip-audit + Safety
- ✅ **Secrets Detection**: TruffleHog + GitGuardian
- ✅ **Configuration**: Docker Compose validation

### Best Practices

- Never commit `.env` files
- Use strong passwords (min 16 characters)
- Rotate credentials regularly
- Enable HTTPS in production (Let's Encrypt)
- Use secrets manager (Vault, AWS Secrets Manager)

---

## 🧪 Testing

### Run Tests

```bash
# Provider Registration Service (69/69 tests)
cd provider-registration-service
pytest tests/ -v --cov=src --cov-report=html

# Weight Service
cd weight-service
pytest tests/ -v

# Billing Service
cd billing-service
pytest tests/ -v
```

### Test Coverage

- **Provider Service**: >90% coverage, 69/69 tests passing
- **Integration Tests**: End-to-end API workflows
- **Performance Tests**: Concurrent request handling
- **Security Tests**: SQL injection, XSS prevention

---

## 📖 Business Logic

### Weight Calculation Formula

```
Bruto (Gross Weight) = Neto (Net Fruit) + Truck Tara + Σ(Container Tara)
```

### Weighing Process

1. **Truck enters** → POST `/weight` (direction=in) → Records gross weight, creates session
2. **Truck unloads** containers
3. **Truck exits** → POST `/weight` (direction=out) → Records tare weight
4. **System calculates** net fruit weight using session ID

### Billing Rate Logic

- Provider-specific rates override general rates (scope precedence)
- Bill calculation: `Neto weight × rate = payment amount`
- Only processes transactions for provider's registered trucks

### Provider Registration Workflow

1. **Candidate submits** application → POST `/candidates`
2. **Admin reviews** candidates → GET `/candidates`
3. **Admin approves** → POST `/candidates/{id}/approve` → Auto-creates provider in billing service
4. **Admin rejects** → POST `/candidates/{id}/reject` (optional rejection reason)

---

## 🛠️ Development

### Project Structure

```
gan-shmuel-2/
├── infrastructure/           # Gateway, monitoring, scripts
│   ├── gateway/             # Traefik configuration
│   ├── monitoring/          # Prometheus + Grafana
│   └── scripts/             # Operational scripts
├── .github/workflows/       # CI/CD pipelines
├── weight-service/          # Weight management
├── billing-service/         # Billing & providers
├── shift-service/           # Shift management
├── provider-registration-service/  # Provider registration
├── frontend/                # React TypeScript app
├── populate-data/           # Test data generator
├── docker-compose.yml       # Service orchestration
└── .env.example            # Environment template
```

### Common Operations

```bash
# View logs
docker-compose logs -f weight-service

# Restart service
docker-compose restart billing-service

# Rebuild service
docker-compose up -d --build weight-service

# Stop all services
docker-compose down

# Clean restart (remove volumes)
docker-compose down -v && docker-compose up -d
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow existing code style (Black for Python, ESLint for TypeScript)
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting PR
- Keep commits atomic and well-described

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **FastAPI** - Modern, fast web framework
- **Traefik** - Cloud-native API gateway
- **Prometheus + Grafana** - Monitoring excellence
- **SlowAPI** - Elegant rate limiting
- **Trivy** - Comprehensive security scanning
- **GitHub Actions** - Flexible CI/CD platform

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/ksalhab89/GanShmuel2.0/issues)
- **API Docs**: Available at `/docs` endpoint for each service

---

## 🎯 DevOps Features Demonstrated

### Core Features ✅
- [x] **Microservices Architecture** - 18-container orchestration
- [x] **API Gateway** - Traefik v3 with service discovery
- [x] **Container Orchestration** - Docker Compose with health checks
- [x] **Monitoring Stack** - Prometheus + Grafana with metrics
- [x] **Security** - Rate limiting, vulnerability scanning, security headers
- [x] **CI/CD Pipeline** - Production-grade GitHub Actions workflows
- [x] **Real-time Health Monitoring** - Live service status dashboard
- [x] **One-Command Setup** - `docker-compose up -d` to start everything

### CI/CD Pipeline Quality 🚀
- **Code Quality Gates** - Type checking, linting, formatting enforced
- **Security Scanning** - Trivy, TruffleHog, GitGuardian with pinned versions
- **Test Coverage** - >90% coverage requirement, 69/69 tests passing
- **Dependency Pinning** - UV v0.5.20 for reproducible builds
- **Optimized Startup** - Health check polling instead of arbitrary waits
- **Build Caching** - Docker layer caching for faster CI runs

### Technical Highlights 🎯
- **API Gateway Pattern** - Single entry point for all services
- **Service Mesh Concepts** - Internal service communication
- **Observability** - Metrics, health checks, dashboards
- **Security Hardening** - Attack surface reduction, automated scanning
- **Infrastructure as Code** - Complete docker-compose configuration
- **Testing** - 69/69 tests passing, >90% coverage

> **Demo & Credentials**: See [PORTFOLIO_SHOWCASE.md](PORTFOLIO_SHOWCASE.md) for access details and system walkthrough

---

<div align="center">

**🚀 Production-Ready System | Built with ❤️ using FastAPI + React**

[![GitHub Stars](https://img.shields.io/github/stars/ksalhab89/GanShmuel2.0?style=social)](https://github.com/ksalhab89/GanShmuel2.0/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/ksalhab89/GanShmuel2.0?style=social)](https://github.com/ksalhab89/GanShmuel2.0/network/members)

</div>
