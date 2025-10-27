# Rate Limiting Implementation

## Status
✅ **Implemented** in Provider Registration Service | 📋 **Template** for other services

## Overview

Rate limiting protects the API from abuse by limiting the number of requests a client can make within a time window. This prevents:
- **DDoS attacks**: Overwhelming the server with requests
- **Brute force attacks**: Repeated login/password attempts
- **Resource exhaustion**: Excessive API calls consuming server resources
- **Cost overruns**: Preventing unexpected cloud costs from API abuse

## Implementation Details

### Technology Stack
- **Library**: SlowAPI (FastAPI rate limiting)
- **Backend**: Redis (distributed rate limiting)
- **Strategy**: Fixed-window rate limiting
- **Fallback**: In-memory limiter if Redis unavailable

### Rate Limit Tiers

Different endpoint types have different rate limits based on their resource intensity and security requirements:

| Tier | Limit | Use Case | Example Endpoints |
|------|-------|----------|-------------------|
| **PUBLIC** | 10/minute | Unauthenticated endpoints | Public APIs |
| **AUTH_LOGIN** | 5/minute | Login attempts | `/auth/login` |
| **AUTH_REGISTER** | 3/minute | Registration | `/auth/register` |
| **READ_LIGHT** | 100/minute | Fast read operations | `/health`, `/metrics` |
| **READ_HEAVY** | 30/minute | Database-intensive reads | `/candidates`, `/search` |
| **WRITE_LIGHT** | 50/minute | Single record writes | `/candidates` (POST) |
| **WRITE_HEAVY** | 10/minute | Batch operations | `/candidates/bulk` |
| **ADMIN** | 20/minute | Administrative ops | `/candidates/{id}/approve` |

### Global Defaults

All endpoints without specific limits get:
- **200 requests per hour**
- **50 requests per minute**

### Response Headers

When rate limit is hit, clients receive:
- **Status Code**: `429 Too Many Requests`
- **Headers**:
  - `Retry-After`: Seconds until retry allowed
  - `X-RateLimit-Limit`: Total allowed requests
  - `X-RateLimit-Remaining`: Requests remaining

### Response Body
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded: 5 per 1 minute",
  "retry_after": "42 seconds"
}
```

## Usage in Code

### Adding Rate Limits to Endpoints

```python
from fastapi import APIRouter, Depends
from slowapi import Limiter
from src.rate_limiting import RateLimits, limiter

router = APIRouter()

# Example 1: Using predefined tier
@router.post("/login")
@limiter.limit(RateLimits.AUTH_LOGIN)
async def login(credentials: LoginRequest):
    # Login logic
    pass

# Example 2: Custom rate limit
@router.get("/search")
@limiter.limit("10 per minute")
async def search(query: str):
    # Search logic
    pass

# Example 3: Multiple rate limits (most restrictive applies)
@router.post("/register")
@limiter.limit(RateLimits.AUTH_REGISTER)
@limiter.limit("10 per hour")  # Also apply hourly limit
async def register(user: UserCreate):
    # Registration logic
    pass
```

### User-Aware Rate Limiting

Rate limits can differentiate between authenticated users and anonymous IPs:

```python
from src.rate_limiting import user_aware_limiter

@router.get("/profile")
@limiter.limit("50 per minute", key_func=user_aware_limiter)
async def get_profile(request: Request):
    # Authenticated users get tracked by user ID
    # Anonymous users tracked by IP address
    pass
```

## Configuration

### Environment Variables

```bash
# Redis URL for distributed rate limiting
REDIS_URL=redis://shift-redis:6379/1
```

### Docker Compose

Provider service must have:
```yaml
environment:
  - REDIS_URL=redis://shift-redis:6379/1
depends_on:
  shift-redis:
    condition: service_healthy
```

## Testing Rate Limits

### Manual Testing

```bash
# Test login rate limit (5/minute)
for i in {1..6}; do
  curl -X POST http://localhost:5004/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"wrong"}'
  echo ""
