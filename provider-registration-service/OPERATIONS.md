# Operations Runbook

Operations guide for the Provider Registration Service.

## Table of Contents

- [Monitoring Setup](#monitoring-setup)
- [Log Management](#log-management)
- [Common Operational Tasks](#common-operational-tasks)
- [Troubleshooting Guide](#troubleshooting-guide)
- [Performance Tuning](#performance-tuning)
- [Backup and Restore](#backup-and-restore)

## Monitoring Setup

### Prometheus Configuration

Add this job to your Prometheus configuration (`prometheus.yml`):

```yaml
scrape_configs:
  - job_name: 'provider-registration-service'
    static_configs:
      - targets: ['provider-registration-service:5004']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Key Metrics to Monitor

#### Service Health

```promql
# Service uptime (1=up, 0=down)
provider_service_up

# Alert if service is down
provider_service_up == 0
```

#### Request Metrics

```promql
# Total requests per second
rate(provider_service_requests_total[5m])

# Error rate (4xx and 5xx responses)
rate(provider_service_requests_total{status_code=~"4..|5.."}[5m])

# Request rate by endpoint
rate(provider_service_requests_total[5m]) by (endpoint)
```

#### Database Health

```promql
# Database connection status (check via health endpoint)
up{job="provider-registration-service"}
```

### Grafana Dashboard

Create a dashboard with these panels:

#### Panel 1: Service Status
```promql
provider_service_up
```
Visualization: Stat panel (green=1, red=0)

#### Panel 2: Request Rate
```promql
sum(rate(provider_service_requests_total[5m])) by (endpoint)
```
Visualization: Graph

#### Panel 3: Error Rate
```promql
sum(rate(provider_service_requests_total{status_code=~"5.."}[5m]))
```
Visualization: Graph (with alert threshold)

#### Panel 4: Response Status Distribution
```promql
sum(rate(provider_service_requests_total[5m])) by (status_code)
```
Visualization: Pie chart

### Alert Rules

Create these Prometheus alert rules (`alerts.yml`):

```yaml
groups:
  - name: provider_registration_service
    interval: 30s
    rules:
      # Service down alert
      - alert: ProviderServiceDown
        expr: provider_service_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Provider Registration Service is down"
          description: "Service has been down for more than 1 minute"

      # High error rate alert
      - alert: ProviderServiceHighErrorRate
        expr: |
          rate(provider_service_requests_total{status_code=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate in Provider Registration Service"
          description: "Error rate is {{ $value }} errors/sec"

      # Database connectivity alert
      - alert: ProviderServiceDatabaseDown
        expr: |
          up{job="provider-registration-service"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Provider Service cannot reach database"
          description: "Database connectivity lost for 2 minutes"
```

---

## Log Management

### Log Locations

**Docker container logs:**
```bash
# View logs
docker logs provider-registration-service

# Follow logs in real-time
docker logs -f provider-registration-service

# View last 100 lines
docker logs --tail 100 provider-registration-service

# View logs since timestamp
docker logs --since 2025-10-27T10:00:00 provider-registration-service
```

**Persistent logs (if volume mounted):**
```bash
/var/log/provider-registration-service/app.log
```

### Log Format

The service uses structured JSON logging:

```json
{
  "event": "billing_service_request",
  "action": "create_provider",
  "company": "Fresh Fruit Ltd",
  "level": "info",
  "timestamp": "2025-10-27T10:00:00.000Z"
}
```

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages (non-critical issues)
- **ERROR**: Error messages (failures)

Set log level via environment variable:
```bash
LOG_LEVEL=DEBUG
```

### Useful Log Queries

#### Find all errors
```bash
docker logs provider-registration-service 2>&1 | grep -i error
```

#### Find billing service failures
```bash
docker logs provider-registration-service 2>&1 | grep billing_service_error
```

#### Find authentication failures
```bash
docker logs provider-registration-service 2>&1 | grep -i "unauthorized\|forbidden"
```

#### Find retry attempts
```bash
docker logs provider-registration-service 2>&1 | grep billing_service_retry
```

#### Count errors by type
```bash
docker logs provider-registration-service 2>&1 | grep -i error | sort | uniq -c | sort -rn
```

### Log Rotation

Configure log rotation with Docker logging driver:

```yaml
# docker-compose.yml
services:
  provider-registration-service:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
```

---

## Common Operational Tasks

### 1. Service Restart

```bash
# Graceful restart
docker restart provider-registration-service

# Force restart (if hung)
docker stop provider-registration-service
docker start provider-registration-service

# Verify service is healthy
curl http://localhost:5004/health
```

### 2. Check Service Status

```bash
# Check if container is running
docker ps | grep provider-registration-service

# Check service health
curl http://localhost:5004/health

# Expected output:
# {"status":"healthy","database":"connected","timestamp":"..."}
```

### 3. View Active Connections

```bash
# Check database connections
docker exec provider-registration-service \
  psql postgresql://provider_user:provider_pass@provider-db:5432/provider_registration \
  -c "SELECT count(*) FROM pg_stat_activity WHERE datname='provider_registration';"
```

### 4. Clear Database (Development Only)

```bash
# WARNING: This deletes all data!
docker exec -it provider-db psql -U provider_user -d provider_registration -c "TRUNCATE candidates CASCADE;"
```

### 5. Update Configuration

```bash
# Edit environment file
vim .env

# Restart service to apply changes
docker restart provider-registration-service

# Verify new configuration
docker exec provider-registration-service env | grep -E "DATABASE_URL|BILLING_SERVICE_URL|LOG_LEVEL"
```

### 6. Scale Service (Docker Swarm/Kubernetes)

```bash
# Docker Swarm
docker service scale provider-registration-service=3

# Kubernetes
kubectl scale deployment provider-registration-service --replicas=3
```

### 7. Export Metrics

```bash
# Export current metrics
curl http://localhost:5004/metrics > metrics_$(date +%Y%m%d_%H%M%S).txt

# Query specific metric
curl -s http://localhost:5004/metrics | grep provider_service_requests_total
```

### 8. Test Billing Integration

```bash
# Check billing service connectivity
docker exec provider-registration-service curl http://billing-service:5002/health

# Test provider creation (requires running billing service)
curl -X POST http://localhost:5004/candidates/test-id/approve \
  -H "Authorization: Bearer $TOKEN"
```

---

## Troubleshooting Guide

### Issue 1: Service Won't Start

**Check container status:**
```bash
docker ps -a | grep provider-registration-service
```

**View startup logs:**
```bash
docker logs provider-registration-service
```

**Common causes:**
- Database connection failure (check DATABASE_URL)
- Port already in use (check with `netstat -tulpn | grep 5004`)
- Missing JWT_SECRET_KEY environment variable
- Invalid configuration in .env file

**Solution:**
```bash
# Fix .env file
vim .env

# Remove and recreate container
docker rm provider-registration-service
docker run -d --name provider-registration-service --env-file .env -p 5004:5004 provider-registration-service:latest

# Verify health
curl http://localhost:5004/health
```

### Issue 2: Database Connection Errors

**Symptoms:**
```json
{"event": "database_error", "error": "connection refused", "level": "error"}
```

**Diagnosis:**
```bash
# Check if database container is running
docker ps | grep provider-db

# Test database connection
docker exec provider-db pg_isready -U provider_user

# Check connection from service container
docker exec provider-registration-service ping provider-db
```

**Solution:**
```bash
# Start database if not running
docker start provider-db

# Verify DATABASE_URL format
# Must be: postgresql+asyncpg://user:pass@host:port/database
docker exec provider-registration-service env | grep DATABASE_URL

# Restart service
docker restart provider-registration-service
```

### Issue 3: High Memory Usage

**Check memory usage:**
```bash
# Container memory stats
docker stats provider-registration-service --no-stream

# Detailed stats
docker exec provider-registration-service ps aux
```

**Solution:**
```bash
# Set memory limits in docker-compose.yml
services:
  provider-registration-service:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

# Restart with new limits
docker-compose up -d
```

### Issue 4: Slow Response Times

**Check response times:**
```bash
# Test API response time
time curl http://localhost:5004/candidates

# Check database query performance
docker exec provider-db psql -U provider_user -d provider_registration \
  -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

**Common causes:**
- Missing database indexes
- Large result sets without pagination
- Database connection pool exhaustion
- Network latency to billing service

**Solution:**
```bash
# Verify indexes exist
docker exec provider-db psql -U provider_user -d provider_registration -c "\di"

# Add pagination to queries
curl "http://localhost:5004/candidates?limit=20&offset=0"

# Check billing service latency
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:5002/health
```

### Issue 5: JWT Token Validation Failures

**Symptoms:**
```json
{"detail": "Could not validate credentials"}
```

**Diagnosis:**
```bash
# Verify JWT_SECRET_KEY is set
docker exec provider-registration-service env | grep JWT_SECRET_KEY

# Test token generation
curl -X POST http://localhost:5004/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=admin123"
```

**Solution:**
```bash
# Regenerate JWT secret
openssl rand -hex 32

# Update .env file
echo "JWT_SECRET_KEY=<new-secret>" >> .env

# Restart service
docker restart provider-registration-service

# Get new token
TOKEN=$(curl -X POST http://localhost:5004/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=admin123" \
  | jq -r '.access_token')
```

### Issue 6: Billing Service Integration Failures

**Symptoms:**
```json
{"detail": "Failed to create provider: Connection refused"}
```

**Diagnosis:**
```bash
# Check billing service health
curl http://localhost:5002/health

# Check network connectivity
docker exec provider-registration-service curl -v http://billing-service:5002/health

# View retry logs
docker logs provider-registration-service | grep billing_service_retry
```

**Solution:**
```bash
# Verify billing service is running
docker ps | grep billing-service

# Check BILLING_SERVICE_URL
docker exec provider-registration-service env | grep BILLING_SERVICE_URL

# Verify network
docker network inspect gan-shmuel-network

# Restart both services
docker restart billing-service provider-registration-service
```

### Issue 7: Optimistic Locking Conflicts

**Symptoms:**
```json
{"detail": "Candidate was modified by another process. Please retry."}
```

**Diagnosis:**
```bash
# Check candidate version
docker exec provider-db psql -U provider_user -d provider_registration \
  -c "SELECT id, company_name, status, version FROM candidates WHERE id='<uuid>';"

# Check for concurrent operations
docker logs provider-registration-service | grep -i "concurrent\|version"
```

**Solution:**
```bash
# This is expected behavior for concurrent approvals
# Client should retry the operation
# No action needed on server side

# If repeated failures occur, check for deadlocks:
docker exec provider-db psql -U provider_user -d provider_registration \
  -c "SELECT * FROM pg_stat_activity WHERE wait_event_type = 'Lock';"
```

---

## Performance Tuning

### Database Optimization

#### 1. Verify Indexes

```sql
-- Check existing indexes
SELECT indexname, tablename FROM pg_indexes WHERE tablename = 'candidates';

-- Expected indexes:
-- idx_candidates_status (for status filtering)
-- idx_candidates_created_at (for ordering)
-- idx_candidates_products (GIN index for JSONB queries)
-- idx_candidates_version (for optimistic locking)
```

#### 2. Analyze Query Performance

```sql
-- Enable query timing
\timing on

-- Explain query plan
EXPLAIN ANALYZE
SELECT * FROM candidates
WHERE status = 'pending'
ORDER BY created_at DESC
LIMIT 20;

-- Should use idx_candidates_status and idx_candidates_created_at
```

#### 3. Connection Pool Tuning

Update database.py configuration:

```python
# Increase pool size for high load
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=20,      # Default: 5
    max_overflow=10,   # Default: 10
    pool_pre_ping=True
)
```

### Application Performance

#### 1. Enable Response Compression

Add middleware in main.py:

```python
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

#### 2. Cache Frequently Accessed Data

Consider adding Redis caching for:
- Candidate listings (with TTL)
- Status counts
- Product statistics

#### 3. Optimize JSON Serialization

For large result sets, use streaming responses:

```python
from fastapi.responses import StreamingResponse
```

### Monitoring Performance

```bash
# Request rate
curl -s http://localhost:5004/metrics | grep provider_service_requests_total

# Response times (add custom metrics)
# P50, P95, P99 latencies

# Database query times
docker exec provider-db psql -U provider_user -d provider_registration \
  -c "SELECT query, calls, mean_time, max_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

---

## Backup and Restore

### Database Backup

#### 1. Manual Backup

```bash
# Full database backup
docker exec provider-db pg_dump -U provider_user provider_registration > backup_$(date +%Y%m%d).sql

# Compressed backup
docker exec provider-db pg_dump -U provider_user provider_registration | gzip > backup_$(date +%Y%m%d).sql.gz

# Backup specific table only
docker exec provider-db pg_dump -U provider_user -t candidates provider_registration > candidates_backup_$(date +%Y%m%d).sql
```

#### 2. Automated Backup Script

```bash
#!/bin/bash
# backup.sh - Run daily via cron

BACKUP_DIR="/backups/provider-registration"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/provider_registration_$DATE.sql.gz"

# Create backup
docker exec provider-db pg_dump -U provider_user provider_registration | gzip > "$BACKUP_FILE"

# Keep only last 7 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

# Verify backup integrity
gunzip -t "$BACKUP_FILE"

echo "Backup completed: $BACKUP_FILE"
```

Add to crontab:
```bash
# Run backup daily at 2 AM
0 2 * * * /opt/scripts/backup.sh >> /var/log/backup.log 2>&1
```

### Database Restore

#### 1. Restore from Backup

```bash
# Stop service first
docker stop provider-registration-service

# Restore from uncompressed backup
docker exec -i provider-db psql -U provider_user -d provider_registration < backup_20251027.sql

# Restore from compressed backup
gunzip -c backup_20251027.sql.gz | docker exec -i provider-db psql -U provider_user -d provider_registration

# Restart service
docker start provider-registration-service

# Verify data
curl http://localhost:5004/candidates
```

#### 2. Point-in-Time Recovery

Enable WAL archiving in PostgreSQL:

```bash
# In postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'cp %p /archive/%f'
```

Then use pg_basebackup and WAL replay for PITR.

### Disaster Recovery

#### Recovery Time Objective (RTO)

Target: 15 minutes

#### Recovery Point Objective (RPO)

Target: 24 hours (daily backups)

#### Recovery Steps

1. **Identify failure point**
   - Check service logs
   - Check database logs
   - Check system resources

2. **Restore database**
   ```bash
   # Latest backup
   gunzip -c latest_backup.sql.gz | docker exec -i provider-db psql -U provider_user -d provider_registration
   ```

3. **Verify data integrity**
   ```bash
   # Check record counts
   docker exec provider-db psql -U provider_user -d provider_registration \
     -c "SELECT status, COUNT(*) FROM candidates GROUP BY status;"
   ```

4. **Restart services**
   ```bash
   docker restart provider-registration-service
   ```

5. **Verify operation**
   ```bash
   curl http://localhost:5004/health
   curl http://localhost:5004/candidates?limit=5
   ```

---

## Contact and Escalation

For operational issues:
1. Check this runbook first
2. Review [TROUBLESHOOTING.md](./DEPLOYMENT.md#common-deployment-issues)
3. Check service logs
4. Escalate to platform team if unresolved

For security incidents:
- See [SECURITY.md](./SECURITY.md)
- Contact security team immediately
