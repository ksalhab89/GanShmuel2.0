# Deployment Guide

Production deployment guide for the Provider Registration Service.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Database Setup](#database-setup)
- [Docker Deployment](#docker-deployment)
- [Health Check Verification](#health-check-verification)
- [Rollback Procedures](#rollback-procedures)
- [Common Deployment Issues](#common-deployment-issues)

## Prerequisites

- Docker 20.10+ or Docker Engine 24.0+
- PostgreSQL 14+ (or Docker container)
- Access to Billing Service (port 5002)
- Network connectivity between services

## Environment Setup

### 1. Create Environment File

Create a `.env` file in the service root directory:

```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://provider_user:provider_pass@provider-db:5432/provider_registration

# External Services
BILLING_SERVICE_URL=http://billing-service:5002

# Application Configuration
APP_HOST=0.0.0.0
APP_PORT=5004
LOG_LEVEL=INFO

# JWT Authentication (REQUIRED)
JWT_SECRET_KEY=your-secret-key-here
```

### 2. Generate Secure JWT Secret

```bash
# Generate a secure random secret key
openssl rand -hex 32

# Example output: 8f42a73054b1749f8f9c8c5d5d5b2e5f7c9a8d6e4f3a2b1c0d9e8f7a6b5c4d3e2f1
```

Set this value in your `.env` file:
```bash
JWT_SECRET_KEY=8f42a73054b1749f8f9c8c5d5d5b2e5f7c9a8d6e4f3a2b1c0d9e8f7a6b5c4d3e2f1
```

### 3. Environment Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | None | PostgreSQL connection string with asyncpg driver |
| `BILLING_SERVICE_URL` | Yes | `http://localhost:5002` | URL of billing service |
| `JWT_SECRET_KEY` | Yes | None | Secret key for JWT token signing (use openssl) |
| `APP_HOST` | No | `0.0.0.0` | Application bind address |
| `APP_PORT` | No | `5004` | Application port |
| `LOG_LEVEL` | No | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |

## Database Setup

### Step 1: Create Database

```bash
# Connect to PostgreSQL as admin
psql -U postgres

# Create database and user
CREATE DATABASE provider_registration;
CREATE USER provider_user WITH PASSWORD 'provider_pass';
GRANT ALL PRIVILEGES ON DATABASE provider_registration TO provider_user;
\q
```

### Step 2: Run Schema Migration

```bash
# Apply database schema
psql -U provider_user -d provider_registration -f schema.sql
```

Expected output:
```
CREATE TABLE
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE INDEX
CREATE FUNCTION
CREATE TRIGGER
```

### Step 3: Verify Schema

```bash
# Verify table exists
psql -U provider_user -d provider_registration -c "\dt"

# Verify indexes
psql -U provider_user -d provider_registration -c "\di"
```

Expected output:
```
List of relations
Schema | Name       | Type  | Owner
-------|------------|-------|-------------
public | candidates | table | provider_user

List of relations
Schema | Name                      | Type  | Owner
-------|---------------------------|-------|-------------
public | idx_candidates_created_at | index | provider_user
public | idx_candidates_products   | index | provider_user
public | idx_candidates_status     | index | provider_user
public | idx_candidates_version    | index | provider_user
```

## Docker Deployment

### Step 1: Build Docker Image

```bash
# Build the image
docker build -t provider-registration-service:latest .

# Verify image was created
docker images | grep provider-registration-service
```

Expected output:
```
provider-registration-service  latest  abc123def456  1 minute ago  150MB
```

### Step 2: Run Container

```bash
# Run with environment file
docker run -d \
  --name provider-registration-service \
  --env-file .env \
  -p 5004:5004 \
  --network gan-shmuel-network \
  provider-registration-service:latest

# Verify container is running
docker ps | grep provider-registration-service
```

Expected output:
```
CONTAINER ID   IMAGE                                  STATUS         PORTS
abc123def456   provider-registration-service:latest   Up 10 seconds  0.0.0.0:5004->5004/tcp
```

### Step 3: View Logs

```bash
# View real-time logs
docker logs -f provider-registration-service

# View last 100 lines
docker logs --tail 100 provider-registration-service
```

Expected startup logs:
```json
{"event": "Starting Provider Registration Service...", "level": "info", "timestamp": "2025-10-27T10:00:00.000Z"}
{"event": "Database connection established", "level": "info", "timestamp": "2025-10-27T10:00:01.000Z"}
{"event": "Application startup complete", "level": "info", "timestamp": "2025-10-27T10:00:01.500Z"}
```

## Health Check Verification

### 1. Basic Health Check

```bash
# Check service health
curl http://localhost:5004/health

# Expected response
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2025-10-27T10:00:00.000Z"
}
```

### 2. Verify API Documentation

```bash
# Access OpenAPI documentation
curl http://localhost:5004/docs

# Should return HTML page (status 200)
```

Visit in browser: http://localhost:5004/docs

### 3. Check Metrics Endpoint

```bash
# Verify Prometheus metrics
curl http://localhost:5004/metrics | head -20

# Expected output (partial)
# HELP provider_service_up Service uptime status
# TYPE provider_service_up gauge
provider_service_up 1.0
```

### 4. Test Database Connectivity

```bash
# Test candidate creation endpoint
curl -X POST http://localhost:5004/candidates \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Company",
    "contact_email": "test@example.com",
    "products": ["apples"],
    "truck_count": 5,
    "capacity_tons_per_day": 100
  }'

# Expected response (status 201)
{
  "candidate_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "company_name": "Test Company",
  ...
}
```

## Rollback Procedures

### Scenario 1: Service Fails to Start

```bash
# Stop failed container
docker stop provider-registration-service
docker rm provider-registration-service

# Rollback to previous image
docker run -d \
  --name provider-registration-service \
  --env-file .env \
  -p 5004:5004 \
  --network gan-shmuel-network \
  provider-registration-service:previous-version

# Verify service is healthy
curl http://localhost:5004/health
```

### Scenario 2: Database Migration Failure

```bash
# Connect to database
psql -U provider_user -d provider_registration

# Drop and recreate table (DANGER: destroys data)
DROP TABLE IF EXISTS candidates CASCADE;

# Re-run schema from backup or previous version
\i schema_backup.sql

# Verify schema
\dt
\di
```

### Scenario 3: Configuration Error

```bash
# Stop service
docker stop provider-registration-service

# Fix .env file
vim .env

# Restart service
docker start provider-registration-service

# Verify logs
docker logs -f provider-registration-service
```

## Common Deployment Issues

### Issue 1: Database Connection Refused

**Symptoms:**
```
ERROR: Connection refused (postgresql://...)
```

**Solutions:**
```bash
# 1. Verify database is running
docker ps | grep postgres
# OR
pg_isready -h localhost -p 5432

# 2. Check DATABASE_URL format
# Must use asyncpg driver:
# postgresql+asyncpg://user:pass@host:port/database

# 3. Verify network connectivity
docker network inspect gan-shmuel-network
```

### Issue 2: Service Not Responding

**Symptoms:**
```
curl: (7) Failed to connect to localhost port 5004
```

**Solutions:**
```bash
# 1. Check container is running
docker ps | grep provider-registration-service

# 2. Check container logs
docker logs provider-registration-service

# 3. Verify port mapping
docker port provider-registration-service
# Expected: 5004/tcp -> 0.0.0.0:5004

# 4. Check if port is in use
netstat -tulpn | grep 5004
# OR
lsof -i :5004
```

### Issue 3: JWT Authentication Failures

**Symptoms:**
```
401 Unauthorized: Could not validate credentials
```

**Solutions:**
```bash
# 1. Verify JWT_SECRET_KEY is set
docker exec provider-registration-service env | grep JWT_SECRET_KEY

# 2. Regenerate JWT secret if needed
openssl rand -hex 32

# 3. Update .env file and restart
docker restart provider-registration-service

# 4. Test login endpoint
curl -X POST http://localhost:5004/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=admin123"
```

### Issue 4: Billing Service Integration Failure

**Symptoms:**
```
502 Bad Gateway: Failed to create provider
```

**Solutions:**
```bash
# 1. Verify billing service is running
curl http://localhost:5002/health

# 2. Check BILLING_SERVICE_URL in .env
echo $BILLING_SERVICE_URL

# 3. Verify network connectivity
docker network inspect gan-shmuel-network

# 4. Check retry logs
docker logs provider-registration-service | grep billing_service_retry
```

### Issue 5: Database Schema Mismatch

**Symptoms:**
```
ERROR: column "version" does not exist
```

**Solutions:**
```bash
# 1. Verify schema version
psql -U provider_user -d provider_registration -c "\d candidates"

# 2. Check for missing columns
psql -U provider_user -d provider_registration -c "SELECT column_name FROM information_schema.columns WHERE table_name='candidates';"

# 3. Re-run schema migration
psql -U provider_user -d provider_registration -f schema.sql

# 4. Restart service
docker restart provider-registration-service
```

## Post-Deployment Checklist

- [ ] Service container is running
- [ ] Health check returns "healthy"
- [ ] Database connection is established
- [ ] Metrics endpoint is accessible
- [ ] API documentation is available at /docs
- [ ] Test candidate creation succeeds
- [ ] JWT authentication works
- [ ] Billing service integration succeeds
- [ ] Logs show no errors
- [ ] Prometheus is scraping metrics

## Monitoring Integration

See [OPERATIONS.md](./OPERATIONS.md) for:
- Prometheus configuration
- Grafana dashboard setup
- Log aggregation
- Alert configuration

## Security Considerations

See [SECURITY.md](./SECURITY.md) for:
- JWT secret management
- Database credential rotation
- Network security policies
- TLS/SSL configuration