done

# 6th request should return 429 Too Many Requests
```

### Automated Testing

```python
import pytest
from fastapi.testclient import TestClient

def test_rate_limit_exceeded(client: TestClient):
    """Test that rate limiting works"""

    # Make 6 requests (limit is 5/minute)
    responses = []
    for _ in range(6):
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "wrong"
        })
        responses.append(response)

    # First 5 should succeed (or return 401 for wrong password)
    assert all(r.status_code in [200, 401] for r in responses[:5])

    # 6th should be rate limited
    assert responses[5].status_code == 429
    assert "rate_limit_exceeded" in responses[5].json()["error"]
```

## Monitoring

### Prometheus Metrics

Rate limit metrics are automatically exported:

```prometheus
# Rate limit hits
rate_limit_exceeded_total{endpoint="/auth/login", method="POST"}

# Requests per endpoint
http_requests_total{endpoint="/auth/login", status="429"}
```

### Grafana Dashboards

Create alerts for:
- High rate limit violations (potential attack)
- Sustained 429 errors (legitimate users being blocked)

## Applying to Other Services

To add rate limiting to other services (weight, billing, shift):

### 1. Update `pyproject.toml`

```toml
dependencies = [
    # ... existing dependencies
    "slowapi>=0.1.9",
    "redis>=5.0.0",
]
```

### 2. Copy rate limiting module

```bash
cp provider-registration-service/src/rate_limiting.py \
   <service>/src/rate_limiting.py
```

### 3. Update config

Add Redis URL to service config:
```python
redis_url: str = Field(
    default="redis://localhost:6379/1",
    alias="REDIS_URL"
)
```

### 4. Integrate in main.py

```python
from .rate_limiting import limiter, rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
```

### 5. Add to endpoints

Add `@limiter.limit()` decorators to routes that need protection.

### 6. Update docker-compose.yml

```yaml
environment:
  - REDIS_URL=redis://shift-redis:6379/1
depends_on:
  shift-redis:
    condition: service_healthy
```

## Security Considerations

### IP Spoofing Prevention

The limiter uses `X-Forwarded-For` header when behind a proxy:
```python
forwarded_for = request.headers.get("X-Forwarded-For")
if forwarded_for:
    client_ip = forwarded_for.split(",")[0].strip()
```

**Important**: In production, ensure your reverse proxy (nginx, Traefik) strips client-provided `X-Forwarded-For` headers and sets trusted values.

### Distributed Systems

Redis-backed rate limiting ensures:
- **Consistency**: Same limits across multiple service instances
- **Persistence**: Limits survive service restarts
- **Performance**: Fast in-memory lookups

### Whitelisting

To bypass rate limits for trusted IPs/users, modify `rate_limiting.py`:

```python
WHITELIST_IPS = ["10.0.0.1", "192.168.1.100"]
WHITELIST_USERS = ["admin@example.com"]

def get_client_identifier(request: Request) -> str:
    client_ip = request.client.host if request.client else "unknown"

    # Skip rate limiting for whitelisted IPs
    if client_ip in WHITELIST_IPS:
        return None

    # ... rest of logic
```

## Benefits

✅ **DDoS Protection**: Prevents overwhelming the server
✅ **Brute Force Prevention**: Limits login attempts
✅ **Fair Usage**: Ensures resources shared fairly
✅ **Cost Control**: Prevents unexpected cloud bills
✅ **Monitoring**: Track API abuse patterns
✅ **User Experience**: Prevents slowdowns from abuse

## Next Steps

1. **Deploy to production** with Redis backend
2. **Monitor rate limit violations** via Prometheus
3. **Tune limits** based on actual usage patterns
4. **Add to other services** (weight, billing, shift)
5. **Implement whitelisting** for trusted clients
6. **Add user-specific tiers** (premium users get higher limits)
