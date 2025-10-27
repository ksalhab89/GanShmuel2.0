# API Documentation

Complete API reference for the Provider Registration Service.

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Error Responses](#error-responses)
- [Pagination](#pagination)
- [Endpoints](#endpoints)
  - [Health Check](#health-check)
  - [Authentication](#authentication-endpoints)
  - [Candidate Management](#candidate-management)
  - [Metrics](#metrics)

## Base URL

```
http://localhost:5004
```

Production:
```
https://provider-registration.gan-shmuel.com
```

## Authentication

The service uses JWT (JSON Web Tokens) for authentication.

### Authentication Flow

1. **Login** to receive JWT token
2. **Include token** in Authorization header for protected endpoints
3. **Token expires** after 30 minutes

### Authorization Header Format

```
Authorization: Bearer <jwt-token>
```

### Protected Endpoints

- `POST /candidates/{id}/approve` - Requires admin role
- `POST /candidates/{id}/reject` - Requires admin role (Phase 3)

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request succeeded |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request data or business rule violation |
| 401 | Unauthorized | Missing or invalid authentication token |
| 403 | Forbidden | Insufficient permissions (not admin) |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Duplicate resource or concurrent modification |
| 422 | Unprocessable Entity | Validation error |
| 502 | Bad Gateway | External service (billing) failure |
| 503 | Service Unavailable | Service is down |

## Pagination

The service supports two pagination formats:

### Format 1: Page-based (Recommended)

Used by frontend applications:

```
GET /candidates?page=1&page_size=20
```

- `page`: Page number (1-indexed)
- `page_size`: Results per page (max 100)

### Format 2: Offset-based (Legacy)

Used for direct API access:

```
GET /candidates?limit=20&offset=0
```

- `limit`: Number of results (max 100)
- `offset`: Number of results to skip

### Pagination Response

```json
{
  "candidates": [...],
  "pagination": {
    "total": 150,
    "limit": 20,
    "offset": 0
  }
}
```

---

## Endpoints

### Health Check

#### GET /health

Check service health and database connectivity.

**Authentication:** None

**Response:** 200 OK

```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2025-10-27T10:00:00.000Z"
}
```

**Example:**

```bash
curl http://localhost:5004/health
```

---

### Authentication Endpoints

#### POST /auth/login

Login and receive JWT access token.

**Authentication:** None

**Content-Type:** application/x-www-form-urlencoded

**Request Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| username | string | Yes | User email address |
| password | string | Yes | User password |

**Response:** 200 OK

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Default Admin Credentials:**

- Username: `admin@example.com`
- Password: `admin123`

**Example:**

```bash
# Login and save token
TOKEN=$(curl -X POST http://localhost:5004/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=admin123" \
  | jq -r '.access_token')

# Use token in subsequent requests
curl http://localhost:5004/candidates/123/approve \
  -H "Authorization: Bearer $TOKEN" \
  -X POST
```

**Error Responses:**

- **401 Unauthorized**: Invalid credentials
  ```json
  {
    "detail": "Incorrect username or password"
  }
  ```

---

### Candidate Management

#### POST /candidates

Register a new provider candidate.

**Authentication:** None (public endpoint)

**Content-Type:** application/json

**Request Body:**

```json
{
  "company_name": "Fresh Fruit Suppliers Ltd.",
  "contact_email": "contact@freshfruit.com",
  "phone": "+1-555-0123",
  "products": ["apples", "oranges"],
  "truck_count": 10,
  "capacity_tons_per_day": 500,
  "location": "California, USA"
}
```

**Field Validation:**

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| company_name | string | Yes | 1-255 characters |
| contact_email | string | Yes | Valid email, must be unique |
| phone | string | No | Max 50 characters |
| products | array[string] | Yes | At least 1 product from allowed list |
| truck_count | integer | Yes | Must be > 0 |
| capacity_tons_per_day | integer | Yes | Must be > 0 |
| location | string | No | Max 255 characters |

**Allowed Products:**
- apples
- oranges
- grapes
- bananas
- mangoes

**Response:** 201 Created

```json
{
  "candidate_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "company_name": "Fresh Fruit Suppliers Ltd.",
  "contact_email": "contact@freshfruit.com",
  "phone": "+1-555-0123",
  "products": ["apples", "oranges"],
  "truck_count": 10,
  "capacity_tons_per_day": 500,
  "location": "California, USA",
  "created_at": "2025-10-27T10:00:00.000Z",
  "updated_at": "2025-10-27T10:00:00.000Z",
  "provider_id": null,
  "version": 1
}
```

**Example:**

```bash
curl -X POST http://localhost:5004/candidates \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Fresh Fruit Suppliers Ltd.",
    "contact_email": "contact@freshfruit.com",
    "phone": "+1-555-0123",
    "products": ["apples", "oranges"],
    "truck_count": 10,
    "capacity_tons_per_day": 500,
    "location": "California, USA"
  }'
```

**Error Responses:**

- **409 Conflict**: Duplicate email
  ```json
  {
    "detail": "A candidate with this email already exists"
  }
  ```

- **422 Validation Error**: Invalid product
  ```json
  {
    "detail": [
      {
        "loc": ["body", "products", 0],
        "msg": "Invalid product: tomatoes. Allowed products: apples, oranges, grapes, bananas, mangoes",
        "type": "value_error"
      }
    ]
  }
  ```

---

#### GET /candidates

List candidates with filtering and pagination.

**Authentication:** None

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| status | string | No | Filter by status: pending, approved, rejected |
| product | string | No | Filter by product (candidates who supply this product) |
| page | integer | No | Page number (1-indexed), use with page_size |
| page_size | integer | No | Results per page (1-100), use with page |
| limit | integer | No | Number of results (1-100), legacy |
| offset | integer | No | Number to skip, legacy |

**Response:** 200 OK

```json
{
  "candidates": [
    {
      "candidate_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "pending",
      "company_name": "Fresh Fruit Suppliers Ltd.",
      "contact_email": "contact@freshfruit.com",
      "phone": "+1-555-0123",
      "products": ["apples", "oranges"],
      "truck_count": 10,
      "capacity_tons_per_day": 500,
      "location": "California, USA",
      "created_at": "2025-10-27T10:00:00.000Z",
      "updated_at": "2025-10-27T10:00:00.000Z",
      "provider_id": null,
      "version": 1
    }
  ],
  "pagination": {
    "total": 1,
    "limit": 20,
    "offset": 0
  }
}
```

**Examples:**

```bash
# List all candidates (default pagination: 20 per page)
curl http://localhost:5004/candidates

# Filter by status
curl http://localhost:5004/candidates?status=pending

# Filter by product
curl http://localhost:5004/candidates?product=apples

# Page-based pagination (frontend)
curl http://localhost:5004/candidates?page=1&page_size=10

# Offset-based pagination (legacy)
curl http://localhost:5004/candidates?limit=10&offset=0

# Combine filters
curl "http://localhost:5004/candidates?status=pending&product=apples&page=1&page_size=20"
```

---

#### GET /candidates/{candidate_id}

Get a single candidate by ID.

**Authentication:** None

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| candidate_id | UUID | Candidate UUID |

**Response:** 200 OK

```json
{
  "candidate_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "company_name": "Fresh Fruit Suppliers Ltd.",
  "contact_email": "contact@freshfruit.com",
  "phone": "+1-555-0123",
  "products": ["apples", "oranges"],
  "truck_count": 10,
  "capacity_tons_per_day": 500,
  "location": "California, USA",
  "created_at": "2025-10-27T10:00:00.000Z",
  "updated_at": "2025-10-27T10:00:00.000Z",
  "provider_id": null,
  "version": 1
}
```

**Example:**

```bash
curl http://localhost:5004/candidates/550e8400-e29b-41d4-a716-446655440000
```

**Error Responses:**

- **404 Not Found**: Candidate doesn't exist
  ```json
  {
    "detail": "Candidate not found"
  }
  ```

- **422 Validation Error**: Invalid UUID format
  ```json
  {
    "detail": [
      {
        "loc": ["path", "candidate_id"],
        "msg": "value is not a valid uuid",
        "type": "type_error.uuid"
      }
    ]
  }
  ```

---

#### POST /candidates/{candidate_id}/approve

Approve a candidate and create provider in billing service. **Admin only**.

**Authentication:** Required (Bearer token with admin role)

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| candidate_id | UUID | Candidate UUID |

**Request Body:** None

**Response:** 200 OK

```json
{
  "candidate_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "approved",
  "provider_id": 123
}
```

**Workflow:**
1. Validates candidate exists and is pending
2. Creates provider in billing service
3. Updates candidate status to 'approved' with provider_id
4. Uses optimistic locking (version check) to prevent concurrent modifications

**Example:**

```bash
# Login first
TOKEN=$(curl -X POST http://localhost:5004/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=admin123" \
  | jq -r '.access_token')

# Approve candidate
curl -X POST http://localhost:5004/candidates/550e8400-e29b-41d4-a716-446655440000/approve \
  -H "Authorization: Bearer $TOKEN"
```

**Error Responses:**

- **401 Unauthorized**: Missing or invalid token
  ```json
  {
    "detail": "Could not validate credentials"
  }
  ```

- **403 Forbidden**: Not admin
  ```json
  {
    "detail": "Admin access required"
  }
  ```

- **404 Not Found**: Candidate doesn't exist
  ```json
  {
    "detail": "Candidate not found"
  }
  ```

- **400 Bad Request**: Already approved/rejected
  ```json
  {
    "detail": "Candidate already approved"
  }
  ```

- **409 Conflict**: Concurrent modification (optimistic locking failure)
  ```json
  {
    "detail": "Candidate was modified by another process. Please retry."
  }
  ```

- **502 Bad Gateway**: Billing service failure
  ```json
  {
    "detail": "Failed to create provider: Connection refused"
  }
  ```

---

#### POST /candidates/{candidate_id}/reject

Reject a candidate with optional reason. **Admin only**. (Phase 3 feature)

**Authentication:** Required (Bearer token with admin role)

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| candidate_id | UUID | Candidate UUID |

**Request Body:**

```json
{
  "rejection_reason": "Insufficient capacity for our requirements"
}
```

**Response:** 200 OK

```json
{
  "candidate_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "rejected",
  "rejection_reason": "Insufficient capacity for our requirements"
}
```

**Example:**

```bash
# Login first
TOKEN=$(curl -X POST http://localhost:5004/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=admin123" \
  | jq -r '.access_token')

# Reject candidate
curl -X POST http://localhost:5004/candidates/550e8400-e29b-41d4-a716-446655440000/reject \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "rejection_reason": "Insufficient capacity for our requirements"
  }'
```

**Error Responses:**

Similar to approve endpoint (401, 403, 404, 400, 409)

---

### Metrics

#### GET /metrics

Prometheus metrics endpoint for monitoring.

**Authentication:** None

**Content-Type:** text/plain

**Response:** 200 OK

```
# HELP provider_service_up Service uptime status
# TYPE provider_service_up gauge
provider_service_up 1.0

# HELP provider_service_requests_total Total number of requests
# TYPE provider_service_requests_total counter
provider_service_requests_total{method="POST",endpoint="/candidates",status_code="201"} 42.0
provider_service_requests_total{method="GET",endpoint="/candidates",status_code="200"} 156.0
```

**Example:**

```bash
# Get all metrics
curl http://localhost:5004/metrics

# Filter specific metric
curl http://localhost:5004/metrics | grep provider_service_up
```

**Available Metrics:**

- `provider_service_up`: Service uptime (1=up, 0=down)
- `provider_service_requests_total`: Request counter by method, endpoint, status

---

## Rate Limiting

Currently not implemented. Future enhancement planned.

## Versioning

API version is included in root endpoint response. Breaking changes will use path-based versioning (`/v2/candidates`).

## Support

For API support:
- View interactive documentation: http://localhost:5004/docs
- Check health: http://localhost:5004/health
- View operations guide: [OPERATIONS.md](./OPERATIONS.md)
