# Security Documentation

Security features and best practices for the Provider Registration Service.

## Table of Contents

- [Security Overview](#security-overview)
- [JWT Authentication](#jwt-authentication)
- [Admin Role Management](#admin-role-management)
- [SQL Injection Prevention](#sql-injection-prevention)
- [Optimistic Locking](#optimistic-locking)
- [Secrets Management](#secrets-management)
- [Security Best Practices](#security-best-practices)
- [Security Audit](#security-audit)

## Security Overview

The Provider Registration Service implements multiple security layers:

1. **Authentication**: JWT-based token authentication
2. **Authorization**: Role-based access control (admin-only endpoints)
3. **SQL Injection Protection**: Parameterized queries with SQLAlchemy
4. **Optimistic Locking**: Prevents concurrent modification conflicts
5. **Password Hashing**: Bcrypt for secure password storage
6. **Secrets Management**: Environment-based configuration
7. **CORS**: Configurable cross-origin resource sharing

## JWT Authentication

### Overview

The service uses JSON Web Tokens (JWT) for stateless authentication with HS256 algorithm.

### Token Structure

```
Header:
{
  "alg": "HS256",
  "typ": "JWT"
}

Payload:
{
  "sub": "admin@example.com",  // Subject (username)
  "role": "admin",              // User role
  "exp": 1698765432             // Expiration timestamp
}

Signature:
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  secret_key
)
```

### Token Lifecycle

1. **Login**: User provides credentials
   ```bash
   POST /auth/login
   username=admin@example.com&password=admin123
   ```

2. **Token Generation**: Server creates JWT with 30-minute expiration
   ```json
   {
     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "token_type": "bearer"
   }
   ```

3. **Token Usage**: Client includes token in Authorization header
   ```
   Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

4. **Token Validation**: Server verifies signature and expiration
   - Checks signature using JWT_SECRET_KEY
   - Validates expiration timestamp
   - Extracts user role for authorization

5. **Token Expiration**: After 30 minutes, client must re-authenticate

### JWT Secret Key Configuration

**Generate secure secret:**
```bash
# Generate 32-byte (256-bit) random secret
openssl rand -hex 32
```

**Set in environment:**
```bash
# .env file
JWT_SECRET_KEY=8f42a73054b1749f8f9c8c5d5d5b2e5f7c9a8d6e4f3a2b1c0d9e8f7a6b5c4d3e2f1
```

**Security requirements:**
- Minimum 32 characters (256 bits)
- Cryptographically random
- Never commit to version control
- Rotate periodically (e.g., quarterly)
- Different secret per environment (dev/staging/prod)

### Token Validation

Implementation in `src/auth/jwt_handler.py`:

```python
async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Extract and validate current user from JWT token"""
    try:
        # Decode and verify token signature
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Extract claims
        username: str = payload.get("sub")
        role: str = payload.get("role")

        # Validate required claims
        if username is None:
            raise credentials_exception

        return {"username": username, "role": role}
    except JWTError:
        # Invalid token, expired, or wrong signature
        raise HTTPException(status_code=401, detail="Could not validate credentials")
```

### Security Considerations

**Do:**
- ✅ Use strong secret keys (256-bit minimum)
- ✅ Set reasonable expiration times (30 minutes)
- ✅ Validate token signature on every request
- ✅ Store secret in environment variables
- ✅ Use HTTPS in production
- ✅ Implement token refresh mechanism (future enhancement)

**Don't:**
- ❌ Hardcode secrets in source code
- ❌ Use weak or predictable secrets
- ❌ Store tokens in localStorage (use httpOnly cookies instead)
- ❌ Share secrets across environments
- ❌ Use tokens after expiration

---

## Admin Role Management

### Role-Based Access Control (RBAC)

The service implements simple RBAC with admin role:

```python
async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Require admin role for endpoint access"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
```

### Protected Endpoints

Only admin users can access:
- `POST /candidates/{id}/approve` - Approve candidate
- `POST /candidates/{id}/reject` - Reject candidate (Phase 3)

### Default Admin Account

**Development/Testing:**
```
Username: admin@example.com
Password: admin123
Password Hash: $2b$12$JTTl35DfwYumO8YwOpKuMum89zzbynJamgwg//U7jaFfEGZM9u1ly
```

**⚠️ WARNING**: This is a hardcoded account for development only. Replace with database-backed user management in production.

### Production Recommendations

1. **Database-backed user management**
   - Create users table with email, password_hash, role
   - Implement user registration endpoint (admin-only)
   - Store user credentials securely

2. **Enhanced roles**
   - `admin`: Full access (approve, reject, manage users)
   - `reviewer`: Read-only access to candidates
   - `auditor`: Read-only access with audit logs

3. **Password policy**
   - Minimum 12 characters
   - Require uppercase, lowercase, numbers, symbols
   - Password expiration (90 days)
   - Prevent password reuse

4. **Multi-factor authentication (MFA)**
   - TOTP-based (Google Authenticator)
   - SMS backup codes
   - Recovery codes

### Password Hashing

Uses bcrypt with automatic salt generation:

```python
def get_password_hash(password: str) -> str:
    """Hash password with bcrypt"""
    salt = bcrypt.gensalt()  # Generates random salt
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
```

**Security features:**
- Automatic salt generation (prevents rainbow table attacks)
- Configurable work factor (default: 12 rounds)
- Constant-time comparison (prevents timing attacks)

---

## SQL Injection Prevention

### Parameterized Queries

All database queries use SQLAlchemy's parameterized queries to prevent SQL injection:

**✅ SAFE - Parameterized:**
```python
query = text("""
    SELECT * FROM candidates
    WHERE status = :status
      AND products @> CAST(:product AS jsonb)
""").bindparams(
    bindparam("status", type_=String),
    bindparam("product", type_=String)
)

result = await db.execute(query, {
    "status": status,
    "product": json.dumps([product])
})
```

**❌ UNSAFE - String Interpolation (Never do this):**
```python
# This would be vulnerable to SQL injection!
query = f"SELECT * FROM candidates WHERE status = '{status}'"
```

### NULL-Safe Filtering

Uses PostgreSQL NULL-safe conditions for optional filters:

```sql
WHERE (:status IS NULL OR status = :status)
  AND (:product IS NULL OR products @> CAST(:product AS jsonb))
```

This pattern:
- Prevents SQL injection through parameterization
- Handles optional filters without dynamic SQL
- Maintains performance with proper indexes

### Testing SQL Injection Protection

See `tests/test_sql_injection.py` for comprehensive tests:

```python
@pytest.mark.asyncio
async def test_sql_injection_attempt_in_filters(client: AsyncClient):
    """Test that SQL injection attempts are safely handled"""

    # Attempt SQL injection in status filter
    malicious_status = "pending' OR '1'='1"
    response = await client.get(f"/candidates?status={malicious_status}")

    # Should return empty results (no match for malicious string)
    # NOT execute injected SQL
    assert response.status_code == 200
    data = response.json()
    assert len(data["candidates"]) == 0
```

### Security Audit Results

All SQL injection tests passing:
- ✅ String interpolation in filters
- ✅ UNION-based injection
- ✅ Boolean-based blind injection
- ✅ Time-based blind injection
- ✅ Stacked queries
- ✅ NULL byte injection
- ✅ Special characters

See: `SECURITY_AUDIT_SQL_INJECTION.md` for detailed audit report.

---

## Optimistic Locking

### Purpose

Prevents lost updates when multiple users/processes modify the same candidate concurrently.

### How It Works

1. **Version column**: Each candidate has a `version` field (default: 1)
2. **Read version**: When reading candidate, include current version
3. **Update with version check**: Only update if version matches expected value
4. **Automatic increment**: Database trigger increments version on update

### Database Schema

```sql
CREATE TABLE candidates (
    id UUID PRIMARY KEY,
    ...
    version INTEGER DEFAULT 1 NOT NULL
);

-- Trigger to auto-increment version
CREATE OR REPLACE FUNCTION update_candidates_metadata()
RETURNS TRIGGER AS $$
BEGIN
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_candidates_metadata
BEFORE UPDATE ON candidates
FOR EACH ROW EXECUTE FUNCTION update_candidates_metadata();
```

### Implementation

```python
async def approve_candidate(
    candidate_id: UUID,
    provider_id: int,
    expected_version: int
) -> CandidateResponse:
    """Approve candidate with optimistic locking"""

    query = text("""
        UPDATE candidates
        SET status = 'approved',
            provider_id = :provider_id,
            version = version + 1
        WHERE id = :id
          AND status = 'pending'
          AND version = :expected_version  -- Version check
        RETURNING *
    """)

    result = await db.execute(query, {
        "id": candidate_id,
        "provider_id": provider_id,
        "expected_version": expected_version
    })

    row = result.fetchone()
    if not row:
        # Version mismatch or status changed
        raise ConcurrentModificationError(
            "Candidate was modified by another process"
        )

    return build_response(row)
```

### Workflow Example

**Scenario: Two admins approve same candidate simultaneously**

```
Time  Admin A                           Admin B
----  ---------------------------------  ---------------------------------
T1    GET /candidates/123                GET /candidates/123
      (version: 1)                       (version: 1)

T2    POST /approve                      (thinking...)
      WHERE version = 1
      ✅ Success (version → 2)

T3    (done)                             POST /approve
                                         WHERE version = 1
                                         ❌ Fails (version is now 2)
                                         409 Conflict returned
```

**Result**: Admin B receives error and must retry (will see candidate is already approved).

### Error Handling

Client receives 409 Conflict:
```json
{
  "detail": "Candidate was modified by another process. Please retry."
}
```

Client should:
1. Refresh candidate data
2. Check current status
3. Decide whether to retry or abort

### Benefits

- ✅ Prevents lost updates
- ✅ No database locks needed (better performance)
- ✅ Works across multiple service instances
- ✅ Simple to understand and implement
- ✅ Automatic version management via trigger

### Testing

See `tests/test_concurrency.py` for concurrent modification tests:

```python
async def test_concurrent_approval_conflict():
    """Test that concurrent approvals are detected"""

    # Both processes read candidate (version 1)
    candidate1 = await service1.get_candidate(candidate_id)
    candidate2 = await service2.get_candidate(candidate_id)

    # Process 1 approves successfully
    await service1.approve_candidate(candidate_id, 101, candidate1.version)

    # Process 2 approval fails (version mismatch)
    with pytest.raises(ConcurrentModificationError):
        await service2.approve_candidate(candidate_id, 102, candidate2.version)
```

---

## Secrets Management

### Environment Variables

All secrets managed via environment variables:

```bash
# .env file (NEVER commit to git)
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
BILLING_SERVICE_URL=http://billing-service:5002
JWT_SECRET_KEY=8f42a73054b1749f8f9c8c5d5d5b2e5f7c9a8d6e4f3a2b1c0d9e8f7a6b5c4d3e2f1
```

### .gitignore Configuration

```
# Exclude secrets
.env
.env.*
!.env.example

# Exclude sensitive data
*.pem
*.key
secrets/
```

### Secret Rotation

**JWT Secret Rotation:**

```bash
# 1. Generate new secret
NEW_SECRET=$(openssl rand -hex 32)

# 2. Update .env file
sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$NEW_SECRET/" .env

# 3. Restart service
docker restart provider-registration-service

# 4. All existing tokens are now invalid
# Users must re-authenticate
```

**Database Password Rotation:**

```bash
# 1. Create new password
NEW_PASS=$(openssl rand -base64 32)

# 2. Update database user
psql -U postgres -c "ALTER USER provider_user WITH PASSWORD '$NEW_PASS';"

# 3. Update DATABASE_URL in .env
# 4. Restart service
docker restart provider-registration-service
```

### Production Secret Management

**Recommended tools:**

1. **HashiCorp Vault**
   - Dynamic secrets
   - Automatic rotation
   - Audit logs

2. **AWS Secrets Manager**
   - KMS encryption
   - Automatic rotation
   - IAM integration

3. **Kubernetes Secrets**
   - Base64 encoded
   - RBAC access control
   - Volume mounts

**Example with AWS Secrets Manager:**

```python
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Load secrets at startup
secrets = get_secret('provider-registration-service/prod')
settings.jwt_secret_key = secrets['jwt_secret_key']
settings.database_url = secrets['database_url']
```

---

## Security Best Practices

### 1. HTTPS/TLS in Production

**Never run in production without HTTPS:**

```nginx
# Nginx reverse proxy configuration
server {
    listen 443 ssl http2;
    server_name provider-registration.gan-shmuel.com;

    ssl_certificate /etc/ssl/certs/provider-service.crt;
    ssl_certificate_key /etc/ssl/private/provider-service.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://provider-registration-service:5004;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. Rate Limiting

Protect against brute force and DoS attacks:

```python
# Future enhancement - add rate limiting middleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/auth/login")
@limiter.limit("5/minute")  # Max 5 login attempts per minute
async def login(...):
    ...
```

### 3. Input Validation

**Always validate input:**
- Pydantic models enforce type checking
- Field validators check business rules
- Database constraints provide last line of defense

```python
class CandidateCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    contact_email: EmailStr  # Validates email format
    truck_count: int = Field(..., gt=0)  # Must be positive

    @field_validator('products')
    @classmethod
    def validate_products(cls, v):
        allowed = ['apples', 'oranges', 'grapes', 'bananas', 'mangoes']
        for product in v:
            if product not in allowed:
                raise ValueError(f"Invalid product: {product}")
        return v
```

### 4. CORS Configuration

**Development (permissive):**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production (restrictive):**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://gan-shmuel.com",
        "https://admin.gan-shmuel.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### 5. Security Headers

Add security headers middleware:

```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Restrict allowed hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["provider-registration.gan-shmuel.com"]
)

# Add security headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

### 6. Logging and Audit

**Log security events:**
- Authentication attempts (success and failure)
- Authorization failures
- Candidate approvals/rejections
- Configuration changes

**Do NOT log:**
- Passwords or password hashes
- JWT tokens
- Database credentials
- PII without anonymization

### 7. Dependency Security

**Scan for vulnerabilities:**

```bash
# Check for known vulnerabilities
pip-audit

# Update dependencies
uv sync --upgrade

# Review security advisories
https://github.com/advisories
```

---

## Security Audit

### Audit Checklist

- [x] JWT authentication implemented
- [x] Admin role-based access control
- [x] SQL injection protection (parameterized queries)
- [x] Optimistic locking for concurrency
- [x] Password hashing with bcrypt
- [x] Secrets in environment variables
- [x] Input validation with Pydantic
- [x] CORS configured
- [x] Structured logging
- [ ] HTTPS/TLS (production)
- [ ] Rate limiting (future)
- [ ] Security headers (future)
- [ ] Database user management (future)
- [ ] MFA support (future)

### Known Security Limitations

1. **Hardcoded admin account** - Replace with database-backed users in production
2. **No rate limiting** - Add slowapi or similar middleware
3. **No MFA** - Implement TOTP-based 2FA
4. **No audit logs** - Add dedicated audit trail table
5. **No IP whitelisting** - Add firewall rules for admin endpoints

### Security Incident Response

**If security breach detected:**

1. **Immediate actions:**
   - Rotate all secrets (JWT, database passwords)
   - Revoke all active tokens
   - Enable debug logging
   - Notify security team

2. **Investigation:**
   - Review logs for suspicious activity
   - Check database for unauthorized changes
   - Identify attack vector

3. **Remediation:**
   - Patch vulnerabilities
   - Update dependencies
   - Deploy security fixes
   - Restore from backup if needed

4. **Post-incident:**
   - Document incident
   - Update security procedures
   - Conduct security training
   - Schedule security audit

### Security Contact

For security issues:
- Email: security@gan-shmuel.com
- Do NOT create public GitHub issues for security vulnerabilities
- Use responsible disclosure process
